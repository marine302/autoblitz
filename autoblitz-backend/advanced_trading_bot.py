# advanced_trading_bot.py - 부분 체결 문제 해결한 고급 봇
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

class AdvancedTradingBot:
    """부분 체결 문제를 해결한 고급 거래 봇"""
    
    def __init__(self):
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        self.base_url = "https://www.okx.com"
        
        # 추적 변수들
        self.active_orders = {}  # 활성 주문 추적
        self.positions = {}      # 포지션 추적
        
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
    
    async def get_instrument_info(self, symbol):
        """코인 상세 정보 조회"""
        endpoint = f"/api/v5/public/instruments?instType=SPOT&instId={symbol}"
        data = await self.make_request('GET', endpoint)
        return data[0] if data else None
    
    async def get_current_price(self, symbol):
        """현재 가격 조회"""
        endpoint = f"/api/v5/market/ticker?instId={symbol}"
        data = await self.make_request('GET', endpoint)
        return float(data[0]['last']) if data else None
    
    async def get_account_balance(self, currency=None):
        """계좌 잔고 조회"""
        endpoint = "/api/v5/account/balance"
        data = await self.make_request('GET', endpoint)
        
        if not data:
            return None
        
        balances = {}
        for account in data:
            for detail in account.get('details', []):
                ccy = detail['ccy']
                available = float(detail['availBal'])
                
                if currency:
                    if ccy == currency:
                        return available
                else:
                    balances[ccy] = available
        
        return balances if not currency else 0
    
    def calculate_order_size(self, amount_usdt, price, lot_size, min_size):
        """정확한 주문 수량 계산"""
        # 기본 계산
        raw_size = amount_usdt / price
        
        # lot_size에 맞춰 반올림 (아래로)
        lot_decimal = Decimal(str(lot_size))
        decimal_places = abs(lot_decimal.as_tuple().exponent)
        
        precise_size = Decimal(str(raw_size)).quantize(
            Decimal(str(lot_size)), 
            rounding=ROUND_DOWN
        )
        
        final_size = float(precise_size)
        
        # 최소 주문량 확인
        if final_size < float(min_size):
            raise ValueError(f"계산된 수량 {final_size}이 최소 주문량 {min_size}보다 작습니다")
        
        return final_size
    
    async def place_order_with_tracking(self, side, symbol, size, order_type="market"):
        """추적 가능한 주문 실행"""
        endpoint = "/api/v5/trade/order"
        
        order_data = {
            "instId": symbol,
            "tdMode": "cash",
            "side": side,
            "ordType": order_type,
            "sz": str(size)
        }
        
        body = json.dumps(order_data)
        order_result = await self.make_request('POST', endpoint, body)
        
        if order_result:
            order_id = order_result[0]['ordId']
            
            # 주문 추적 시작
            self.active_orders[order_id] = {
                'symbol': symbol,
                'side': side,
                'total_size': size,
                'filled_size': 0,
                'status': 'pending'
            }
            
            print(f"✅ 주문 생성: {order_id} ({side} {size} {symbol})")
            return order_id
        
        return None
    
    async def monitor_order_until_filled(self, order_id, timeout=60):
        """주문이 완전히 체결될 때까지 모니터링"""
        print(f"⏳ 주문 {order_id} 체결 대기 중...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 주문 상태 확인
            endpoint = f"/api/v5/trade/order?instId={self.active_orders[order_id]['symbol']}&ordId={order_id}"
            order_info = await self.make_request('GET', endpoint)
            
            if not order_info:
                await asyncio.sleep(1)
                continue
            
            order_data = order_info[0]
            state = order_data['state']
            filled_size = float(order_data['accFillSz'])
            avg_price = float(order_data['avgPx']) if order_data['avgPx'] else 0
            
            print(f"📊 주문 상태: {state} | 체결량: {filled_size}")
            
            if state == 'filled':
                # 완전 체결
                self.active_orders[order_id]['status'] = 'filled'
                self.active_orders[order_id]['filled_size'] = filled_size
                self.active_orders[order_id]['avg_price'] = avg_price
                
                print(f"✅ 주문 완전 체결: {filled_size} @ ${avg_price}")
                return {
                    'order_id': order_id,
                    'filled_size': filled_size,
                    'avg_price': avg_price,
                    'status': 'completed'
                }
            
            elif state == 'partially_filled':
                # 부분 체결 - 계속 대기
                self.active_orders[order_id]['filled_size'] = filled_size
                print(f"🔄 부분 체결: {filled_size} (대기 중...)")
            
            elif state == 'cancelled':
                print(f"❌ 주문 취소됨: {order_id}")
                return None
            
            await asyncio.sleep(2)  # 2초마다 확인
        
        print(f"⏰ 타임아웃: 주문 {order_id}")
        return None
    
    async def safe_trade_execution(self, symbol, amount_usdt, profit_target=1.0, max_hold_time=300):
        """안전한 거래 실행 (부분 체결 문제 해결)"""
        print(f"🤖 안전한 거래 시작: {symbol}")
        print(f"💰 거래 금액: ${amount_usdt}")
        print(f"📈 목표 수익률: {profit_target}%")
        print("=" * 50)
        
        try:
            # 1. 코인 정보 및 현재 가격 조회
            instrument = await self.get_instrument_info(symbol)
            current_price = await self.get_current_price(symbol)
            
            if not instrument or not current_price:
                print("❌ 코인 정보 조회 실패")
                return None
            
            print(f"💰 {symbol} 현재가: ${current_price}")
            print(f"🔧 최소 주문량: {instrument['minSz']}")
            print(f"🔧 수량 단위: {instrument['lotSz']}")
            
            # 2. 정확한 주문 수량 계산
            order_size = self.calculate_order_size(
                amount_usdt, 
                current_price, 
                float(instrument['lotSz']), 
                float(instrument['minSz'])
            )
            
            print(f"🛒 계산된 주문량: {order_size}")
            
            # 3. 매수 주문 실행 및 완전 체결 대기
            buy_order_id = await self.place_order_with_tracking("buy", symbol, order_size)
            
            if not buy_order_id:
                print("❌ 매수 주문 실패")
                return None
            
            # 4. 매수 완전 체결까지 대기
            buy_result = await self.monitor_order_until_filled(buy_order_id)
            
            if not buy_result:
                print("❌ 매수 체결 실패")
                return None
            
            # 5. 실제 체결된 수량 확인 (수수료 고려)
            actual_balance = await self.get_account_balance(symbol.split('-')[0])
            print(f"💎 실제 보유량: {actual_balance} (수수료 차감 후)")
            
            entry_price = buy_result['avg_price']
            entry_time = time.time()
            
            # 6. 수익률 모니터링
            print(f"\n📊 수익률 모니터링 시작 (최대 {max_hold_time}초)")
            
            while time.time() - entry_time < max_hold_time:
                current_price = await self.get_current_price(symbol)
                profit_rate = ((current_price - entry_price) / entry_price) * 100
                profit_usd = (current_price - entry_pr
