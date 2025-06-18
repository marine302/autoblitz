# fixed_trading_bot.py - 문법 오류 수정 버전
import asyncio
import aiohttp
import hmac
import hashlib
import base64
import json
import os
import time
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from dotenv import load_dotenv

load_dotenv()

class FixedTradingBot:
    """문법 오류를 수정한 안전한 거래 봇"""
    
    def __init__(self):
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        self.base_url = "https://www.okx.com"
    
    async def make_request(self, method, endpoint, body=''):
        """OKX API 요청"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        message = timestamp + method + endpoint + body
        signature = base64.b64encode(
            hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256).digest()
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
    
    async def get_current_price(self, symbol):
        """현재 가격 조회"""
        endpoint = f"/api/v5/market/ticker?instId={symbol}"
        data = await self.make_request('GET', endpoint)
        return float(data[0]['last']) if data else None
    
    async def get_account_balance(self, currency):
        """특정 통화 잔고 조회"""
        endpoint = "/api/v5/account/balance"
        data = await self.make_request('GET', endpoint)
        
        if not data:
            return 0
        
        for account in data:
            for detail in account.get('details', []):
                if detail['ccy'] == currency:
                    return float(detail['availBal'])
        
        return 0
    
    async def place_order(self, side, symbol, size):
        """주문 실행"""
        endpoint = "/api/v5/trade/order"
        
        order_data = {
            "instId": symbol,
            "tdMode": "cash",
            "side": side,
            "ordType": "market",
            "sz": str(size)
        }
        
        body = json.dumps(order_data)
        result = await self.make_request('POST', endpoint, body)
        
        if result:
            order_id = result[0]['ordId']
            print(f"✅ {side} 주문 생성: {order_id}")
            return order_id
        
        return None
    
    async def wait_for_order_fill(self, order_id, symbol, timeout=60):
        """주문 체결 대기"""
        print(f"⏳ 주문 체결 대기: {order_id}")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            endpoint = f"/api/v5/trade/order?instId={symbol}&ordId={order_id}"
            order_info = await self.make_request('GET', endpoint)
            
            if order_info:
                state = order_info[0]['state']
                filled_size = float(order_info[0]['accFillSz'])
                
                print(f"📊 상태: {state} | 체결량: {filled_size}")
                
                if state == 'filled':
                    avg_price = float(order_info[0]['avgPx'])
                    print(f"✅ 완전 체결: {filled_size} @ ${avg_price}")
                    return {'filled': True, 'size': filled_size, 'price': avg_price}
                elif state == 'cancelled':
                    print(f"❌ 주문 취소: {order_id}")
                    return {'filled': False}
            
            await asyncio.sleep(2)
        
        print(f"⏰ 타임아웃: {order_id}")
        return {'filled': False}
    
    async def safe_trade(self, symbol, amount_usdt, target_profit=0.5, max_time=120):
        """안전한 거래 실행"""
        print(f"🤖 안전한 거래 시작")
        print(f"💰 거래쌍: {symbol}")
        print(f"💰 금액: ${amount_usdt}")
        print(f"📈 목표: {target_profit}%")
        print("=" * 40)
        
        try:
            # 1. 현재 가격 확인
            current_price = await self.get_current_price(symbol)
            if not current_price:
                print("❌ 가격 조회 실패")
                return None
            
            print(f"💰 현재가: ${current_price}")
            
            # 2. 매수량 계산
            buy_size = amount_usdt / current_price
            buy_size = round(buy_size, 8)  # 8자리로 반올림
            
            print(f"🛒 매수량: {buy_size}")
            
            # 3. 매수 주문
            buy_order_id = await self.place_order("buy", symbol, buy_size)
            if not buy_order_id:
                print("❌ 매수 주문 실패")
                return None
            
            # 4. 매수 체결 대기
            buy_result = await self.wait_for_order_fill(buy_order_id, symbol)
            if not buy_result['filled']:
                print("❌ 매수 체결 실패")
                return None
            
            entry_price = buy_result['price']
            
            # 5. 실제 보유량 확인
            base_currency = symbol.split('-')[0]
            actual_balance = await self.get_account_balance(base_currency)
            print(f"💎 실제 보유: {actual_balance} {base_currency}")
            
            # 6. 수익률 모니터링
            print(f"\n📊 수익률 모니터링 ({max_time}초)")
            start_time = time.time()
            
            while time.time() - start_time < max_time:
                current_price = await self.get_current_price(symbol)
                if current_price:
                    profit_rate = ((current_price - entry_price) / entry_price) * 100
                    profit_amount = (current_price - entry_price) * actual_balance
                    
                    elapsed = int(time.time() - start_time)
                    print(f"[{elapsed:3d}s] ${current_price:8.5f} | {profit_rate:+6.3f}% | ${profit_amount:+7.4f}")
                    
                    # 목표 달성 시 매도
                    if profit_rate >= target_profit:
                        print(f"🎉 목표 달성! ({profit_rate:.3f}%)")
                        break
                
                await asyncio.sleep(5)
            
            # 7. 매도 실행
            print(f"\n💸 매도 실행: {actual_balance}")
            sell_order_id = await self.place_order("sell", symbol, actual_balance)
            
            if sell_order_id:
                sell_result = await self.wait_for_order_fill(sell_order_id, symbol)
                
                if sell_result['filled']:
                    exit_price = sell_result['price']
                    final_profit_rate = ((exit_price - entry_price) / entry_price) * 100
                    final_profit_amount = (exit_price - entry_price) * actual_balance
                    
                    print("\n" + "=" * 40)
                    print("✅ 거래 완료!")
                    print(f"📊 진입가: ${entry_price:.5f}")
                    print(f"📊 청산가: ${exit_price:.5f}")
                    print(f"💰 수익률: {final_profit_rate:+.3f}%")
                    print(f"💰 수익금: ${final_profit_amount:+.4f}")
                    
                    return {
                        'success': True,
                        'profit_rate': final_profit_rate,
                        'profit_amount': final_profit_amount
                    }
            
            print("❌ 매도 실패")
            return None
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            return None

async def main():
    bot = FixedTradingBot()
    
    print("🤖 수정된 거래 봇 테스트")
    print("=" * 30)
    
    confirm = input("10 USDT로 테스트하시겠습니까? (yes): ")
    if confirm.lower() != 'yes':
        print("❌ 취소")
        return
    
    result = await bot.safe_trade(
        symbol="BTC-USDT",
        amount_usdt=10.0,
        target_profit=0.5,
        max_time=60
    )
    
    if result and result['success']:
        print("🎉 테스트 성공!")
    else:
        print("❌ 테스트 실패")

if __name__ == "__main__":
    asyncio.run(main())
