import asyncio
import aiohttp
import hmac
import hashlib
import base64
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class AccountChecker:
    def __init__(self):
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        self.base_url = "https://www.okx.com"

    async def make_request(self, method, endpoint, body=''):
        """OKX API 요청 공통 함수"""
        timestamp = datetime.utcnow().strftime(
            '%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        message = timestamp + method + endpoint + body
        signature = base64.b64encode(
            hmac.new(self.secret_key.encode(),
                     message.encode(), hashlib.sha256).digest()
        ).decode()

        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }

        async with aiohttp.ClientSession() as session:
            if method == 'GET':
                async with session.get(self.base_url + endpoint, headers=headers) as response:
                    return await self.handle_response(response)
            elif method == 'POST':
                async with session.post(self.base_url + endpoint, headers=headers, data=body) as response:
                    return await self.handle_response(response)

    async def handle_response(self, response):
        """응답 처리"""
        if response.status == 200:
            data = await response.json()
            if data.get('code') == '0':
                return data['data']
            else:
                print(f"❌ API 오류: {data.get('msg')}")
                return None
        else:
            error_text = await response.text()
            print(f"❌ HTTP 오류: {response.status} - {error_text}")
            return None

    async def get_account_balance(self):
        """계좌 잔고 조회"""
        print("💰 계좌 잔고 조회 중...")
        endpoint = "/api/v5/account/balance"

        balance_data = await self.make_request('GET', endpoint)
        if not balance_data:
            return None

        balances = {}
        for account in balance_data:
            for detail in account.get('details', []):
                currency = detail['ccy']
                available = float(detail['availBal'])
                frozen = float(detail['frozenBal'])
                total = available + frozen

                if total > 0:
                    balances[currency] = {
                        'available': available,
                        'frozen': frozen,
                        'total': total
                    }

        return balances

    async def get_trading_balance(self):
        """거래 계좌 잔고 조회 (현물)"""
        print("🔄 거래 계좌 잔고 조회 중...")
        endpoint = "/api/v5/account/balance"

        return await self.get_account_balance()

    async def get_order_history(self, symbol="", limit=10):
        """최근 주문 내역 조회"""
        print(f"📋 최근 주문 내역 조회 중... (최근 {limit}개)")

        endpoint = f"/api/v5/trade/orders-history-archive?instType=SPOT"
        if symbol:
            endpoint += f"&instId={symbol}"
        endpoint += f"&limit={limit}"

        order_data = await self.make_request('GET', endpoint)
        return order_data if order_data else []

    async def get_fill_history(self, symbol="", limit=10):
        """최근 체결 내역 조회"""
        print(f"✅ 최근 체결 내역 조회 중... (최근 {limit}개)")

        endpoint = f"/api/v5/trade/fills-history?instType=SPOT"
        if symbol:
            endpoint += f"&instId={symbol}"
        endpoint += f"&limit={limit}"

        fill_data = await self.make_request('GET', endpoint)
        return fill_data if fill_data else []

    async def check_pending_orders(self):
        """미체결 주문 확인"""
        print("⏳ 미체결 주문 확인 중...")

        endpoint = "/api/v5/trade/orders-pending?instType=SPOT"

        pending_data = await self.make_request('GET', endpoint)
        return pending_data if pending_data else []

    async def get_instrument_info(self, symbol):
        """코인 정보 조회"""
        endpoint = f"/api/v5/public/instruments?instType=SPOT&instId={symbol}"

        inst_data = await self.make_request('GET', endpoint)
        return inst_data[0] if inst_data else None

    async def comprehensive_check(self):
        """종합 계좌 상태 확인"""
        print("🔍 종합 계좌 상태 확인 시작")
        print("=" * 60)

        # 1. 계좌 잔고
        balances = await self.get_account_balance()
        if balances:
            print("\n💰 현재 보유 자산:")
            print("-" * 40)
            for currency, info in balances.items():
                if info['total'] > 0:
                    print(
                        f"   {currency:>8}: {info['available']:>15.8f} (사용가능)")
                    if info['frozen'] > 0:
                        print(f"   {' ':>8}: {info['frozen']:>15.8f} (동결됨)")
                    print(f"   {' ':>8}: {info['total']:>15.8f} (총합)")
                    print()

        # 2. 미체결 주문
        pending_orders = await self.check_pending_orders()
        if pending_orders:
            print("\n⏳ 미체결 주문:")
            print("-" * 40)
            for order in pending_orders:
                print(f"   주문ID: {order['ordId']}")
                print(f"   코인: {order['instId']}")
                print(f"   타입: {order['side']} / {order['ordType']}")
                print(f"   수량: {order['sz']}")
                print(f"   가격: {order.get('px', 'Market')}")
                print(f"   상태: {order['state']}")
                print()
        else:
            print("\n✅ 미체결 주문 없음")

        # 3. 최근 체결 내역 (VENOM 관련)
        venom_fills = await self.get_fill_history("VENOM-USDT", 20)
        if venom_fills:
            print("\n📊 최근 VENOM 체결 내역:")
            print("-" * 40)
            total_buy = 0
            total_sell = 0

            for fill in venom_fills:
                side = fill['side']
                size = float(fill['fillSz'])
                price = float(fill['fillPx'])
                fee = float(fill['fee'])
                timestamp = fill['ts']

                # UTC 타임스탬프를 읽기 쉬운 형태로 변환
                dt = datetime.fromtimestamp(int(timestamp) / 1000)
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')

                print(
                    f"   {time_str} | {side:>4} | {size:>12.8f} | ${price:>8.5f} | 수수료: {fee:>10.8f}")

                if side == 'buy':
                    total_buy += size
                else:
                    total_sell += size

            print("-" * 40)
            print(f"   총 매수: {total_buy:>12.8f} VENOM")
            print(f"   총 매도: {total_sell:>12.8f} VENOM")
            print(f"   순 보유: {total_buy - total_sell:>12.8f} VENOM")

        # 4. VENOM 코인 정보
        venom_info = await self.get_instrument_info("VENOM-USDT")
        if venom_info:
            print(f"\n🔧 VENOM 거래 정보:")
            print("-" * 40)
            print(f"   최소 주문량: {venom_info['minSz']}")
            print(f"   수량 단위: {venom_info['lotSz']}")
            print(f"   가격 단위: {venom_info['tickSz']}")

        print("\n" + "=" * 60)
        print("✅ 종합 계좌 상태 확인 완료")


async def main():
    checker = AccountChecker()
    await checker.comprehensive_check()

if __name__ == "__main__":
    asyncio.run(main())
