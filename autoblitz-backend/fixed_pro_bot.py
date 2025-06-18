# fixed_pro_bot.py - 환경 변수 문제 해결 버전
import asyncio
import aiohttp
import hmac
import hashlib
import base64
import json
import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드 (경로 명시적 지정)
env_path = '/workspaces/autoblitz/autoblitz-backend/.env'
load_dotenv(env_path)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class FixedProBot:
    def __init__(self):
        # API 키 확인 및 로드
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        
        # API 키 검증
        if not all([self.api_key, self.secret_key, self.passphrase]):
            logger.error("❌ API 키가 설정되지 않았습니다!")
            logger.error(f"API_KEY: {'✅' if self.api_key else '❌'}")
            logger.error(f"SECRET_KEY: {'✅' if self.secret_key else '❌'}")
            logger.error(f"PASSPHRASE: {'✅' if self.passphrase else '❌'}")
            raise ValueError("API 키 설정이 필요합니다")
        
        self.base_url = "https://www.okx.com"
        self.taker_fee = 0.001
        
        logger.info(f"🤖 봇 초기화 완료: API 키 확인됨")
    
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
                    if response.status == 200:
                        data = await response.json()
                        if data.get('code') == '0':
                            return data['data']
            elif method == 'POST':
                async with session.post(self.base_url + endpoint, headers=headers, data=body) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('code') == '0':
                            return data['data']
        return None
    
    async def get_order_book(self, symbol):
        """호가창 조회"""
        endpoint = f"/api/v5/market/books?instId={symbol}&sz=10"
        data = await self.make_request('GET', endpoint)
        
        if data:
            asks = data[0]['asks']  # 매도 호가
            bids = data[0]['bids']  # 매수 호가
            
            logger.info(f"📊 {symbol} 호가창:")
            logger.info(f"   최우선 매도: ${float(asks[0][0]):.5f} ({asks[0][1]}개)")
            logger.info(f"   최우선 매수: ${float(bids[0][0]):.5f} ({bids[0][1]}개)")
            logger.info(f"   스프레드: ${float(asks[0][0]) - float(bids[0][0]):.5f}")
            
            return {
                'asks': asks,
                'bids': bids,
                'best_ask': float(asks[0][0]),
                'best_bid': float(bids[0][0])
            }
        return None
    
    async def simulate_buy(self, symbol, amount_usdt):
        """매수 시뮬레이션"""
        order_book = await self.get_order_book(symbol)
        if not order_book:
            return None
        
        asks = order_book['asks']
        remaining_usdt = amount_usdt
        total_size = 0
        weighted_cost = 0
        
        logger.info(f"🧮 매수 시뮬레이션: ${amount_usdt}")
        
        for ask_price, ask_size in asks:
            price = float(ask_price)
            available_size = float(ask_size)
            
            max_buyable = remaining_usdt / price
            actual_size = min(max_buyable, available_size)
            
            if actual_size > 0:
                cost = actual_size * price
                remaining_usdt -= cost
                total_size += actual_size
                weighted_cost += cost
                
                logger.info(f"   ${price:.5f} × {actual_size:.3f} = ${cost:.2f}")
                
                if remaining_usdt <= 0.01:
                    break
        
        avg_price = weighted_cost / amount_usdt if total_size > 0 else 0
        fee = weighted_cost * self.taker_fee
        
        result = {
            'total_size': total_size,
            'avg_price': avg_price,
            'gross_cost': weighted_cost,
            'fee': fee,
            'total_cost': weighted_cost + fee
        }
        
        logger.info(f"📊 시뮬레이션 결과: {total_size:.6f}개 @ ${avg_price:.5f}")
        return result
    
    async def simulate_sell(self, symbol, sell_size):
        """매도 시뮬레이션"""
        order_book = await self.get_order_book(symbol)
        if not order_book:
            return None
        
        bids = order_book['bids']
        remaining_size = sell_size
        total_revenue = 0
        
        logger.info(f"🧮 매도 시뮬레이션: {sell_size:.6f}개")
        
        for bid_price, bid_size in bids:
            price = float(bid_price)
            available_size = float(bid_size)
            
            actual_size = min(remaining_size, available_size)
            
            if actual_size > 0:
                revenue = actual_size * price
                total_revenue += revenue
                remaining_size -= actual_size
                
                logger.info(f"   ${price:.5f} × {actual_size:.3f} = ${revenue:.2f}")
                
                if remaining_size <= 0:
                    break
        
        avg_price = total_revenue / sell_size if sell_size > 0 else 0
        fee = total_revenue * self.taker_fee
        
        result = {
            'total_revenue': total_revenue,
            'avg_price': avg_price,
            'fee': fee,
            'net_revenue': total_revenue - fee
        }
        
        logger.info(f"📊 시뮬레이션 결과: ${total_revenue:.4f} @ ${avg_price:.5f}")
        return result
    
    async def get_balance(self, currency):
        """잔고 조회"""
        endpoint = "/api/v5/account/balance"
        data = await self.make_request('GET', endpoint)
        
        if data:
            for account in data:
                for detail in account.get('details', []):
                    if detail['ccy'] == currency:
                        return float(detail['availBal'])
        return 0
    
    async def place_order(self, side, symbol, amount):
        """주문 실행"""
        endpoint = "/api/v5/trade/order"
        
        if side == 'buy':
            order_data = {
                "instId": symbol,
                "tdMode": "cash",
                "side": "buy",
                "ordType": "market",
                "sz": str(amount),
                "tgtCcy": "quote_ccy"  # USDT 기준 주문
            }
        else:
            order_data = {
                "instId": symbol,
                "tdMode": "cash", 
                "side": "sell",
                "ordType": "market",
                "sz": str(amount)  # 코인 수량 기준
            }
        
        body = json.dumps(order_data)
        logger.info(f"📤 주문 요청: {body}")
        
        result = await self.make_request('POST', endpoint, body)
        
        if result:
            order_id = result[0]['ordId']
            logger.info(f"✅ {side} 주문 생성: {order_id}")
            return order_id
        
        logger.error(f"❌ {side} 주문 실패")
        return None
    
    async def check_order(self, order_id, symbol):
        """주문 상태 확인"""
        endpoint = f"/api/v5/trade/order?instId={symbol}&ordId={order_id}"
        data = await self.make_request('GET', endpoint)
        
        if data:
            order = data[0]
            return {
                'state': order['state'],
                'filled_size': float(order['accFillSz']),
                'avg_price': float(order['avgPx']) if order['avgPx'] else 0,
                'fee': float(order['fee']) if order['fee'] else 0
            }
        return None
    
    async def wait_order_fill(self, order_id, symbol):
        """주문 체결 대기"""
        logger.info(f"⏳ 주문 체결 대기: {order_id}")
        
        for i in range(30):
            order_info = await self.check_order(order_id, symbol)
            
            if order_info:
                state = order_info['state']
                filled = order_info['filled_size']
                
                logger.info(f"📊 [{i+1:2d}] {state} | 체결: {filled:.6f}")
                
                if state == 'filled':
                    logger.info(f"✅ 완전 체결: {filled:.6f} @ ${order_info['avg_price']:.5f}")
                    return order_info
                elif state == 'cancelled':
                    logger.error(f"❌ 주문 취소: {order_id}")
                    return None
            
            await asyncio.sleep(2)
        
        logger.error(f"⏰ 체결 타임아웃: {order_id}")
        return None
    
    async def professional_trade(self, symbol="VENOM-USDT", amount_usdt=10.0, target_profit=0.5, max_time=60):
        """프로페셔널 거래 실행"""
        logger.info("🚀 프로페셔널 거래 시작")
        logger.info(f"📊 설정: {symbol} | ${amount_usdt} | {target_profit}% | {max_time}s")
        
        try:
            # 1. 잔고 확인
            usdt_balance = await self.get_balance('USDT')
            logger.info(f"💰 USDT 잔고: ${usdt_balance:.2f}")
            
            if usdt_balance < amount_usdt:
                logger.error(f"❌ 잔고 부족: ${usdt_balance} < ${amount_usdt}")
                return None
            
            # 2. 매수 시뮬레이션
            buy_sim = await self.simulate_buy(symbol, amount_usdt)
            if not buy_sim:
                return None
            
            # 3. 손익분기점 계산
            breakeven = (buy_sim['fee'] / amount_usdt + self.taker_fee) * 100
            actual_target = target_profit + breakeven
            logger.info(f"📊 손익분기점: {breakeven:.3f}% | 실제 목표: {actual_target:.3f}%")
            
            # 4. 매수 실행
            logger.info("\n🛒 매수 실행")
            buy_order_id = await self.place_order('buy', symbol, amount_usdt)
            
            if not buy_order_id:
                return None
            
            buy_result = await self.wait_order_fill(buy_order_id, symbol)
            if not buy_result:
                return None
            
            entry_price = buy_result['avg_price']
            position_size = buy_result['filled_size']
            
            logger.info(f"✅ 매수 완료: {position_size:.6f} @ ${entry_price:.5f}")
            
            # 5. 수익률 모니터링
            logger.info(f"\n📊 수익률 모니터링 ({max_time}초)")
            start_time = time.time()
            
            while time.time() - start_time < max_time:
                sell_sim = await self.simulate_sell(symbol, position_size)
                
                if sell_sim:
                    current_price = sell_sim['avg_price']
                    gross_profit_rate = ((current_price - entry_price) / entry_price) * 100
                    
                    # 실제 수익률
                    total_cost = amount_usdt + buy_result['fee']
                    net_profit = sell_sim['net_revenue'] - total_cost
                    net_profit_rate = (net_profit / total_cost) * 100
                    
                    elapsed = int(time.time() - start_time)
                    logger.info(f"[{elapsed:3d}s] ${current_price:.5f} | 총: {gross_profit_rate:+.3f}% | 순: {net_profit_rate:+.3f}%")
                    
                    if net_profit_rate >= target_profit:
                        logger.info(f"🎉 목표 달성! ({net_profit_rate:.3f}%)")
                        break
                
                await asyncio.sleep(5)
            
            # 6. 매도 실행
            logger.info(f"\n💸 매도 실행: {position_size:.6f}")
            sell_order_id = await self.place_order('sell', symbol, position_size)
            
            if not sell_order_id:
                return None
            
            sell_result = await self.wait_order_fill(sell_order_id, symbol)
            if not sell_result:
                return None
            
            exit_price = sell_result['avg_price']
            
            # 7. 최종 결과
            total_cost = amount_usdt + buy_result['fee']
            total_revenue = (position_size * exit_price) - sell_result['fee']
            net_profit = total_revenue - total_cost
            net_profit_rate = (net_profit / total_cost) * 100
            
            logger.info("\n" + "=" * 50)
            logger.info("🏆 거래 완료!")
            logger.info(f"📊 진입: ${entry_price:.5f} | 청산: ${exit_price:.5f}")
            logger.info(f"💰 비용: ${total_cost:.4f} | 수익: ${total_revenue:.4f}")
            logger.info(f"📈 순손익: ${net_profit:+.4f} ({net_profit_rate:+.3f}%)")
            logger.info(f"💳 총수수료: ${buy_result['fee'] + sell_result['fee']:.4f}")
            logger.info("=" * 50)
            
            return {
                'success': True,
                'net_profit': net_profit,
                'net_profit_rate': net_profit_rate
            }
            
        except Exception as e:
            logger.error(f"❌ 오류: {e}")
            return None

async def main():
    try:
        bot = FixedProBot()
        result = await bot.professional_trade()
        
        if result and result['success']:
            print(f"🎉 거래 성공! 수익률: {result['net_profit_rate']:+.3f}%")
        else:
            print("❌ 거래 실패")
            
    except Exception as e:
        print(f"❌ 초기화 오류: {e}")

if __name__ == "__main__":
    asyncio.run(main())
