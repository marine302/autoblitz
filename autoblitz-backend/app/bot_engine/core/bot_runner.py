# app/bot_engine/core/bot_runner.py (완전 재작성)

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from decimal import Decimal
from enum import Enum

from app.bot_engine.executors.strategy_executor import StrategyExecutor, create_strategy_executor
from app.bot_engine.executors.order_executor import OrderExecutor, create_order_executor
from app.bot_engine.managers.position_manager import PositionManager, create_position_manager
from app.bot_engine.managers.risk_manager import RiskManager, create_risk_manager
from app.exchanges.okx.client import create_okx_client

logger = logging.getLogger(__name__)


class BotState(Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class BotRunner:
    """완전한 봇 러너 - 모든 컴포넌트를 통합하여 실제 자동매매 실행"""

    def __init__(self, bot_id: int, user_id: int, config: Dict[str, Any]):
        self.bot_id = bot_id
        self.user_id = user_id
        self.config = config
        self.state = BotState.IDLE

        # 기본 설정
        self.symbol = config['symbol']
        self.strategy_name = config['strategy']
        self.capital = Decimal(str(config['capital']))
        self.exchange_name = config['exchange']

        # 핵심 컴포넌트들
        self.exchange_client = None
        self.strategy_executor = None
        self.order_executor = None
        self.position_manager = None
        self.risk_manager = None

        # 실행 제어
        self._stop_requested = False
        self._graceful_stop_requested = False
        self._paused = False
        self._running = False

        # 상태 추적
        self.start_time = None
        self.last_tick_time = None
        self.last_price = None
        self.tick_count = 0
        self.error_count = 0

        # 성능 설정
        self.tick_interval = 5.0  # 5초마다 실행
        self.heartbeat_interval = 60.0  # 1분마다 상태 저장
        self.price_update_interval = 10.0  # 10초마다 가격 업데이트

        # 통계
        self.total_trades = 0
        self.successful_trades = 0
        self.total_profit = Decimal('0')

    async def initialize(self):
        """봇 러너 전체 초기화"""
        try:
            logger.info(f"봇 {self.bot_id} 초기화 시작")
            self.state = BotState.INITIALIZING

            # 1. 거래소 클라이언트 초기화
            await self._initialize_exchange_client()

            # 2. 핵심 컴포넌트들 초기화
            await self._initialize_components()

            # 3. 초기 상태 설정
            await self._setup_initial_state()

            self.state = BotState.IDLE
            logger.info(f"봇 {self.bot_id} 초기화 완료")

        except Exception as e:
            logger.error(f"봇 {self.bot_id} 초기화 실패: {e}")
            self.state = BotState.ERROR
            raise

    async def _initialize_exchange_client(self):
        """거래소 클라이언트 초기화"""
        try:
            if self.exchange_name.lower() == 'okx':
                # 환경변수 또는 사용자 설정에서 API 키 로드
                api_keys = self._get_api_keys()
                if not api_keys:
                    # 테스트 모드 (더미 클라이언트)
                    self.exchange_client = DummyExchangeClient()
                    logger.info("테스트 모드: 더미 거래소 클라이언트 사용")
                else:
                    self.exchange_client = await create_okx_client(
                        api_keys['api_key'],
                        api_keys['secret_key'],
                        api_keys['passphrase'],
                        sandbox=True  # 초기에는 항상 테스트넷
                    )
                    logger.info("OKX 클라이언트 초기화 완료")
            else:
                raise ValueError(f"지원하지 않는 거래소: {self.exchange_name}")

        except Exception as e:
            logger.error(f"거래소 클라이언트 초기화 실패: {e}")
            # 실패 시 더미 클라이언트로 대체
            self.exchange_client = DummyExchangeClient()
            logger.info("더미 클라이언트로 대체")

    async def _initialize_components(self):
        """핵심 컴포넌트들 초기화"""
        try:
            # 전략 설정에 capital 추가
            strategy_settings = self.config.get('strategy_settings', {}).copy()
            strategy_settings['capital'] = float(self.capital)  # capital 추가

            # 전략 실행기
            self.strategy_executor = create_strategy_executor(
                self.strategy_name,
                self.exchange_client,
                self.symbol,
                strategy_settings  # 수정된 설정 전달
            )
            await self.strategy_executor.initialize()

            # 주문 실행기
            self.order_executor = create_order_executor(
                self.exchange_client,
                self.symbol
            )

            # 포지션 매니저
            self.position_manager = create_position_manager(
                self.bot_id,
                float(self.capital),
                self.exchange_client,
                self.symbol
            )
            await self.position_manager.initialize()

            # 리스크 매니저
            self.risk_manager = create_risk_manager(
                float(self.capital),
                self.config.get('risk_settings', {})
            )

            logger.info("모든 컴포넌트 초기화 완료")

        except Exception as e:
            logger.error(f"컴포넌트 초기화 실패: {e}")
            raise

    async def _setup_initial_state(self):
        """초기 상태 설정"""
        try:
            # 현재 시장 가격 조회
            ticker = await self.exchange_client.get_ticker(self.symbol)
            if ticker:
                self.last_price = Decimal(str(ticker['last']))
                logger.info(f"현재 가격: {self.last_price}")

            # 기존 포지션 복구 (있다면)
            # 실제 구현에서는 데이터베이스에서 로드

        except Exception as e:
            logger.warning(f"초기 상태 설정 실패: {e}")
            # 실패해도 계속 진행

    async def run(self):
        """봇 메인 실행 루프"""
        try:
            logger.info(f"봇 {self.bot_id} 실행 시작")
            self.state = BotState.RUNNING
            self._running = True
            self.start_time = datetime.now(timezone.utc)

            # 백그라운드 태스크들 시작
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            price_update_task = asyncio.create_task(self._price_update_loop())

            # 메인 거래 루프
            main_task = asyncio.create_task(self._main_trading_loop())

            try:
                # 모든 태스크 병렬 실행
                await asyncio.gather(heartbeat_task, price_update_task, main_task)
            except asyncio.CancelledError:
                logger.info(f"봇 {self.bot_id} 실행 취소됨")
            finally:
                # 정리 작업
                await self._cleanup_tasks([heartbeat_task, price_update_task, main_task])

        except Exception as e:
            logger.error(f"봇 {self.bot_id} 실행 중 오류: {e}")
            self.state = BotState.ERROR
            self.error_count += 1
            raise
        finally:
            self._running = False
            if self.state != BotState.ERROR:
                self.state = BotState.STOPPED
            await self._final_cleanup()
            logger.info(f"봇 {self.bot_id} 실행 종료")

    async def _main_trading_loop(self):
        """메인 거래 루프"""
        while not self._stop_requested:
            try:
                self.tick_count += 1
                self.last_tick_time = datetime.now(timezone.utc)

                # 일시정지 상태 확인
                if self._paused:
                    await asyncio.sleep(self.tick_interval)
                    continue

                # 정상 종료 요청 확인 (포지션이 없을 때만)
                if self._graceful_stop_requested:
                    has_position = await self.position_manager.has_open_position()
                    if not has_position:
                        logger.info(f"봇 {self.bot_id} 정상 종료 조건 만족")
                        break

                # 1. 현재 시장 상황 분석
                market_data = await self._get_market_data()
                if not market_data:
                    await asyncio.sleep(self.tick_interval * 2)
                    continue

                current_price = Decimal(str(market_data['ticker']['last']))
                self.last_price = current_price

                # 2. 리스크 체크
                position = await self.position_manager.get_current_position()
                risk_result = await self.risk_manager.check_risk(
                    current_price,
                    position,
                    self.total_profit
                )

                # 리스크 대응
                if risk_result.should_stop:
                    logger.critical(
                        f"봇 {self.bot_id} 리스크 중지: {risk_result.reason}")
                    await self._emergency_stop(risk_result.reason)
                    break

                if risk_result.should_close_position:
                    logger.warning(
                        f"봇 {self.bot_id} 포지션 강제 청산: {risk_result.reason}")
                    await self._close_all_positions("리스크 관리")

                if risk_result.should_pause:
                    logger.warning(
                        f"봇 {self.bot_id} 일시정지: {risk_result.reason}")
                    await self.pause()
                    continue

                # 3. 전략 신호 생성
                signal = await self.strategy_executor.get_signal(
                    current_price,
                    position,
                    market_data
                )

                # 4. 신호에 따른 주문 실행
                if signal.action == "BUY":
                    await self._execute_buy_signal(signal, current_price)
                elif signal.action == "SELL":
                    await self._execute_sell_signal(signal, current_price)
                elif signal.action == "HOLD":
                    # 기존 주문 상태만 업데이트
                    await self._update_orders()

                # 5. 포지션 상태 업데이트
                await self.position_manager.update_position(current_price)

                # 6. 수익/손실 업데이트
                await self._update_performance()

                # 다음 틱까지 대기
                await asyncio.sleep(self.tick_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"봇 {self.bot_id} 거래 루프 오류: {e}")
                self.error_count += 1

                # 연속 오류가 많으면 중지
                if self.error_count >= 5:
                    logger.critical(f"봇 {self.bot_id} 연속 오류로 중지")
                    await self._emergency_stop("연속 오류 발생")
                    break

                await asyncio.sleep(self.tick_interval * 2)

    async def _execute_buy_signal(self, signal, current_price):
        """매수 신호 실행"""
        try:
            strategy_info = {
                'grid_level': signal.grid_level,
                'strategy': self.strategy_name,
                'reason': signal.reason
            }

            # 주문 생성
            if signal.order_type == "MARKET":
                order = await self.order_executor.create_market_order(
                    side="buy",
                    quantity=signal.quantity,
                    strategy_info=strategy_info
                )
            else:
                order = await self.order_executor.create_limit_order(
                    side="buy",
                    quantity=signal.quantity,
                    price=signal.price,
                    strategy_info=strategy_info
                )

            if order:
                # 포지션 매니저에 등록
                await self.position_manager.add_buy_order(order)
                logger.info(f"봇 {self.bot_id} 매수 주문 실행: {order.order_id}")

                # 통계 업데이트
                self.total_trades += 1

        except Exception as e:
            logger.error(f"봇 {self.bot_id} 매수 신호 실행 실패: {e}")

    async def _execute_sell_signal(self, signal, current_price):
        """매도 신호 실행"""
        try:
            strategy_info = {
                'grid_level': signal.grid_level,
                'strategy': self.strategy_name,
                'reason': signal.reason
            }

            # 주문 생성
            if signal.order_type == "MARKET":
                order = await self.order_executor.create_market_order(
                    side="sell",
                    quantity=signal.quantity,
                    strategy_info=strategy_info
                )
            else:
                order = await self.order_executor.create_limit_order(
                    side="sell",
                    quantity=signal.quantity,
                    price=signal.price,
                    strategy_info=strategy_info
                )

            if order:
                # 포지션 매니저에 등록
                await self.position_manager.add_sell_order(order)
                logger.info(f"봇 {self.bot_id} 매도 주문 실행: {order.order_id}")

                # 통계 업데이트
                self.total_trades += 1

        except Exception as e:
            logger.error(f"봇 {self.bot_id} 매도 신호 실행 실패: {e}")

    async def _update_orders(self):
        """주문 상태 업데이트"""
        try:
            # 미체결 주문들 상태 확인
            open_orders = await self.position_manager.get_open_orders()

            for order in open_orders:
                updated_order = await self.order_executor.get_order_status(order.order_id)
                if updated_order:
                    await self.position_manager.update_order_status(updated_order)

                    # 체결된 주문 처리
                    if updated_order.status.value == "filled":
                        await self._on_order_filled(updated_order)

        except Exception as e:
            logger.error(f"봇 {self.bot_id} 주문 상태 업데이트 실패: {e}")

    async def _on_order_filled(self, order):
        """주문 체결 시 처리"""
        try:
            if order.side.value == "sell":
                # 매도 체결 시 수익 기록
                profit = await self.position_manager.calculate_cycle_profit(order)
                self.total_profit += profit
                self.risk_manager.record_trade(profit)

                if profit > 0:
                    self.successful_trades += 1

                logger.info(f"봇 {self.bot_id} 매도 체결: 수익 {profit} USDT")

        except Exception as e:
            logger.error(f"봇 {self.bot_id} 주문 체결 처리 실패: {e}")

    async def _update_performance(self):
        """성과 업데이트"""
        try:
            # 미실현 손익 업데이트
            if self.last_price:
                unrealized_pnl = await self.position_manager.get_unrealized_pnl(self.last_price)

                # 전체 손익 = 실현손익 + 미실현손익
                total_pnl = self.total_profit + unrealized_pnl

                # 성과 로깅 (주기적으로)
                if self.tick_count % 100 == 0:  # 100틱마다
                    logger.info(f"봇 {self.bot_id} 성과: 총 손익 {total_pnl} USDT")

        except Exception as e:
            logger.error(f"봇 {self.bot_id} 성과 업데이트 실패: {e}")

    async def _get_market_data(self) -> Optional[Dict]:
        """시장 데이터 조회"""
        try:
            ticker = await self.exchange_client.get_ticker(self.symbol)
            orderbook = await self.exchange_client.get_orderbook(self.symbol, limit=5)

            if not ticker:
                return None

            return {
                'ticker': ticker,
                'orderbook': orderbook or {},
                'timestamp': datetime.now(timezone.utc)
            }

        except Exception as e:
            logger.error(f"봇 {self.bot_id} 시장 데이터 조회 실패: {e}")
            return None

    async def _heartbeat_loop(self):
        """하트비트 루프 - 주기적 상태 저장"""
        while not self._stop_requested:
            try:
                # 상태 정보 로깅
                logger.debug(
                    f"봇 {self.bot_id} 하트비트: 틱={self.tick_count}, 상태={self.state.value}")

                # 실제 구현에서는 데이터베이스에 상태 저장
                await self._save_bot_state()

                await asyncio.sleep(self.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"봇 {self.bot_id} 하트비트 오류: {e}")
                await asyncio.sleep(30)

    async def _price_update_loop(self):
        """가격 업데이트 루프"""
        while not self._stop_requested:
            try:
                # 가격만 빠르게 업데이트
                ticker = await self.exchange_client.get_ticker(self.symbol)
                if ticker:
                    self.last_price = Decimal(str(ticker['last']))

                await asyncio.sleep(self.price_update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"봇 {self.bot_id} 가격 업데이트 오류: {e}")
                await asyncio.sleep(self.price_update_interval * 2)

    async def _save_bot_state(self):
        """봇 상태 저장 (데이터베이스)"""
        try:
            # 실제 구현에서는 데이터베이스에 저장
            # 현재는 로그만 기록
            pass
        except Exception as e:
            logger.error(f"봇 상태 저장 실패: {e}")

    # ===== 외부 제어 메서드들 =====

    async def stop(self):
        """봇 중지"""
        logger.info(f"봇 {self.bot_id} 중지 요청")
        self._stop_requested = True

    def request_graceful_stop(self):
        """정상 종료 요청 (현재 사이클 완료 후)"""
        logger.info(f"봇 {self.bot_id} 정상 종료 요청")
        self._graceful_stop_requested = True

    async def pause(self):
        """일시정지"""
        logger.info(f"봇 {self.bot_id} 일시정지")
        self._paused = True
        self.state = BotState.PAUSED

    async def resume(self):
        """재개"""
        logger.info(f"봇 {self.bot_id} 재개")
        self._paused = False
        self.state = BotState.RUNNING

    async def _emergency_stop(self, reason: str):
        """긴급 중지"""
        logger.critical(f"봇 {self.bot_id} 긴급 중지: {reason}")
        await self._close_all_positions(reason)
        self._stop_requested = True
        self.state = BotState.ERROR

    async def _close_all_positions(self, reason: str):
        """모든 포지션 청산"""
        try:
            # 미체결 주문 모두 취소
            await self.order_executor.cancel_all_orders()

            # 보유 포지션이 있으면 시장가 매도
            position = await self.position_manager.get_current_position()
            total_quantity = position.get('total_quantity', 0)

            if total_quantity > 0:
                await self.order_executor.create_market_order(
                    side="sell",
                    quantity=Decimal(str(total_quantity)),
                    strategy_info={'reason': reason, 'emergency': True}
                )
                logger.info(f"봇 {self.bot_id} 긴급 청산 주문 실행")

        except Exception as e:
            logger.error(f"봇 {self.bot_id} 포지션 청산 실패: {e}")

    async def _cleanup_tasks(self, tasks):
        """태스크 정리"""
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def _final_cleanup(self):
        """최종 정리 작업"""
        try:
            logger.info(f"봇 {self.bot_id} 최종 정리 시작")

            # 컴포넌트들 정리
            if self.strategy_executor:
                await self.strategy_executor.cleanup()

            if self.order_executor:
                await self.order_executor.cleanup()

            if self.position_manager:
                await self.position_manager.cleanup()

            # 거래소 연결 종료
            if self.exchange_client and hasattr(self.exchange_client, 'close'):
                await self.exchange_client.close()

            logger.info(f"봇 {self.bot_id} 최종 정리 완료")

        except Exception as e:
            logger.error(f"봇 {self.bot_id} 정리 중 오류: {e}")

    def _get_api_keys(self) -> Optional[Dict]:
        """API 키 조회 (환경변수 또는 사용자 설정)"""
        # 실제 구현에서는 사용자별 암호화된 API 키를 로드
        # 현재는 테스트용으로 None 반환
        return None

    # ===== 상태 조회 메서드들 =====

    def is_running(self) -> bool:
        """실행 상태 확인"""
        return self._running

    def get_status(self) -> Dict:
        """봇 상태 정보"""
        return {
            'bot_id': self.bot_id,
            'user_id': self.user_id,
            'state': self.state.value,
            'symbol': self.symbol,
            'strategy': self.strategy_name,
            'exchange': self.exchange_name,
            'capital': float(self.capital),
            'current_price': float(self.last_price) if self.last_price else None,
            'running_time': (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0,
            'tick_count': self.tick_count,
            'error_count': self.error_count,
            'is_paused': self._paused,
            'stop_requested': self._stop_requested,
            'graceful_stop_requested': self._graceful_stop_requested
        }

    def get_performance(self) -> Dict:
        """봇 성과 정보"""
        win_rate = (self.successful_trades / self.total_trades *
                    100) if self.total_trades > 0 else 0
        roi = (self.total_profit / self.capital *
               100) if self.capital > 0 else 0

        # position_info를 동기식으로 변경
        position_info = {}
        if self.position_manager:
            # position_manager의 동기식 메서드 사용
            position_info = {
                'symbol': self.position_manager.position.symbol,
                'status': self.position_manager.position.status.value,
                'total_quantity': float(self.position_manager.position.total_quantity),
                'total_cost': float(self.position_manager.position.total_cost),
                'average_price': float(self.position_manager.position.average_price),
                'grid_level': self.position_manager.position.grid_level,
                'unrealized_pnl': float(self.position_manager.position.unrealized_pnl),
                'realized_pnl': float(self.position_manager.position.realized_pnl)
            }

        return {
            'total_profit': float(self.total_profit),
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'win_rate': win_rate,
            'roi_percentage': roi,
            'position_info': position_info,
            'risk_summary': self.risk_manager.get_risk_summary() if self.risk_manager else {}
        }


# ===== 더미 거래소 클라이언트 (테스트용) =====

class DummyExchangeClient:
    """테스트용 더미 거래소 클라이언트"""

    def __init__(self):
        self.base_price = 50000
        self.price_volatility = 0.02  # 2% 변동성

    async def get_ticker(self, symbol: str):
        import random
        # 가격 변동 시뮬레이션
        change = random.uniform(-self.price_volatility, self.price_volatility)
        current_price = self.base_price * (1 + change)

        return {
            'symbol': symbol,
            'last': current_price,
            'bid': current_price * 0.999,
            'ask': current_price * 1.001,
            'high': current_price * 1.02,
            'low': current_price * 0.98,
            'volume': 1000,
            'timestamp': int(datetime.now().timestamp() * 1000)
        }

    async def get_orderbook(self, symbol: str, limit: int = 20):
        ticker = await self.get_ticker(symbol)
        price = ticker['last']

        return {
            'symbol': symbol,
            'bids': [[price * 0.999, 10], [price * 0.998, 15]],
            'asks': [[price * 1.001, 8], [price * 1.002, 12]],
            'timestamp': ticker['timestamp']
        }

    async def create_market_order(self, symbol: str, side: str, amount: float):
        ticker = await self.get_ticker(symbol)
        price = ticker['last']

        return {
            'id': f"dummy_{int(datetime.now().timestamp())}",
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'cost': amount * price,
            'filled': amount,
            'status': 'closed',
            'average': price,
            'timestamp': ticker['timestamp']
        }

    async def create_limit_order(self, symbol: str, side: str, amount: float, price: float):
        return {
            'id': f"dummy_limit_{int(datetime.now().timestamp())}",
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'cost': 0,
            'filled': 0,
            'status': 'open',
            'timestamp': int(datetime.now().timestamp() * 1000)
        }

    async def get_order_status(self, order_id: str, symbol: str):
        # 50% 확률로 체결 시뮬레이션
        import random
        if random.random() > 0.5:
            return {
                'id': order_id,
                'status': 'filled',
                'filled': 0.001,
                'average': 49500,
                'cost': 49.5,
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
        else:
            return {
                'id': order_id,
                'status': 'open',
                'filled': 0,
                'timestamp': int(datetime.now().timestamp() * 1000)
            }

    async def cancel_order(self, order_id: str, symbol: str):
        return True

    async def cancel_all_orders(self, symbol: str = None):
        return True

    async def close(self):
        pass


# ===== 팩토리 함수 =====

def create_bot_runner(bot_id: int, user_id: int, config: Dict[str, Any]) -> BotRunner:
    """봇 러너 팩토리 함수"""
    return BotRunner(bot_id, user_id, config)


# ===== 테스트 함수 =====

async def test_complete_bot_runner():
    """완전한 봇 러너 테스트"""
    print("=== 완전한 봇 러너 테스트 ===")

    # 테스트 설정
    config = {
        'symbol': 'BTC/USDT',
        'strategy': 'dantaro',
        'capital': 1000.0,
        'exchange': 'okx',
        'strategy_settings': {
            'profit_target': 0.5,
            'stop_loss': -10.0,
            'grid_levels': 7,
            'base_amount': 10.0,
            'multiplier': 2.0
        },
        'risk_settings': {
            'max_loss_percentage': -15.0,
            'max_position_size': 80.0,
            'daily_loss_limit': -5.0
        }
    }

    # 봇 러너 생성 및 초기화
    bot = create_bot_runner(1, 100, config)
    await bot.initialize()

    print(f"봇 상태: {bot.get_status()}")

    # 잠시 실행 테스트 (10초)
    async def run_for_seconds(seconds):
        import asyncio
        try:
            await asyncio.wait_for(bot.run(), timeout=seconds)
        except asyncio.TimeoutError:
            await bot.stop()
            print(f"{seconds}초 테스트 실행 완료")

    await run_for_seconds(10)

    # 최종 상태 및 성과
    print(f"최종 상태: {bot.get_status()}")
    print(f"성과: {bot.get_performance()}")


if __name__ == "__main__":
    asyncio.run(test_complete_bot_runner())
