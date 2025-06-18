# debug_orderbook.py - 호가창 구조 확인
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

class OrderBookDebugger:
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
        return None
    
    async def debug_order_book(self, symbol="VENOM-USDT"):
        print(f"🔍 {symbol} 호가창 구조 분석")
        print("=" * 50)
        
        endpoint = f"/api/v5/market/books?instId={symbol}&sz=5"
        data = await self.make_request('GET', endpoint)
        
        if data:
            print("📊 원본 데이터:")
            print(json.dumps(data, indent=2))
            print()
            
            order_book = data[0]
            asks = order_book['asks']
            bids = order_book['bids']
            
            print(f"📋 asks 구조 (총 {len(asks)}개):")
            for i, ask in enumerate(asks[:3]):
                print(f"  [{i}] {ask} (타입: {type(ask)}, 길이: {len(ask)})")
            
            print(f"\n📋 bids 구조 (총 {len(bids)}개):")
            for i, bid in enumerate(bids[:3]):
                print(f"  [{i}] {bid} (타입: {type(bid)}, 길이: {len(bid)})")
            
            # 안전한 파싱 테스트
            print(f"\n🧪 안전한 파싱 테스트:")
            try:
                best_ask = asks[0]
                best_bid = bids[0]
                
                print(f"  최우선 매도: {best_ask}")
                print(f"  최우선 매수: {best_bid}")
                
                # 각 필드 접근 테스트
                ask_price = float(best_ask[0])
                ask_size = float(best_ask[1])
                bid_price = float(best_bid[0])
                bid_size = float(best_bid[1])
                
                print(f"  매도 가격: ${ask_price:.5f}")
                print(f"  매도 수량: {ask_size}")
                print(f"  매수 가격: ${bid_price:.5f}")
                print(f"  매수 수량: {bid_size}")
                print(f"  스프레드: ${ask_price - bid_price:.5f}")
                
                print("✅ 파싱 성공!")
                
            except Exception as e:
                print(f"❌ 파싱 오류: {e}")
        
        else:
            print("❌ 호가창 데이터 조회 실패")

async def main():
    debugger = OrderBookDebugger()
    await debugger.debug_order_book()

if __name__ == "__main__":
    asyncio.run(main())
