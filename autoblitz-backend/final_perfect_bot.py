# final_perfect_bot.py - 호가창 구조 문제 해결한 완벽한 봇
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

load_dotenv('/workspaces/autoblitz/autoblitz-backend/.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class PerfectTradingBot:
    """완벽하게 작동하는 프로페셔널 봇"""
    
    def __init__(self):
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        self.base_url = "https://www.okx.com"
        self.taker_fee = 0.001
        
        logger.info(f"🤖 완벽한 봇 초기화 완료")
    
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
                        else:
                            logger.error(f"❌ API 오류: {data.get('msg')}")
            elif method == 'POST':
                async with session.post(self.base_url + endpoint, headers=headers, data=body) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('code') == '0':
                            return data['data']
                        else:
                            logger.error(f"❌ API 오류: {data.get('msg')}")
        return None
    
    async def get_order_book(self, symbol):
        """호가창 조회 (4요소 구조 대응)"""
        endpoint = f"/api/v5/market/books?instId={symbol}&sz=10"
        data = await self.make_request('GET', endpoint)
        
        if data:
            order_book = data[0]
            asks = order_book['asks']  # [price, size, ?, ?]
            bids = order_book['bids']  # [price, size, ?, ?]
            
            # 4요소 구조에서 가격과 수량만 추출
            best_ask_price = float(asks[0][0])
            best_ask_size = float(asks[0][1])
            best_bid_price = float(bids[0][0])
            best_bid_size = float(bids[0][1])
            
            logger.info(f"📊 {symbol} 호가창:")
            logger.info(f"   최우선 매도: ${best_ask_price:.5f} ({best_ask_size}개)")
            logger.info(f"   최우선 매수: ${best_bid_price:.5f} ({best_bid_size}개)")
            logger.info(f"   스프레드: ${best_ask_price - best_bid_price:.5f}")
            
            return {
                'asks': asks,
                'bids': bids,
                'best_ask': best_ask_price,
                'best_bid': best_bid_price,
                'spread': best_ask_price - best_bid_price
            }
        return None
    
    async def simulate_buy(self, symbol, amount_usdt):
        """매수 시뮬레이션 (4요소 구조 대응)"""
        order_book = await self.get_order_book(symbol)
        if not order_book:
            return None
        
        asks = order_book['asks']
        remaining_usdt = amount_usdt
        total_size = 0
        weighted_cost = 0
        
        logger.info(f"🧮 매수 시뮬레이션: ${amount_usdt}")
        
        for ask in asks:
            price = float(ask[0])  # 첫 번째 요소: 가격
            available_size = float(ask[1])  # 두 번째 요소: 수량
            
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
            'total_cost': weighted_cost + fee,
            'slippage': abs(avg_price - order_book['best_ask']) / order_book['best_ask'] * 100
        }
        
        logger.info(f"📊 매수 시뮬레이션 결과:")
        logger.info(f"   예상 수량: {total_size:.6f}")
        logger.info(f"   평균 가격: ${avg_price:.5f}")
        logger.info(f"   예상 수수료: ${fee:.4f}")
        logger.info(f"   슬리피지: {result['slippage']:.3f}%")
        
        return result
    
    async def simulate_sell(self, symbol, sell_size):
        """매도 시뮬레이션 (4요소 구조 대응)"""
        order_book = await self.get_order_book(symbol)
        if not order_book:
            return None
        
        bids = order_book['bids']
        remaining_size = sell_size
        total_revenue = 0
        
        logger.info(f"🧮 매도 시뮬레이션: {sell_size:.6f}개")
        
        for bid in bids:
            price = float(bid[0])  # 첫 번째 요소: 가격
            available_size = float(bid[1])  # 두 번째 요소: 수량
            
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
            'net_revenue': total_revenue - fee,
            'slippage': abs(avg_price - order_book['best_bid']) / order_book['best_bid'] * 100
        }
        
        logger.info(f"📊 매도 시뮬레이션 결과:")
        logger.info(f"   예상 수익: ${total_revenue:.4f}")
        logger.info(f"   평균 가격: ${avg_price:.5f}")
        logger.info(f"   예상 수수료: ${fee:.4f}")
        logger.info(f"   순 수익: ${result['net_revenue']:.4f}")
        
        return result
    
    async def get_balance(self, currency):
        """잔고 조회"""
        endpoint = "/api/v5/account/balance"
        data = await self.make_request('GET', endpoint)
        
        if data:
            for account in data:
                for detail in account.get('details', []):
                    if detail['ccy'] == currency:
                        balance = float(detail['availBal'])
                        logger.info(f"💰 {currency} 잔고: {balance:.6f}")
                        return balance
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
                "tgtCcy": "quote_ccy"  # USDT 기준 주문 (중요!)
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
        logger.info(f"📤 {side} 주문 요청: {body}")
        
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
        
        for i in range(30):  # 최대 60초 대기
            order_info = await self.check_order(order_id, symbol)
            
            if order_info:
                state = order_info['state']
                filled = order_info['filled_size']
                price = order_info['avg_price']
                
                logger.info(f"📊 [{i+1:2d}] {state} | 체결: {filled:.6f} | 가격: ${price:.5f}")
                
                if state == 'filled':
                    logger.info(f"✅ 완전 체결!")
                    logger.info(f"   체결량: {filled:.6f}")
                    logger.info(f"   평균가: ${price:.5f}")
                    logger.info(f"   수수료: {order_info['fee']:.6f}")
                    return order_info
                elif state == 'cancelled':
                    logger.error(f"❌ 주문 취소: {order_id}")
                    return None
            
            await asyncio.sleep(2)
        
        logger.error(f"⏰ 체결 타임아웃: {order_id}")
        return None
    
    async def perfect_trade(self, symbol="VENOM-USDT", amount_usdt=10.0, target_profit=0.5, max_time=60):
        """완벽한 거래 실행"""
        logger.info("🏆 완벽한 거래 시작!")
        logger.info("=" * 60)
        logger.info(f"📊 거래 설정:")
        logger.info(f"   코인: {symbol}")
        logger.info(f"   금액: ${amount_usdt}")
        logger.info(f"   목표: {target_profit}%")
        logger.info(f"   시간: {max_time}초")
        logger.info("=" * 60)
        
        try:
            # 1. 사전 검증
            logger.info("🔍 1단계: 사전 검증")
            
            usdt_balance = await self.get_balance('USDT')
            if usdt_balance < amount_usdt:
                logger.error(f"❌ USDT 잔고 부족: {usdt_balance} < {amount_usdt}")
                return None
            
            # 2. 매수 시뮬레이션 및 분석
            logger.info("\n🧮 2단계: 매수 분석")
            buy_sim = await self.simulate_buy(symbol, amount_usdt)
            if not buy_sim:
                logger.error("❌ 매수 시뮬레이션 실패")
                return None
            
            # 손익분기점 계산
            total_fee_rate = self.taker_fee * 2  # 매수 + 매도 수수료
            breakeven_rate = total_fee_rate * 100
            actual_target = target_profit + breakeven_rate
            
            logger.info(f"📊 수익률 분석:")
            logger.info(f"   매수+매도 수수료: {total_fee_rate*100:.2f}%")
            logger.info(f"   손익분기점: {breakeven_rate:.2f}%")
            logger.info(f"   목표 수익률: {target_profit}%")
            logger.info(f"   실제 필요 상승률: {actual_target:.2f}%")
            
            # 3. 매수 실행
            logger.info(f"\n🛒 3단계: 매수 실행")
            buy_order_id = await self.place_order('buy', symbol, amount_usdt)
            
            if not buy_order_id:
                logger.error("❌ 매수 주문 실패")
                return None
            
            buy_result = await self.wait_order_fill(buy_order_id, symbol)
            if not buy_result:
                logger.error("❌ 매수 체결 실패")
                return None
            
            entry_price = buy_result['avg_price']
            position_size = buy_result['filled_size']
            buy_fee = buy_result['fee']
            
            logger.info(f"✅ 매수 완료!")
            logger.info(f"   진입가: ${entry_price:.5f}")
            logger.info(f"   수량: {position_size:.6f}")
            logger.info(f"   수수료: {abs(buy_fee):.6f}")
            
            # 실제 사용 금액 계산
            actual_cost = position_size * entry_price + abs(buy_fee)
            logger.info(f"   실제 비용: ${actual_cost:.4f}")
            
            # 4. 수익률 모니터링
            logger.info(f"\n📊 4단계: 수익률 모니터링 ({max_time}초)")
            start_time = time.time()
            
            target_price = entry_price * (1 + actual_target / 100)
            logger.info(f"🎯 목표가: ${target_price:.5f} (+{actual_target:.2f}%)")
            
            while time.time() - start_time < max_time:
                sell_sim = await self.simulate_sell(symbol, position_size)
                
                if sell_sim:
                    current_price = sell_sim['avg_price']
                    gross_profit_rate = ((current_price - entry_price) / entry_price) * 100
                    
                    # 실제 수익률 계산 (수수료 포함)
                    gross_revenue = sell_sim['total_revenue']
                    sell_fee_estimate = gross_revenue * self.taker_fee
                    net_revenue = gross_revenue - sell_fee_estimate
                    net_profit = net_revenue - actual_cost
                    net_profit_rate = (net_profit / actual_cost) * 100
                    
                    elapsed = int(time.time() - start_time)
                    logger.info(f"[{elapsed:3d}s] ${current_price:.5f} | 가격상승: {gross_profit_rate:+.3f}% | 실수익률: {net_profit_rate:+.3f}%")
                    
                    # 목표 달성 확인
                    if net_profit_rate >= target_profit:
                        logger.info(f"🎉 목표 수익률 달성! ({net_profit_rate:.3f}%)")
                        break
                
                await asyncio.sleep(5)
            
            # 5. 매도 실행
            logger.info(f"\n💸 5단계: 매도 실행")
            logger.info(f"   매도 수량: {position_size:.6f}")
            
            sell_order_id = await self.place_order('sell', symbol, position_size)
            
            if not sell_order_id:
                logger.error("❌ 매도 주문 실패")
                return None
            
            sell_result = await self.wait_order_fill(sell_order_id, symbol)
            if not sell_result:
                logger.error("❌ 매도 체결 실패")
                return None
            
            exit_price = sell_result['avg_price']
            sell_fee = sell_result['fee']
            
            logger.info(f"✅ 매도 완료!")
            logger.info(f"   청산가: ${exit_price:.5f}")
            logger.info(f"   수수료: {abs(sell_fee):.6f}")
            
            # 6. 최종 결과 계산
            logger.info(f"\n📊 6단계: 최종 결과")
            
            gross_revenue = position_size * exit_price
            net_revenue = gross_revenue - abs(sell_fee)
            total_cost = actual_cost
            net_profit = net_revenue - total_cost
            net_profit_rate = (net_profit / total_cost) * 100
            
            total_fees = abs(buy_fee) + abs(sell_fee)
            holding_time = time.time() - start_time
            
            logger.info("=" * 60)
            logger.info("🏆 거래 완료!")
            logger.info(f"📊 진입가: ${entry_price:.5f}")
            logger.info(f"📊 청산가: ${exit_price:.5f}")
            logger.info(f"📊 거래량: {position_size:.6f}")
            logger.info(f"💰 총 비용: ${total_cost:.4f}")
            logger.info(f"💰 총 수익: ${net_revenue:.4f}")
            logger.info(f"💰 순 손익: ${net_profit:+.4f}")
            logger.info(f"📈 순수익률: {net_profit_rate:+.3f}%")
            logger.info(f"💳 총 수수료: ${total_fees:.4f}")
            logger.info(f"⏰ 보유 시간: {holding_time:.1f}초")
            logger.info("=" * 60)
            
            if net_profit > 0:
                logger.info("🎉 수익 실현 성공!")
            else:
                logger.info("📚 거래 경험 완료")
            
            return {
                'success': True,
                'net_profit': net_profit,
                'net_profit_rate': net_profit_rate,
                'total_fees': total_fees,
                'holding_time': holding_time
            }
            
        except Exception as e:
            logger.error(f"❌ 거래 오류: {e}")
            return None

async def main():
    try:
        bot = PerfectTradingBot()
        
        print("🏆 완벽한 거래 봇 v3.0")
        print("✨ 호가창 4요소 구조 완벽 대응")
        print("✨ 수수료 포함 정확한 수익률 계산")
        print("✨ 상세한 시뮬레이션 및 검증")
        
        result = await bot.perfect_trade()
        
        if result and result['success']:
            print(f"\n🎉 거래 성공!")
            print(f"💰 순수익률: {result['net_profit_rate']:+.3f}%")
            print(f"💵 순손익: ${result['net_profit']:+.4f}")
            print(f"⏰ 거래 시간: {result['holding_time']:.1f}초")
        else:
            print(f"\n❌ 거래 실패")
            
    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    asyncio.run(main())