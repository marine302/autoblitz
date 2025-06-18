# test_real_bot.py - 실제 거래 봇 테스트
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

class SimpleOKXBot:
    """간단한 OKX 실거래 봇 (테스트용)"""
    
    def __init__(self):
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        self.base_url = "https://www.okx.com"
        
        # 봇 설정 (매우 안전한 테스트 설정)
        self.symbol = "BTC-USDT"
        self.test_amount = 5.0  # 5 USDT로 테스트 (매우 작은 금액)
        self.profit_target = 0.5  # 0.5% 수익률
        self.stop_loss = -0.3  # 0.3% 손절
        
        self.is_running = False
        self.entry_price = None
        self.position_size = None
        
    async def get_ticker(self):
        """현재 가격 조회"""
        import aiohttp
        import hmac
        import hashlib
        import base64
        
        endpoint = f"/api/v5/market/ticker?instId={self.symbol}"
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        message = timestamp + 'GET' + endpoint + ''
        signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url + endpoint, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0':
                        ticker_data = data['data'][0]
                        return {
                            'last': float(ticker_data['last']),
                            'bid': float(ticker_data['bidPx']),
                            'ask': float(ticker_data['askPx'])
                        }
        return None
    
    async def place_order(self, side, size, price=None):
        """주문 실행 (매우 작은 테스트 주문)"""
        import aiohttp
        import hmac
        import hashlib
        import base64
        import json
        
        endpoint = "/api/v5/trade/order"
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        # 주문 데이터 (현물 거래)
        order_data = {
            "instId": self.symbol,
            "tdMode": "cash",  # 현물 거래
            "side": side,  # buy 또는 sell
            "ordType": "market" if price is None else "limit",
            "sz": str(size)  # 주문 수량
        }
        
        if price:
            order_data["px"] = str(price)
        
        body = json.dumps(order_data)
        
        message = timestamp + 'POST' + endpoint + body
        signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        print(f"📋 주문 실행: {side} {size} {self.symbol}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url + endpoint, headers=headers, data=body) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0':
                        order_info = data['data'][0]
                        print(f"✅ 주문 성공: 주문ID {order_info['ordId']}")
                        return order_info
                    else:
                        print(f"❌ 주문 실패: {data.get('msg')}")
                        return None
                else:
                    error_text = await response.text()
                    print(f"❌ HTTP 오류: {response.status} - {error_text}")
                    return None
    
    async def run_simple_test(self):
        """간단한 매수-매도 테스트"""
        print("🤖 실거래 봇 테스트 시작!")
        print("=" * 50)
        print(f"💰 테스트 금액: {self.test_amount} USDT")
        print(f"📈 목표 수익률: {self.profit_target}%")
        print(f"📉 손절선: {self.stop_loss}%")
        print()
        
        # 안전 확인
        print("⚠️  실제 돈이 사용됩니다!")
        confirmation = input("정말 실거래를 시작하시겠습니까? (yes 입력): ")
        if confirmation.lower() != 'yes':
            print("❌ 테스트 취소됨")
            return
        
        try:
            # 1. 현재 가격 확인
            print("📊 현재 가격 조회 중...")
            ticker = await self.get_ticker()
            if not ticker:
                print("❌ 가격 조회 실패")
                return
            
            current_price = ticker['last']
            print(f"💰 {self.symbol} 현재가: ${current_price:,.2f}")
            
            # 2. 매수 수량 계산 (매우 작은 금액)
            buy_amount_btc = self.test_amount / current_price
            buy_amount_btc = round(buy_amount_btc, 8)  # 8자리까지
            
            print(f"🛒 매수 예정: {buy_amount_btc} BTC (약 ${self.test_amount})")
            
            # 3. 시장가 매수
            print("\n🚀 시장가 매수 실행...")
            buy_order = await self.place_order("buy", buy_amount_btc)
            
            if buy_order:
                self.entry_price = current_price
                self.position_size = buy_amount_btc
                
                print(f"✅ 매수 완료!")
                print(f"   진입가: ${self.entry_price:,.2f}")
                print(f"   수량: {self.position_size} BTC")
                
                # 4. 수익률 모니터링 (30초간)
                print(f"\n📊 30초간 수익률 모니터링...")
                
                for i in range(30):
                    await asyncio.sleep(1)
                    
                    ticker = await self.get_ticker()
                    if ticker:
                        current_price = ticker['last']
                        profit_rate = ((current_price - self.entry_price) / self.entry_price) * 100
                        profit_usd = (current_price - self.entry_price) * self.position_size
                        
                        print(f"[{i+1:2d}s] 가격: ${current_price:,.2f} | 수익률: {profit_rate:+.3f}% | 수익: ${profit_usd:+.2f}")
                        
                        # 수익률 체크
                        if profit_rate >= self.profit_target:
                            print(f"🎉 목표 수익률 달성! (+{profit_rate:.3f}%)")
                            break
                        elif profit_rate <= self.stop_loss:
                            print(f"🛑 손절선 도달 (-{abs(profit_rate):.3f}%)")
                            break
                
                # 5. 매도 (테스트 완료)
                print(f"\n💸 매도 실행...")
                sell_order = await self.place_order("sell", self.position_size)
                
                if sell_order:
                    final_ticker = await self.get_ticker()
                    final_price = final_ticker['last'] if final_ticker else current_price
                    
                    final_profit_rate = ((final_price - self.entry_price) / self.entry_price) * 100
                    final_profit_usd = (final_price - self.entry_price) * self.position_size
                    
                    print("✅ 매도 완료!")
                    print("📊 최종 결과:")
                    print(f"   진입가: ${self.entry_price:,.2f}")
                    print(f"   청산가: ${final_price:,.2f}")
                    print(f"   수익률: {final_profit_rate:+.3f}%")
                    print(f"   수익금: ${final_profit_usd:+.3f}")
                    print(f"🎉 첫 실거래 테스트 완료!")
                    
                    if final_profit_usd > 0:
