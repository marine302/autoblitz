# emergency_sell.py - 긴급 매도 스크립트
import asyncio
import aiohttp
import hmac
import hashlib
import base64
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/workspaces/autoblitz/autoblitz-backend/.env')

class EmergencySell:
    def __init__(self):
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        self.base_url = "https://www.okx.com"
    
    async def make_request(self, method, endpoint, body=''):
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
                    if response.status == 200:
                        data = await response.json()
                        if data.get('code') == '0':
                            return data['data']
                        else:
                            print(f"❌ API 오류: {data.get('msg')}")
            elif method == 'POST':
                async with session.post(self.base_url + endpoint, headers=headers, data=body) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('code') == '0':
                            return data['data']
                        else:
                            print(f"❌ API 오류: {data.get('msg')}")
                            print(f"📤 요청: {body}")
        return None
    
    async def get_balance(self, currency):
        endpoint = "/api/v5/account/balance"
        data = await self.make_request('GET', endpoint)
        
        if data:
            for account in data:
                for detail in account.get('details', []):
                    if detail['ccy'] == currency:
                        return float(detail['availBal'])
        return 0
    
    async def get_instrument_info(self, symbol):
        """코인 정보 조회"""
        endpoint = f"/api/v5/public/instruments?instType=SPOT&instId={symbol}"
        data = await self.make_request('GET', endpoint)
        return data[0] if data else None
    
    async def emergency_sell_venom(self):
        print("🚨 VENOM 긴급 매도 시작")
        
        # 현재 보유량 확인
        venom_balance = await self.get_balance('VENOM')
        print(f"💰 현재 VENOM 보유량: {venom_balance}")
        
        if venom_balance <= 0:
            print("✅ 매도할 VENOM이 없습니다")
            return
        
        # 코인 정보 확인
        instrument = await self.get_instrument_info('VENOM-USDT')
        if instrument:
            print(f"🔧 최소 주문량: {instrument['minSz']}")
            print(f"🔧 수량 단위: {instrument['lotSz']}")
        
        # 여러 방법으로 매도 시도
        methods = [
            # 방법 1: 전체 보유량 (소수점 그대로)
            ("전체 보유량", str(venom_balance)),
            
            # 방법 2: 3자리 반올림
            ("3자리 반올림", f"{venom_balance:.3f}"),
            
            # 방법 3: 정수 부분만
            ("정수 부분", str(int(venom_balance))),
            
            # 방법 4: 60개 (안전한 수량)
            ("안전 수량", "60"),
        ]
        
        for method_name, sell_amount in methods:
            print(f"\n🔄 {method_name} 매도 시도: {sell_amount}")
            
            order_data = {
                "instId": "VENOM-USDT",
                "tdMode": "cash",
                "side": "sell",
                "ordType": "market",
                "sz": sell_amount
            }
            
            body = json.dumps(order_data)
            print(f"📤 요청: {body}")
            
            result = await self.make_request('POST', "/api/v5/trade/order", body)
            
            if result:
                order_id = result[0]['ordId']
                print(f"✅ 매도 성공! 주문ID: {order_id}")
                
                # 체결 확인
                await asyncio.sleep(3)
                
                endpoint = f"/api/v5/trade/order?instId=VENOM-USDT&ordId={order_id}"
                order_info = await self.make_request('GET', endpoint)
                
                if order_info:
                    order = order_info[0]
                    print(f"📊 체결 상태: {order['state']}")
                    print(f"📊 체결량: {order['accFillSz']}")
                    print(f"📊 평균가: ${float(order['avgPx']):.5f}")
                
                return True
            else:
                print(f"❌ {method_name} 실패")
        
        print("\n❌ 모든 매도 방법 실패")
        return False

async def main():
    seller = EmergencySell()
    await seller.emergency_sell_venom()

if __name__ == "__main__":
    asyncio.run(main())
