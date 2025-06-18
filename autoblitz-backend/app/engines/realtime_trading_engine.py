# 🔄 실시간 거래 엔진 (Real-time Trading Engine)

"""
app/engines/realtime_trading_engine.py

실시간 시장 데이터를 받아서 단타로 전략을 실행하는 메인 엔진
- WebSocket을 통한 실시간 가격 수신
- 다중 코인 동시 모니터링 및 거래
- 자동 주문 실행 및 포지션 관리
- 실시간 성과 추적 및 리포팅
"""

import asyncio
import logging
import json
import websockets
from typing import Dict, List, Optional, Set, Callable
from datetime import datetime, timedelta
import aiohttp
from dataclasses import dataclass, asdict
from decimal import Decimal
import signal
import sys

from app.strategies.dantaro.okx_spot_v1_complete import DantaroOKXSpotV1Complete, create_dantaro_strategy
from app.exchanges.okx.client import OKXClient
from app.models.trading import Order, Position, TradingSignal

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """시장 데이터 구조"""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    
    def to_dict(self):
        return asdict(self)

@dataclass
class TradingResult:
    """거래 결과 구조"""
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    price: float
    quantity: float
    profit_rate: Optional[float] = None
    reason: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class RealtimeTradingEngine:
    """실시간 거래 엔진 메인 클래스"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.is_running = False
        self.strategies: Dict[str, DantaroOKXSpotV1Complete] = {}
        self.market_data: Dict[str, MarketData] = {}
        self.last_signals: Dict[str, datetime] = {}
        
        # OKX 클라이언트
        self.okx_client = OKXClient(
            api_key=config.get('okx_api_key'),
            secret_key=config.get('okx_secret_key'),
            passphrase=config.get('okx_passphrase'),
            sandbox=config.get('sandbox', True)  # 기본값은 테스트넷
        )
        
        # WebSocket 연결
        self.ws_connection = None
        self.subscribed_symbols: Set[str] = set()
        
        # 성과 추적
        self.trading_results: List[TradingResult] = []
        self.total_trades = 0
        self.successful_trades = 0
        self.total_profit = 0.0
        
        # 제어 플래그
        self.emergency_stop = False
        self.max_daily_trades = config.get('max_daily_trades', 100)
        self.min_signal_interval = config.get('min_signal_interval', 60)  # 60초
        
        # 이벤트 콜백
        self.on_trade_executed: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_status_update: Optional[Callable] = None
        
        logger.info("실시간 거래 엔진 초기화 완료")
    
    async def add_strategy(self, symbol: str, capital: float, strategy_config: Dict = None):
        """거래 전략 추가"""
        try:
            strategy = create_dantaro_strategy(symbol, capital, strategy_config)
            self.strategies[symbol] = strategy
            self.subscribed_symbols.add(symbol)
            
            logger.info(f"전략 추가 완료: {symbol}, 자본금: {capital} USDT")
            
            # WebSocket 구독 업데이트
            if self.ws_connection:
                await self._subscribe_symbol(symbol)
                
        except Exception as e:
            logger.error(f"전략 추가 실패: {symbol}, 오류: {e}")
            raise
    
    async def remove_strategy(self, symbol: str):
        """거래 전략 제거"""
        try:
            if symbol in self.strategies:
                # 기존 포지션 있으면 강제 청산
                strategy = self.strategies[symbol]
                if strategy.current_position:
                    logger.warning(f"포지션 보유 중인 전략 제거: {symbol}, 강제 청산 실행")
                    current_price = self.market_data.get(symbol, {}).get('price', 0)
                    if current_price > 0:
                        await strategy.execute_sell(current_price, {})
                
                del self.strategies[symbol]
                self.subscribed_symbols.discard(symbol)
                
                logger.info(f"전략 제거 완료: {symbol}")
        except Exception as e:
            logger.error(f"전략 제거 실패: {symbol}, 오류: {e}")
    
    async def start(self):
        """거래 엔진 시작"""
        try:
            self.is_running = True
            self.emergency_stop = False
            
            logger.info("🚀 실시간 거래 엔진 시작")
            
            # WebSocket 연결 시작
            asyncio.create_task(self._start_websocket())
            
            # 메인 거래 루프 시작
            asyncio.create_task(self._trading_loop())
            
            # 성과 추적 루프 시작
            asyncio.create_task(self._performance_tracking_loop())
            
            logger.info("모든 백그라운드 작업 시작 완료")
            
        except Exception as e:
            logger.error(f"거래 엔진 시작 실패: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """거래 엔진 중지"""
        try:
            logger.info("🛑 실시간 거래 엔진 중지 중...")
            
            self.is_running = False
            self.emergency_stop = True
            
            # 모든 포지션 강제 청산
            await self._emergency_close_all_positions()
            
            # WebSocket 연결 종료
            if self.ws_connection:
                await self.ws_connection.close()
            
            logger.info("거래 엔진 중지 완료")
            
        except Exception as e:
            logger.error(f"거래 엔진 중지 중 오류: {e}")
    
    async def _start_websocket(self):
        """WebSocket 연결 및 데이터 수신"""
        okx_ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        if self.config.get('sandbox', True):
            okx_ws_url = "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999"
        
        try:
            while self.is_running:
                try:
                    async with websockets.connect(okx_ws_url) as websocket:
                        self.ws_connection = websocket
                        logger.info("✅ OKX WebSocket 연결 성공")
                        
                        # 구독 메시지 전송
                        await self._subscribe_all_symbols()
                        
                        # 메시지 수신 루프
                        async for message in websocket:
                            if not self.is_running:
                                break
                                
                            try:
                                await self._handle_websocket_message(message)
                            except Exception as e:
                                logger.error(f"WebSocket 메시지 처리 오류: {e}")
                                
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket 연결 끊김, 재연결 시도...")
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"WebSocket 연결 오류: {e}")
                    await asyncio.sleep(10)
                    
        except Exception as e:
            logger.error(f"WebSocket 처리 중 심각한 오류: {e}")
    
    async def _subscribe_all_symbols(self):
        """모든 구독 심볼에 대해 WebSocket 구독"""
        if not self.subscribed_symbols:
            return
        
        # 티커 데이터 구독
        channels = []
        for symbol in self.subscribed_symbols:
            channels.append({"channel": "tickers", "instId": symbol})
        
        subscribe_msg = {
            "op": "subscribe",
            "args": channels
        }
        
        await self.ws_connection.send(json.dumps(subscribe_msg))
        logger.info(f"WebSocket 구독 완료: {list(self.subscribed_symbols)}")
    
    async def _subscribe_symbol(self, symbol: str):
        """개별 심볼 WebSocket 구독"""
        if not self.ws_connection:
            return
        
        subscribe_msg = {
            "op": "subscribe",
            "args": [{"channel": "tickers", "instId": symbol}]
        }
        
        await self.ws_connection.send(json.dumps(subscribe_msg))
        logger.info(f"심볼 구독 추가: {symbol}")
    
    async def _handle_websocket_message(self, message: str):
        """WebSocket 메시지 처리"""
        try:
            data = json.loads(message)
            
            # 성공 메시지 처리
            if data.get('event') == 'subscribe':
                logger.debug(f"구독 확인: {data}")
                return
            
            # 티커 데이터 처리
            if 'data' in data and data.get('arg', {}).get('channel') == 'tickers':
                for ticker_data in data['data']:
                    await self._process_ticker_data(ticker_data)
                    
        except json.JSONDecodeError:
            logger.warning(f"잘못된 JSON 메시지: {message[:100]}")
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")
    
    async def _process_ticker_data(self, ticker_data: Dict):
        """티커 데이터 처리 및 시장 데이터 업데이트"""
        try:
            symbol = ticker_data.get('instId')
            if not symbol or symbol not in self.strategies:
                return
            
            # 시장 데이터 업데이트
            market_data = MarketData(
                symbol=symbol,
                price=float(ticker_data.get('last', 0)),
                volume=float(ticker_data.get('vol24h', 0)),
                bid=float(ticker_data.get('bidPx', 0)) if ticker_data.get('bidPx') else None,
                ask=float(ticker_data.get('askPx', 0)) if ticker_data.get('askPx') else None,
                timestamp=datetime.now()
            )
            
            self.market_data[symbol] = market_data
            
            # 거래 신호 처리는 별도 루프에서 처리 (빠른 데이터 수신을 위해)
            
        except Exception as e:
            logger.error(f"티커 데이터 처리 오류: {e}")
    
    async def _trading_loop(self):
        """메인 거래 루프"""
        logger.info("📈 거래 루프 시작")
        
        while self.is_running and not self.emergency_stop:
            try:
                # 모든 전략에 대해 거래 신호 확인
                for symbol, strategy in self.strategies.items():
                    if symbol not in self.market_data:
                        continue
                    
                    # 최소 신호 간격 확인
                    last_signal_time = self.last_signals.get(symbol)
                    if last_signal_time:
                        time_diff = (datetime.now() - last_signal_time).total_seconds()
                        if time_diff < self.min_signal_interval:
                            continue
                    
                    # 일일 거래 횟수 제한 확인
                    if self.total_trades >= self.max_daily_trades:
                        logger.warning("일일 최대 거래 횟수 도달")
                        continue
                    
                    await self._process_trading_signals(symbol, strategy)
                
                # 0.5초 대기 (너무 빠른 루프 방지)
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"거래 루프 오류: {e}")
                await asyncio.sleep(1)
    
    async def _process_trading_signals(self, symbol: str, strategy: DantaroOKXSpotV1Complete):
        """거래 신호 처리"""
        try:
            market_data = self.market_data[symbol]
            current_price = market_data.price
            
            if current_price <= 0:
                return
            
            market_dict = market_data.to_dict()
            
            # 매도 신호 먼저 확인 (기존 포지션 있는 경우)
            if strategy.current_position:
                should_sell, sell_reason = await strategy.should_sell(current_price, market_dict)
                
                if should_sell:
                    await self._execute_sell_order(symbol, strategy, current_price, sell_reason)
                    self.last_signals[symbol] = datetime.now()
                    return
            
            # 매수 신호 확인 (포지션 없는 경우)
            else:
                should_buy, buy_reason = await strategy.should_buy(current_price, market_dict)
                
                if should_buy:
                    await self._execute_buy_order(symbol, strategy, current_price, buy_reason)
                    self.last_signals[symbol] = datetime.now()
                    return
                    
        except Exception as e:
            logger.error(f"거래 신호 처리 오류 ({symbol}): {e}")
    
    async def _execute_buy_order(self, symbol: str, strategy: DantaroOKXSpotV1Complete, price: float, reason: str):
        """매수 주문 실행"""
        try:
            # 포지션 크기 계산
            quantity = await strategy.calculate_position_size(price, {})
            
            if quantity <= 0:
                logger.warning(f"매수 주문 취소 - 수량 부족: {symbol}")
                return
            
            # 실제 주문 실행 (테스트 모드에서는 시뮬레이션)
            if self.config.get('sandbox', True):
                # 시뮬레이션 매수
                order = await strategy.execute_buy(price, quantity, {})
                success = True
            else:
                # 실제 매수 주문
                order_result = await self.okx_client.place_order(
                    symbol=symbol,
                    side='buy',
                    order_type='market',
                    quantity=quantity
                )
                success = order_result.get('success', False)
                order = await strategy.execute_buy(price, quantity, {}) if success else None
            
            if success and order:
                # 거래 결과 기록
                result = TradingResult(
                    symbol=symbol,
                    action='buy',
                    price=price,
                    quantity=quantity,
                    reason=reason
                )
                
                self.trading_results.append(result)
                self.total_trades += 1
                
                logger.info(f"✅ 매수 주문 성공: {symbol} {quantity} @ {price} ({reason})")
                
                # 콜백 호출
                if self.on_trade_executed:
                    await self.on_trade_executed(result)
            else:
                logger.error(f"❌ 매수 주문 실패: {symbol}")
                
        except Exception as e:
            logger.error(f"매수 주문 실행 오류 ({symbol}): {e}")
            if self.on_error:
                await self.on_error(f"매수 오류: {e}")
    
    async def _execute_sell_order(self, symbol: str, strategy: DantaroOKXSpotV1Complete, price: float, reason: str):
        """매도 주문 실행"""
        try:
            if not strategy.current_position:
                return
            
            quantity = strategy.current_position.quantity
            entry_price = strategy.entry_price
            
            # 실제 주문 실행 (테스트 모드에서는 시뮬레이션)
            if self.config.get('sandbox', True):
                # 시뮬레이션 매도
                order = await strategy.execute_sell(price, {})
                success = True
            else:
                # 실제 매도 주문
                order_result = await self.okx_client.place_order(
                    symbol=symbol,
                    side='sell',
                    order_type='market',
                    quantity=quantity
                )
                success = order_result.get('success', False)
                order = await strategy.execute_sell(price, {}) if success else None
            
            if success and order:
                # 수익률 계산
                profit_rate = ((price - entry_price) / entry_price) * 100
                profit_amount = (price - entry_price) * quantity
                
                # 거래 결과 기록
                result = TradingResult(
                    symbol=symbol,
                    action='sell',
                    price=price,
                    quantity=quantity,
                    profit_rate=profit_rate,
                    reason=reason
                )
                
                self.trading_results.append(result)
                self.total_trades += 1
                
                if profit_rate > 0:
                    self.successful_trades += 1
                    self.total_profit += profit_amount
                
                logger.info(f"✅ 매도 주문 성공: {symbol} {quantity} @ {price}, 수익률: {profit_rate:.2f}% ({reason})")
                
                # 콜백 호출
                if self.on_trade_executed:
                    await self.on_trade_executed(result)
            else:
                logger.error(f"❌ 매도 주문 실패: {symbol}")
                
        except Exception as e:
            logger.error(f"매도 주문 실행 오류 ({symbol}): {e}")
            if self.on_error:
                await self.on_error(f"매도 오류: {e}")
    
    async def _emergency_close_all_positions(self):
        """긴급 상황 시 모든 포지션 강제 청산"""
        logger.warning("🚨 긴급 포지션 청산 시작")
        
        for symbol, strategy in self.strategies.items():
            if strategy.current_position and symbol in self.market_data:
                try:
                    current_price = self.market_data[symbol].price
                    await strategy.execute_sell(current_price, {})
                    logger.info(f"긴급 청산 완료: {symbol}")
                except Exception as e:
                    logger.error(f"긴급 청산 실패 ({symbol}): {e}")
    
    async def _performance_tracking_loop(self):
        """성과 추적 루프"""
        logger.info("📊 성과 추적 시작")
        
        while self.is_running:
            try:
                # 1분마다 성과 업데이트
                await asyncio.sleep(60)
                
                if self.on_status_update:
                    status = await self.get_performance_summary()
                    await self.on_status_update(status)
                    
            except Exception as e:
                logger.error(f"성과 추적 오류: {e}")
    
    async def get_performance_summary(self) -> Dict:
        """성과 요약 반환"""
        try:
            # 기본 통계
            win_rate = (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            
            # 활성 포지션 수
            active_positions = sum(1 for strategy in self.strategies.values() if strategy.current_position)
            
            # 현재 미실현 손익
            unrealized_pnl = 0.0
            for symbol, strategy in self.strategies.items():
                if strategy.current_position and symbol in self.market_data:
                    current_price = self.market_data[symbol].price
                    entry_price = strategy.entry_price
                    if current_price > 0 and entry_price > 0:
                        pnl = (current_price - entry_price) * strategy.current_position.quantity
                        unrealized_pnl += pnl
            
            # 오늘 거래 내역
            today = datetime.now().date()
            today_trades = [r for r in self.trading_results if r.timestamp.date() == today]
            today_profit = sum(((r.profit_rate or 0) / 100) * (r.price * r.quantity) for r in today_trades if r.action == 'sell')
            
            return {
                'engine_status': 'running' if self.is_running else 'stopped',
                'total_strategies': len(self.strategies),
                'active_positions': active_positions,
                'total_trades': self.total_trades,
                'successful_trades': self.successful_trades,
                'win_rate': round(win_rate, 2),
                'total_profit': round(self.total_profit, 2),
                'unrealized_pnl': round(unrealized_pnl, 2),
                'today_trades': len(today_trades),
                'today_profit': round(today_profit, 2),
                'emergency_stop': self.emergency_stop,
                'subscribed_symbols': list(self.subscribed_symbols),
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"성과 요약 생성 오류: {e}")
            return {'error': str(e)}
    
    async def get_strategy_status(self, symbol: str) -> Optional[Dict]:
        """특정 전략 상태 조회"""
        if symbol not in self.strategies:
            return None
        
        try:
            strategy = self.strategies[symbol]
            status = await strategy.get_strategy_status()
            
            # 시장 데이터 추가
            if symbol in self.market_data:
                market_data = self.market_data[symbol]
                status['market_data'] = {
                    'current_price': market_data.price,
                    'volume': market_data.volume,
                    'bid': market_data.bid,
                    'ask': market_data.ask,
                    'last_update': market_data.timestamp.isoformat()
                }
            
            return status
            
        except Exception as e:
            logger.error(f"전략 상태 조회 오류 ({symbol}): {e}")
            return None


# 엔진 컨트롤러 및 시그널 핸들러
class TradingEngineController:
    """거래 엔진 제어 클래스"""
    
    def __init__(self, config: Dict):
        self.engine = RealtimeTradingEngine(config)
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """시그널 핸들러 설정 (Ctrl+C 등)"""
        def signal_handler(signum, frame):
            logger.info("종료 신호 받음, 안전하게 종료 중...")
            asyncio.create_task(self.engine.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run_with_strategies(self, strategies_config: List[Dict]):
        """전략들과 함께 엔진 실행"""
        try:
            # 전략들 추가
            for config in strategies_config:
                await self.engine.add_strategy(
                    symbol=config['symbol'],
                    capital=config['capital'],
                    strategy_config=config.get('strategy_config')
                )
            
            # 엔진 시작
            await self.engine.start()
            
            # 무한 대기 (시그널까지)
            while self.engine.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("사용자에 의한 종료")
        except Exception as e:
            logger.error(f"엔진 실행 오류: {e}")
        finally:
            await self.engine.stop()


# 사용 예시 및 테스트
async def example_usage():
    """실시간 거래 엔진 사용 예시"""
    
    # 엔진 설정
    config = {
        'okx_api_key': 'your_api_key',
        'okx_secret_key': 'your_secret_key', 
        'okx_passphrase': 'your_passphrase',
        'sandbox': True,  # 테스트넷 사용
        'max_daily_trades': 50,
        'min_signal_interval': 30  # 30초
    }
    
    # 거래할 전략들 설정
    strategies_config = [
        {
            'symbol': 'BTC-USDT',
            'capital': 1000.0,
            'strategy_config': {
                'profit_target': 1.3,
                'stop_loss': -2.0
            }
        },
        {
            'symbol': 'ETH-USDT', 
            'capital': 500.0,
            'strategy_config': {
                'profit_target': 1.5,
                'stop_loss': -1.5
            }
        }
    ]
    
    # 엔진 컨트롤러 생성 및 실행
    controller = TradingEngineController(config)
    
    # 콜백 함수 설정
    async def on_trade_executed(result: TradingResult):
        print(f"🎯 거래 실행: {result.symbol} {result.action} @ {result.price}")
    
    async def on_error(error_msg: str):
        print(f"❌ 오류 발생: {error_msg}")
    
    async def on_status_update(status: Dict):
        print(f"📊 상태 업데이트: 총 거래 {status['total_trades']}, 승률 {status['win_rate']}%")
    
    controller.engine.on_trade_executed = on_trade_executed
    controller.engine.on_error = on_error
    controller.engine.on_status_update = on_status_update
    
    # 엔진 실행
    await controller.run_with_strategies(strategies_config)


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 예시 실행
    asyncio.run(example_usage())