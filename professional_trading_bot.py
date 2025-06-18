# professional_trading_bot.py - 완벽한 검증 시스템을 갖춘 프로페셔널 봇
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
from decimal import Decimal, ROUND_DOWN
from dotenv import load_dotenv

load_dotenv()

# 상세한 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProfessionalTradingBot:
    """완벽한 검증 시스템을 갖춘 프로페셔널 거래 봇"""
    
    def __init__(self, bot_id="test_bot_001"):
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        self.base_url = "https://www.okx.com"
        
        # 봇 전용 포지션 추적
        self.bot_id = bot_id
        self.bot_positions = {}  # {symbol: [positions]}
        self.transaction_log = []  # 모든 거래 기록
        
        # 수수료 설정 (OKX 기준)
        self.maker_fee = 0.0008  # 0.08%
        self.taker_fee = 0.001   # 0.1%
        
        logger.info(f"🤖 프로페셔널 봇 초기화: {self.bot_id}")
    
    async def make_request(self, method, endpoint, body=''):
        """OKX API 요청 (상세 로깅 포함)"""
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
        
        logger.info(f"📡 API 요청: {method} {endpoint}")
        if body:
            logger.info(f"📦 요청 데이터: {body}")
        
        async with aiohttp.ClientSession() as session:
            if method == 'GET':
                async with session.get(self.base_url + endpoint, headers=headers) as response:
                    return await self.handle_response(response, endpoint)
            elif method == 'POST':
                async with session.post(self.base_url + endpoint, headers=headers, data=body) as response:
                    return await self.handle_response(response, endpoint)
    
    async def handle_response(self, response, endpoint):
        """응답 처리 (상세 로깅)"""
        logger.info(f"📥 응답 상태: {response.status}")
        
        if response.status == 200:
            data = await response.json()
            logger.info(f"📄 응답 코드: {data.get('code', 'unknown')}")
            
            if data.get('code') == '0':
                logger.info(f"✅ {endpoint} 성공")
                return data['data']
            else:
                logger.error(f"❌ API 오류: {data.get('msg')}")
                return None
        else:
            error_text = await response.text()
            logger.error(f"❌ HTTP 오류: {response.status} - {error_text}")
            return None
    
    # ============ 1. 주문 전 검증 ============
    
    async def get_order_book(self, symbol, depth=20):
        """호가창 정보 조회"""
        endpoint = f"/api/v5/market/books?instId={symbol}&sz={depth}"
        data = await self.make_request('GET', endpoint)
        
        if data:
            asks = data[0]['asks']  # [[price, size], ...]
            bids = data[0]['bids']
            
            logger.info(f"�� {symbol} 호가창 정보:")
            logger.info(f"   최우선 매도: ${float(asks[0][0]):.5f} ({asks[0][1]}개)")
            logger.info(f"   최우선 매수: ${float(bids[0][0]):.5f} ({bids[0][1]}개)")
            logger.info(f"   스프레드: ${float(asks[0][0]) - float(bids[0][0]):.5f}")
            
            return {
                'asks': asks,
                'bids': bids,
                'spread': float(asks[0][0]) - float(bids[0][0]),
                'best_ask': float(asks[0][0]),
                'best_bid': float(bids[0][0])
            }
        return None
    
    async def simulate_buy_execution(self, symbol, amount_usdt):
        """매수 체결 시뮬레이션 (호가창 기반)"""
        logger.info(f"🧮 매수 시뮬레이션: {symbol} ${amount_usdt}")
        
        order_book = await self.get_order_book(symbol)
        if not order_book:
            return None
        
        asks = order_book['asks']
        remaining_usdt = amount_usdt
        total_size = 0
        weighted_cost = 0
        execution_steps = []
        
        for ask_price, ask_size in asks:
            price = float(ask_price)
            available_size = float(ask_size)
            
            max_buyable_size = remaining_usdt / price
            actual_size = min(max_buyable_size, available_size)
            
            if actual_size > 0:
                cost = actual_size * price
                remaining_usdt -= cost
                total_size += actual_size
                weighted_cost += cost
                
                execution_steps.append({
                    'price': price,
                    'size': actual_size,
                    'cost': cost
                })
                
                logger.info(f"   단계: ${price:.5f} × {actual_size:.3f} = ${cost:.2f}")
                
                if remaining_usdt <= 0.01:  # 1센트 미만 남으면 중단
                    break
        
        avg_price = weighted_cost / amount_usdt if total_size > 0 else 0
        
        # 수수료 계산
        fee = weighted_cost * self.taker_fee
        total_cost = weighted_cost + fee
        
        result = {
            'total_size': total_size,
            'avg_price': avg_price,
            'gross_cost': weighted_cost,
            'fee': fee,
            'total_cost': total_cost,
            'remaining_usdt': remaining_usdt,
            'execution_steps': execution_steps,
            'slippage': abs(avg_price - order_book['best_ask']) / order_book['best_ask'] * 100
        }
        
        logger.info(f"📊 매수 시뮬레이션 결과:")
        logger.info(f"   총 수량: {total_size:.6f}")
        logger.info(f"   평균가: ${avg_price:.5f}")
        logger.info(f"   수수료: ${fee:.4f}")
        logger.info(f"   슬리피지: {result['slippage']:.3f}%")
        
        return result
    
    async def simulate_sell_execution(self, symbol, sell_size):
        """매도 체결 시뮬레이션 (호가창 기반)"""
        logger.info(f"🧮 매도 시뮬레이션: {symbol} {sell_size}")
        
        order_book = await self.get_order_book(symbol)
        if not order_book:
            return None
        
        bids = order_book['bids']
        remaining_size = sell_size
        total_revenue = 0
        execution_steps = []
        
        for bid_price, bid_size in bids:
            price = float(bid_price)
            available_size = float(bid_size)
            
            actual_size = min(remaining_size, available_size)
            
            if actual_size > 0:
                revenue = actual_size * price
                total_revenue += revenue
                remaining_size -= actual_size
                
                execution_steps.append({
                    'price': price,
                    'size': actual_size,
                    'revenue': revenue
                })
                
                logger.info(f"   단계: ${price:.5f} × {actual_size:.3f} = ${revenue:.2f}")
                
                if remaining_size <= 0:
                    break
        
        avg_price = total_revenue / sell_size if sell_size > 0 else 0
        
        # 수수료 계산
        fee = total_revenue * self.taker_fee
        net_revenue = total_revenue - fee
        
        result = {
            'total_revenue': total_revenue,
            'avg_price': avg_price,
            'fee': fee,
            'net_revenue': net_revenue,
            'remaining_size': remaining_size,
            'execution_steps': execution_steps,
            'slippage': abs(avg_price - order_book['best_bid']) / order_book['best_bid'] * 100
        }
        
        logger.info(f"📊 매도 시뮬레이션 결과:")
        logger.info(f"   총 수익: ${total_revenue:.4f}")
        logger.info(f"   평균가: ${avg_price:.5f}")
        logger.info(f"   수수료: ${fee:.4f}")
        logger.info(f"   순수익: ${net_revenue:.4f}")
        
        return result
    
    async def check_account_balance(self, currency=None):
        """계좌 잔고 확인"""
        endpoint = "/api/v5/account/balance"
        data = await self.make_request('GET', endpoint)
        
        if not data:
            return None
        
        balances = {}
        for account in data:
            for detail in account.get('details', []):
                ccy = detail['ccy']
                available = float(detail['availBal'])
                frozen = float(detail['frozenBal'])
                
                balances[ccy] = {
                    'available': available,
                    'frozen': frozen,
                    'total': available + frozen
                }
        
        if currency:
            balance = balances.get(currency, {'available': 0, 'frozen': 0, 'total': 0})
            logger.info(f"💰 {currency} 잔고: {balance['available']:.6f} (사용가능)")
            return balance['available']
        
        return balances
    
    async def check_pending_orders(self, symbol=None):
        """미체결 주문 확인"""
        endpoint = "/api/v5/trade/orders-pending?instType=SPOT"
        if symbol:
            endpoint += f"&instId={symbol}"
        
        data = await self.make_request('GET', endpoint)
        
        if data:
            logger.info(f"⏳ 미체결 주문: {len(data)}개")
            for order in data:
                logger.info(f"   {order['instId']} | {order['side']} | {order['sz']} | {order['state']}")
        
        return data if data else []
    
    def get_bot_position(self, symbol):
        """봇이 보유한 포지션 조회"""
        if symbol not in self.bot_positions:
            return 0
        
        total_size = sum(pos['size'] for pos in self.bot_positions[symbol])
        logger.info(f"🤖 봇 보유 {symbol}: {total_size:.6f}")
        return total_size
    
    # ============ 2. 주문 실행 ============
    
    async def execute_buy_order(self, symbol, amount_usdt):
        """검증된 매수 주문 실행"""
        logger.info(f"🛒 매수 주문 실행 시작: {symbol} ${amount_usdt}")
        
        # 1. 사전 시뮬레이션
        simulation = await self.simulate_buy_execution(symbol, amount_usdt)
        if not simulation:
            logger.error("❌ 매수 시뮬레이션 실패")
            return None
        
        # 2. 실제 주문 실행
        endpoint = "/api/v5/trade/order"
        order_data = {
            "instId": symbol,
            "tdMode": "cash",
            "side": "buy",
            "ordType": "market",
            "sz": str(amount_usdt),  # USDT 금액으로 주문
            "tgtCcy": "quote_ccy"    # 기준 통화로 주문 (중요!)
        }
        
        body = json.dumps(order_data)
        logger.info(f"📤 주문 요청: {body}")
        
        result = await self.make_request('POST', endpoint, body)
        
        if result:
            order_id = result[0]['ordId']
            logger.info(f"✅ 매수 주문 생성: {order_id}")
            
            # 3. 체결 모니터링
            fill_result = await self.monitor_order_execution(order_id, symbol)
            
            if fill_result:
                # 4. 봇 포지션에 기록
                self.add_bot_position(symbol, fill_result)
                return fill_result
        
        logger.error("❌ 매수 주문 실패")
        return None
    
    async def execute_sell_order(self, symbol, sell_size):
        """검증된 매도 주문 실행"""
        logger.info(f"💸 매도 주문 실행 시작: {symbol} {sell_size}")
        
        # 1. 봇 포지션 확인
        bot_balance = self.get_bot_position(symbol)
        if sell_size > bot_balance:
            logger.error(f"❌ 봇 보유량 부족: {bot_balance} < {sell_size}")
            return None
        
        # 2. 사전 시뮬레이션
        simulation = await self.simulate_sell_execution(symbol, sell_size)
        if not simulation:
            logger.error("❌ 매도 시뮬레이션 실패")
            return None
        
        # 3. 실제 주문 실행
        endpoint = "/api/v5/trade/order"
        order_data = {
            "instId": symbol,
            "tdMode": "cash",
            "side": "sell",
            "ordType": "market",
            "sz": str(sell_size)  # 코인 수량으로 주문
        }
        
        body = json.dumps(order_data)
        logger.info(f"📤 주문 요청: {body}")
        
        result = await self.make_request('POST', endpoint, body)
        
        if result:
            order_id = result[0]['ordId']
            logger.info(f"✅ 매도 주문 생성: {order_id}")
            
            # 4. 체결 모니터링
            fill_result = await self.monitor_order_execution(order_id, symbol)
            
            if fill_result:
                # 5. 봇 포지션에서 제거
                self.remove_bot_position(symbol, sell_size)
                return fill_result
        
        logger.error("❌ 매도 주문 실패")
        return None
    
    # ============ 3. 주문 모니터링 ============
    
    async def monitor_order_execution(self, order_id, symbol, timeout=60):
        """주문 체결 모니터링 (상세 로깅)"""
        logger.info(f"👀 주문 체결 모니터링 시작: {order_id}")
        
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            check_count += 1
            endpoint = f"/api/v5/trade/order?instId={symbol}&ordId={order_id}"
            order_info = await self.make_request('GET', endpoint)
            
            if order_info:
                order = order_info[0]
                state = order['state']
                filled_size = float(order['accFillSz'])
                avg_price = float(order['avgPx']) if order['avgPx'] else 0
                fee = float(order['fee']) if order['fee'] else 0
                
                logger.info(f"📊 체결 확인 #{check_count}: {state} | 체결량: {filled_size} | 평균가: ${avg_price:.5f}")
                
                if state == 'filled':
                    logger.info(f"✅ 주문 완전 체결!")
                    logger.info(f"   체결량: {filled_size}")
                    logger.info(f"   평균가: ${avg_price:.5f}")
                    logger.info(f"   수수료: {fee}")
                    
                    # 상세 체결 내역 조회
                    fills = await self.get_order_fills(order_id)
                    
                    return {
                        'order_id': order_id,
                        'filled_size': filled_size,
                        'avg_price': avg_price,
                        'fee': fee,
                        'fills': fills,
                        'status': 'completed'
                    }
                
                elif state == 'partially_filled':
                    logger.info(f"🔄 부분 체결: {filled_size} (계속 대기...)")
                
                elif state == 'cancelled':
                    logger.error(f"❌ 주문 취소됨: {order_id}")
                    return None
            
            await asyncio.sleep(2)
        
        logger.error(f"⏰ 주문 모니터링 타임아웃: {order_id}")
        return None
    
    async def get_order_fills(self, order_id):
        """주문 체결 상세 내역 조회"""
        endpoint = f"/api/v5/trade/fills?ordId={order_id}"
        data = await self.make_request('GET', endpoint)
        
        if data:
            logger.info(f"📋 체결 상세 내역 ({len(data)}개):")
            for fill in data:
                logger.info(f"   ${float(fill['fillPx']):.5f} × {float(fill['fillSz']):.6f} = ${float(fill['fillPx']) * float(fill['fillSz']):.4f}")
        
        return data if data else []
    
    # ============ 4. 포지션 관리 ============
    
    def add_bot_position(self, symbol, fill_result):
        """봇 포지션 추가"""
        if symbol not in self.bot_positions:
            self.bot_positions[symbol] = []
        
        position = {
            'timestamp': time.time(),
            'order_id': fill_result['order_id'],
            'size': fill_result['filled_size'],
            'avg_price': fill_result['avg_price'],
            'fee': fill_result['fee'],
            'side': 'buy'
        }
        
        self.bot_positions[symbol].append(position)
        logger.info(f"📝 봇 포지션 추가: {symbol} +{fill_result['filled_size']:.6f}")
        
        # 거래 로그에 기록
        self.transaction_log.append({
            'timestamp': datetime.now().isoformat(),
            'action': 'buy',
            'symbol': symbol,
            'size': fill_result['filled_size'],
            'price': fill_result['avg_price'],
            'fee': fill_result['fee'],
            'order_id': fill_result['order_id']
        })
    
    def remove_bot_position(self, symbol, sell_size):
        """봇 포지션 제거 (FIFO 방식)"""
        if symbol not in self.bot_positions:
            return
        
        remaining_size = sell_size
        removed_positions = []
        
        # FIFO 방식으로 포지션 제거
        for i, position in enumerate(self.bot_positions[symbol]):
            if remaining_size <= 0:
                break
            
            if position['size'] <= remaining_size:
                # 전체 포지션 제거
                remaining_size -= position['size']
                removed_positions.append(i)
            else:
                # 부분 포지션 제거
                position['size'] -= remaining_size
                remaining_size = 0
        
        # 제거할 포지션들 삭제 (역순으로)
        for i in reversed(removed_positions):
            del self.bot_positions[symbol][i]
        
        logger.info(f"📝 봇 포지션 제거: {symbol} -{sell_size:.6f}")
    
    # ============ 5. 완전한 거래 실행 ============
    
    async def execute_complete_trade(self, symbol, amount_usdt, target_profit_rate=1.0, max_hold_time=300):
        """완전한 거래 실행 (모든 검증 포함)"""
        logger.info("🚀 프로페셔널 거래 시작")
        logger.info("=" * 60)
        logger.info(f"📊 거래 설정:")
        logger.info(f"   코인: {symbol}")
        logger.info(f"   금액: ${amount_usdt}")
        logger.info(f"   목표: {target_profit_rate}%")
        logger.info(f"   최대 시간: {max_hold_time}초")
        logger.info("=" * 60)
        
        try:
            # ========== 주문 전 검증 ==========
            logger.info("🔍 1단계: 주문 전 검증")
            
            # 1.1 계좌 잔고 확인
            usdt_balance = await self.check_account_balance('USDT')
            if usdt_balance < amount_usdt:
                logger.error(f"❌ USDT 잔고 부족: {usdt_balance} < {amount_usdt}")
                return None
            
            # 1.2 기존 미체결 주문 확인
            pending = await self.check_pending_orders(symbol)
            if pending:
                logger.warning(f"⚠️ 기존 미체결 주문 {len(pending)}개 발견")
            
            # 1.3 봇 포지션 확인
            bot_balance = self.get_bot_position(symbol)
            if bot_balance > 0:
                logger.warning(f"⚠️ 기존 봇 포지션: {bot_balance:.6f}")
            
            # 1.4 매수 시뮬레이션
            buy_simulation = await self.simulate_buy_execution(symbol, amount_usdt)
            if not buy_simulation:
                logger.error("❌ 매수 시뮬레이션 실패")
                return None
            
            # 1.5 수익률 계산 (수수료 포함)
            breakeven_rate = (buy_simulation['fee'] / amount_usdt + self.taker_fee) * 100
            actual_target = target_profit_rate + breakeven_rate
            
            logger.info(f"📊 수익률 분석:")
            logger.info(f"   손익분기점: {breakeven_rate:.3f}%")
            logger.info(f"   실제 목표: {actual_target:.3f}%")
            
            # ========== 매수 실행 ==========
            logger.info("\n🛒 2단계: 매수 실행")
            
            buy_result = await self.execute_buy_order(symbol, amount_usdt)
            if not buy_result:
                logger.error("❌ 매수 실행 실패")
                return None
            
            entry_price = buy_result['avg_price']
            position_size = buy_result['filled_size']
            
            logger.info(f"✅ 매수 완료:")
            logger.info(f"   진입가: ${entry_price:.5f}")
            logger.info(f"   수량: {position_size:.6f}")
            logger.info(f"   수수료: ${buy_result['fee']:.4f}")
            
            # ========== 수익률 모니터링 ==========
            logger.info(f"\n📊 3단계: 수익률 모니터링 ({max_hold_time}초)")
            
            start_time = time.time()
            check_interval = 5  # 5초마다 확인
            
            while time.time() - start_time < max_hold_time:
                # 현재 매도 시뮬레이션
                sell_simulation = await self.simulate_sell_execution(symbol, position_size)
                
                if sell_simulation:
                    current_price = sell_simulation['avg_price']
                    gross_profit_rate = ((current_price - entry_price) / entry_price) * 100
                    
                    # 실제 수익률 (수수료 포함)
                    net_revenue = sell_simulation['net_revenue']
                    total_cost = amount_usdt + buy_result['fee']
                    net_profit = net_revenue - total_cost
                    net_profit_rate = (net_profit / total_cost) * 100
                    
                    elapsed = int(time.time() - start_time)
                    logger.info(f"[{elapsed:3d}s] ${current_price:.5f} | 총수익률: {gross_profit_rate:+.3f}% | 순수익률: {net_profit_rate:+.3f}%")
                    
                    # 목표 달성 확인
                    if net_profit_rate >= target_profit_rate:
                        logger.info(f"🎉 목표 수익률 달성! ({net_profit_rate:.3f}%)")
                        break
                
                await asyncio.sleep(check_interval)
            
            # ========== 매도 실행 ==========
            logger.info(f"\n💸 4단계: 매도 실행")
            
            sell_result = await self.execute_sell_order(symbol, position_size)
            if not sell_result:
                logger.error("❌ 매도 실행 실패")
                return None
            
            exit_price = sell_result['avg_price']
            
            # ========== 최종 결과 계산 ==========
            logger.info("\n📊 5단계: 최종 결과 계산")
            
            # 총 비용 및 수익
            total_cost = amount_usdt + buy_result['fee']
            total_revenue = (position_size * exit_price) - sell_result['fee']
            net_profit = total_revenue - total_cost
            net_profit_rate = (net_profit / total_cost) * 100
            
            # 거래 요약
            trade_summary = {
                'symbol': symbol,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'position_size': position_size,
                'total_cost': total_cost,
                'total_revenue': total_revenue,
                'net_profit': net_profit,
                'net_profit_rate': net_profit_rate,
                'buy_fee': buy_result['fee'],
                'sell_fee': sell_result['fee'],
                'total_fees': buy_result['fee'] + sell_result['fee'],
                'holding_time': time.time() - start_time
            }
            
            logger.info("=" * 60)
            logger.info("🏆 거래 완료!")
            logger.info(f"📊 진입가: ${entry_price:.5f}")
            logger.info(f"📊 청산가: ${exit_price:.5f}")
            logger.info(f"📊 거래량: {position_size:.6f}")
            logger.info(f"💰 총 비용: ${total_cost:.4f}")
            logger.info(f"💰 총 수익: ${total_revenue:.4f}")
            logger.info(f"💰 순 손익: ${net_profit:+.4f}")
            logger.info(f"📈 순수익률: {net_profit_rate:+.3f}%")
            logger.info(f"💳 총 수수료: ${trade_summary['total_fees']:.4f}")
            logger.info(f"⏰ 보유 시간: {trade_summary['holding_time']:.1f}초")
            logger.info("=" * 60)
            
            if net_profit > 0:
                logger.info("🎉 수익 실현 성공!")
            else:
                logger.info("📚 거래 경험 완료")
            
            return trade_summary
            
        except Exception as e:
            logger.error(f"❌ 거래 실행 오류: {str(e)}")
            return None

async def main():
    """프로페셔널 봇 테스트 실행"""
    
    print("🏆 프로페셔널 거래 봇 v2.0")
    print("=" * 50)
    print("✨ 특징:")
    print("   📊 호가창 기반 정확한 가격 계산")
    print("   💰 수수료 포함 실제 수익률 계산")
    print("   🤖 봇 전용 포지션 관리")
    print("   📝 상세한 로깅 및 검증")
    print("=" * 50)
    
    # 거래 설정
    symbol = input("거래할 코인 (예: VENOM-USDT): ").strip().upper()
    if not symbol:
        symbol = "VENOM-USDT"
    
    try:
        amount_str = input("거래 금액 (USDT, 기본값 5): ").strip()
        amount_usdt = float(amount_str) if amount_str else 5.0
    except:
        amount_usdt = 5.0
    
    try:
        target_str = input("목표 수익률 (%, 기본값 1.0): ").strip()
        target_profit = float(target_str) if target_str else 1.0
    except:
        target_profit = 1.0
    
    try:
        time_str = input("최대 보유 시간 (초, 기본값 120): ").strip()
        max_time = int(time_str) if time_str else 120
    except:
        max_time = 120
    
    print(f"\n📋 거래 설정 확인:")
    print(f"   코인: {symbol}")
    print(f"   금액: ${amount_usdt}")
    print(f"   목표: {target_profit}%")
    print(f"   시간: {max_time}초")
    
    confirm = input("\n실행하시겠습니까? (yes): ").strip().lower()
    if confirm != 'yes':
        print("❌ 거래 취소")
        return
    
    # 봇 생성 및 실행
    bot = ProfessionalTradingBot("PRO_BOT_001")
    
    try:
        result = await bot.execute_complete_trade(
            symbol=symbol,
            amount_usdt=amount_usdt,
            target_profit_rate=target_profit,
            max_hold_time=max_time
        )
        
        if result:
            print(f"\n🎉 거래 성공!")
            print(f"💰 최종 수익률: {result['net_profit_rate']:+.3f}%")
            print(f"💵 순 손익: ${result['net_profit']:+.4f}")
            
            # 거래 로그 파일 안내
            print(f"\n📝 상세 로그: trading_bot.log 파일 확인")
            
        else:
            print(f"\n❌ 거래 실패")
            
    except KeyboardInterrupt:
        print(f"\n⏹️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")

if __name__ == "__main__":
    asyncio.run(main())
