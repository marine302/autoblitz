# app/bot_engine/managers/position_manager.py

import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone
from enum import Enum

from app.bot_engine.executors.order_executor import OrderInfo, OrderStatus, OrderSide

logger = logging.getLogger(__name__)


class PositionStatus(Enum):
    EMPTY = "empty"
    BUILDING = "building"  # 포지션 구축 중
    HOLDING = "holding"    # 포지션 보유 중
    CLOSING = "closing"    # 포지션 정리 중
    CLOSED = "closed"      # 포지션 완전 정리됨


@dataclass
class GridLevel:
    """그리드 레벨 정보"""
    level: int
    target_price: Decimal
    quantity: Decimal
    amount_usdt: Decimal
    executed: bool = False
    order_id: Optional[str] = None
    executed_price: Optional[Decimal] = None
    executed_at: Optional[datetime] = None


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    status: PositionStatus

    # 포지션 기본 정보
    total_quantity: Decimal = Decimal('0')
    total_cost: Decimal = Decimal('0')
    average_price: Decimal = Decimal('0')

    # 그리드 정보
    grid_level: int = 0
    max_grid_level: int = 7
    grid_levels: List[GridLevel] = None

    # 손익 정보
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')

    # 목표가 정보
    target_profit_price: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None

    # 시간 정보
    opened_at: Optional[datetime] = None
    last_update: datetime = None

    def __post_init__(self):
        if self.grid_levels is None:
            self.grid_levels = []
        if self.last_update is None:
            self.last_update = datetime.now(timezone.utc)

    def update_average_price(self):
        """평균 매수가 재계산"""
        if self.total_quantity > 0:
            self.average_price = self.total_cost / self.total_quantity
        else:
            self.average_price = Decimal('0')

    def calculate_unrealized_pnl(self, current_price: Decimal):
        """미실현 손익 계산"""
        if self.total_quantity > 0:
            current_value = self.total_quantity * current_price
            self.unrealized_pnl = current_value - self.total_cost
        else:
            self.unrealized_pnl = Decimal('0')

    def get_profit_percentage(self, current_price: Decimal) -> Decimal:
        """수익률 계산"""
        if self.average_price > 0:
            return (current_price - self.average_price) / self.average_price * 100
        return Decimal('0')


class PositionManager:
    """포지션 관리자 - 봇의 포지션과 주문 상태를 추적 및 관리"""

    def __init__(self, bot_id: int, capital: float, exchange_client, symbol: str):
        self.bot_id = bot_id
        self.capital = Decimal(str(capital))
        self.exchange_client = exchange_client
        self.symbol = symbol

        # 포지션 상태
        self.position = Position(
            symbol=symbol,
            status=PositionStatus.EMPTY
        )

        # 주문 추적
        self.pending_orders: Dict[str, OrderInfo] = {}
        self.completed_orders: List[OrderInfo] = []

        # 설정
        self.min_order_amount = Decimal('10.0')  # 최소 주문 금액 (USDT)
        self.precision = 4  # 소수점 자리수

        # 통계
        self.total_cycles = 0
        self.successful_cycles = 0
        self.total_fees = Decimal('0')

    async def initialize(self):
        """포지션 매니저 초기화"""
        try:
            logger.info(f"봇 {self.bot_id} 포지션 매니저 초기화")

            # 기존 포지션이 있는지 확인 (서버 재시작 등의 경우)
            await self._recover_existing_position()

            logger.info(f"포지션 매니저 초기화 완료 - 상태: {self.position.status}")

        except Exception as e:
            logger.error(f"포지션 매니저 초기화 실패: {e}")
            raise

    async def _recover_existing_position(self):
        """기존 포지션 복구 (DB에서 로드)"""
        try:
            # 실제 구현에서는 데이터베이스에서 봇의 마지막 상태를 로드
            # 현재는 빈 포지션으로 시작
            self.position.status = PositionStatus.EMPTY
            logger.info("새로운 포지션으로 시작")

        except Exception as e:
            logger.error(f"포지션 복구 실패: {e}")
            # 실패 시 안전하게 빈 포지션으로 초기화
            self.position = Position(
                symbol=self.symbol, status=PositionStatus.EMPTY)

    async def add_buy_order(self, order_info: OrderInfo):
        """매수 주문 추가"""
        try:
            if order_info.side != OrderSide.BUY:
                logger.error("매수 주문이 아닙니다")
                return

            # 펜딩 주문에 추가
            self.pending_orders[order_info.order_id] = order_info

            # 포지션 상태 업데이트
            if self.position.status == PositionStatus.EMPTY:
                self.position.status = PositionStatus.BUILDING
                self.position.opened_at = datetime.now(timezone.utc)

            logger.info(
                f"매수 주문 추가: {order_info.order_id} ({order_info.quantity} @ {order_info.price})")

        except Exception as e:
            logger.error(f"매수 주문 추가 실패: {e}")

    async def add_sell_order(self, order_info: OrderInfo):
        """매도 주문 추가"""
        try:
            if order_info.side != OrderSide.SELL:
                logger.error("매도 주문이 아닙니다")
                return

            # 펜딩 주문에 추가
            self.pending_orders[order_info.order_id] = order_info

            # 포지션 상태 업데이트 (전량 매도인 경우)
            if order_info.quantity >= self.position.total_quantity:
                self.position.status = PositionStatus.CLOSING

            logger.info(
                f"매도 주문 추가: {order_info.order_id} ({order_info.quantity} @ {order_info.price})")

        except Exception as e:
            logger.error(f"매도 주문 추가 실패: {e}")

    async def update_order_status(self, updated_order: OrderInfo):
        """주문 상태 업데이트"""
        try:
            order_id = updated_order.order_id

            if order_id not in self.pending_orders:
                logger.warning(f"알 수 없는 주문 ID: {order_id}")
                return

            old_order = self.pending_orders[order_id]

            # 주문 정보 업데이트
            self.pending_orders[order_id] = updated_order

            # 체결된 경우 포지션 업데이트
            if updated_order.status == OrderStatus.FILLED:
                await self._process_filled_order(updated_order)

                # 완료된 주문으로 이동
                del self.pending_orders[order_id]
                self.completed_orders.append(updated_order)

            elif updated_order.status in [OrderStatus.CANCELED, OrderStatus.REJECTED]:
                # 취소/거부된 주문 처리
                del self.pending_orders[order_id]
                self.completed_orders.append(updated_order)

                logger.info(f"주문 {updated_order.status.value}: {order_id}")

        except Exception as e:
            logger.error(f"주문 상태 업데이트 실패: {e}")

    async def _process_filled_order(self, order: OrderInfo):
        """체결된 주문 처리"""
        try:
            if order.side == OrderSide.BUY:
                # 매수 체결 처리
                self.position.total_quantity += order.filled_quantity
                self.position.total_cost += order.cost
                self.position.update_average_price()

                # 그리드 레벨 증가
                self.position.grid_level += 1

                # 포지션 상태 업데이트
                self.position.status = PositionStatus.HOLDING

                logger.info(
                    f"매수 체결: {order.filled_quantity} @ {order.average_price}")
                logger.info(
                    f"포지션 업데이트 - 수량: {self.position.total_quantity}, 평균가: {self.position.average_price}")

            elif order.side == OrderSide.SELL:
                # 매도 체결 처리
                sold_quantity = order.filled_quantity
                sold_value = order.cost

                # 실현 손익 계산
                cost_basis = self.position.average_price * sold_quantity
                realized_pnl = sold_value - cost_basis
                self.position.realized_pnl += realized_pnl

                # 포지션 수량 감소
                self.position.total_quantity -= sold_quantity
                self.position.total_cost = self.position.total_quantity * self.position.average_price

                logger.info(f"매도 체결: {sold_quantity} @ {order.average_price}")
                logger.info(f"실현 손익: {realized_pnl} USDT")

                # 전량 매도인 경우 포지션 종료
                # 거의 0에 가까우면
                if self.position.total_quantity <= Decimal('0.00001'):
                    await self._close_position()
                    self.total_cycles += 1
                    if realized_pnl > 0:
                        self.successful_cycles += 1

            # 수수료 추가
            if order.fee:
                self.total_fees += Decimal(str(order.fee.get('cost', 0)))

            self.position.last_update = datetime.now(timezone.utc)

        except Exception as e:
            logger.error(f"체결 주문 처리 실패: {e}")

    async def _close_position(self):
        """포지션 종료"""
        try:
            logger.info(f"포지션 종료 - 총 손익: {self.position.realized_pnl} USDT")

            # 포지션 초기화
            self.position.status = PositionStatus.CLOSED
            self.position.total_quantity = Decimal('0')
            self.position.total_cost = Decimal('0')
            self.position.average_price = Decimal('0')
            self.position.grid_level = 0
            self.position.unrealized_pnl = Decimal('0')

            # 다음 사이클을 위해 상태 리셋
            await asyncio.sleep(1)  # 잠시 대기
            self.position.status = PositionStatus.EMPTY

        except Exception as e:
            logger.error(f"포지션 종료 처리 실패: {e}")

    async def get_open_orders(self) -> List[OrderInfo]:
        """미체결 주문 목록"""
        return list(self.pending_orders.values())

    async def get_current_position(self) -> Dict:
        """현재 포지션 정보 반환"""
        return {
            'symbol': self.position.symbol,
            'status': self.position.status.value,
            'total_quantity': float(self.position.total_quantity),
            'total_cost': float(self.position.total_cost),
            'average_price': float(self.position.average_price),
            'grid_level': self.position.grid_level,
            'max_grid_level': self.position.max_grid_level,
            'unrealized_pnl': float(self.position.unrealized_pnl),
            'realized_pnl': float(self.position.realized_pnl),
            'target_profit_price': float(self.position.target_profit_price) if self.position.target_profit_price else None,
            'stop_loss_price': float(self.position.stop_loss_price) if self.position.stop_loss_price else None,
            'opened_at': self.position.opened_at.isoformat() if self.position.opened_at else None,
            'last_update': self.position.last_update.isoformat()
        }

    async def update_position(self, current_price: Decimal):
        """포지션 업데이트 (현재가 기준)"""
        try:
            # 미실현 손익 계산
            self.position.calculate_unrealized_pnl(current_price)

            # 목표가 업데이트 (단타로 전략의 경우)
            if self.position.total_quantity > 0 and not self.position.target_profit_price:
                profit_rate = Decimal('0.5')  # 0.5% 익절
                self.position.target_profit_price = self.position.average_price * \
                    (1 + profit_rate / 100)

            self.position.last_update = datetime.now(timezone.utc)

        except Exception as e:
            logger.error(f"포지션 업데이트 실패: {e}")

    async def get_average_buy_price(self) -> Decimal:
        """평균 매수가 조회"""
        return self.position.average_price

    async def get_total_quantity(self) -> Decimal:
        """총 보유 수량"""
        return self.position.total_quantity

    async def calculate_cycle_profit(self, sell_order: OrderInfo) -> Decimal:
        """사이클 수익 계산"""
        if sell_order.side != OrderSide.SELL:
            return Decimal('0')

        # 매도가 - 평균 매수가 = 단위당 수익
        profit_per_unit = sell_order.average_price - self.position.average_price
        total_profit = profit_per_unit * sell_order.filled_quantity

        return total_profit

    async def clear_position(self):
        """포지션 클리어"""
        self.position = Position(
            symbol=self.symbol, status=PositionStatus.EMPTY)
        self.pending_orders.clear()
        logger.info("포지션 클리어 완료")

    async def get_unrealized_pnl(self, current_price: Decimal) -> Decimal:
        """미실현 손익"""
        self.position.calculate_unrealized_pnl(current_price)
        return self.position.unrealized_pnl

    async def has_open_position(self) -> bool:
        """오픈 포지션 확인"""
        return self.position.status in [PositionStatus.BUILDING, PositionStatus.HOLDING, PositionStatus.CLOSING]

    def should_add_grid_level(self, current_price: Decimal, drop_threshold: Decimal = Decimal('2.0')) -> bool:
        """그리드 레벨 추가 조건 확인"""
        if self.position.grid_level >= self.position.max_grid_level:
            return False

        if self.position.average_price <= 0:
            return False

        # 평균가 대비 하락률 확인
        drop_rate = (self.position.average_price - current_price) / \
            self.position.average_price * 100
        return drop_rate >= drop_threshold

    def should_take_profit(self, current_price: Decimal, profit_threshold: Decimal = Decimal('0.5')) -> bool:
        """익절 조건 확인"""
        if self.position.average_price <= 0:
            return False

        profit_rate = self.position.get_profit_percentage(current_price)
        return profit_rate >= profit_threshold

    def should_stop_loss(self, current_price: Decimal, loss_threshold: Decimal = Decimal('-10.0')) -> bool:
        """손절 조건 확인"""
        if self.position.average_price <= 0:
            return False

        loss_rate = self.position.get_profit_percentage(current_price)
        return loss_rate <= loss_threshold

    def get_next_grid_amount(self, base_amount: Decimal, multiplier: Decimal = Decimal('2')) -> Decimal:
        """다음 그리드 매수 금액 계산"""
        next_level = self.position.grid_level + 1
        amount = base_amount * (multiplier ** (next_level - 1))
        return amount

    def calculate_position_size(self, usdt_amount: Decimal, price: Decimal) -> Decimal:
        """포지션 크기 계산 (USDT -> 코인 수량)"""
        if price <= 0:
            return Decimal('0')

        quantity = usdt_amount / price
        # 소수점 자리수 조정
        return quantity.quantize(Decimal('0.0001'), rounding=ROUND_DOWN)

    def get_statistics(self) -> Dict:
        """포지션 매니저 통계"""
        return {
            'bot_id': self.bot_id,
            'symbol': self.symbol,
            'capital': float(self.capital),
            'position_info': {
                'symbol': self.position.symbol,
                'status': self.position.status.value,
                'total_quantity': float(self.position.total_quantity),
                'total_cost': float(self.position.total_cost),
                'average_price': float(self.position.average_price),
                'grid_level': self.position.grid_level,
                'unrealized_pnl': float(self.position.unrealized_pnl),
                'realized_pnl': float(self.position.realized_pnl)
            },
            'trading_stats': {
                'total_cycles': self.total_cycles,
                'successful_cycles': self.successful_cycles,
                'success_rate': (self.successful_cycles / self.total_cycles * 100) if self.total_cycles > 0 else 0,
                'total_fees': float(self.total_fees),
                'pending_orders': len(self.pending_orders),
                'completed_orders': len(self.completed_orders)
            },
            'performance': {
                'realized_pnl': float(self.position.realized_pnl),
                'unrealized_pnl': float(self.position.unrealized_pnl),
                'total_pnl': float(self.position.realized_pnl + self.position.unrealized_pnl),
                'roi_percentage': float((self.position.realized_pnl / self.capital * 100)) if self.capital > 0 else 0
            }
        }

    async def cleanup(self):
        """정리 작업"""
        logger.info(f"봇 {self.bot_id} 포지션 매니저 정리 작업")

        # 미체결 주문이 있으면 경고
        if self.pending_orders:
            logger.warning(f"정리 시점에 미체결 주문 {len(self.pending_orders)}개 존재")

        # 메모리 정리
        self.pending_orders.clear()
        self.completed_orders.clear()


# ===== 팩토리 함수 =====

def create_position_manager(bot_id: int, capital: float, exchange_client, symbol: str) -> PositionManager:
    """포지션 매니저 팩토리 함수"""
    return PositionManager(bot_id, capital, exchange_client, symbol)


# ===== 테스트 함수 =====

async def test_position_manager():
    """포지션 매니저 테스트"""
    print("=== 포지션 매니저 테스트 ===")

    from app.bot_engine.executors.order_executor import OrderInfo, OrderSide, OrderType, OrderStatus
    from decimal import Decimal

    # 포지션 매니저 생성
    manager = PositionManager(1, 1000.0, None, "BTC/USDT")
    await manager.initialize()

    # 1. 첫 매수 주문
    buy_order1 = OrderInfo(
        order_id="test_buy_1",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        quantity=Decimal('0.001'),
        average_price=Decimal('50000'),
        filled_quantity=Decimal('0.001'),
        cost=Decimal('50')
    )
    buy_order1.update_status(
        OrderStatus.FILLED, Decimal('0.001'), Decimal('50000'))

    await manager.add_buy_order(buy_order1)
    await manager.update_order_status(buy_order1)

    print(f"첫 매수 후 포지션: {await manager.get_current_position()}")

    # 2. 추가 매수 (물타기)
    buy_order2 = OrderInfo(
        order_id="test_buy_2",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        quantity=Decimal('0.002'),
        average_price=Decimal('49000'),
        filled_quantity=Decimal('0.002'),
        cost=Decimal('98')
    )
    buy_order2.update_status(
        OrderStatus.FILLED, Decimal('0.002'), Decimal('49000'))

    await manager.add_buy_order(buy_order2)
    await manager.update_order_status(buy_order2)

    print(f"추가 매수 후 포지션: {await manager.get_current_position()}")

    # 3. 전량 매도
    sell_order = OrderInfo(
        order_id="test_sell_1",
        symbol="BTC/USDT",
        side=OrderSide.SELL,
        type=OrderType.MARKET,
        quantity=Decimal('0.003'),
        average_price=Decimal('49500'),
        filled_quantity=Decimal('0.003'),
        cost=Decimal('148.5')
    )
    sell_order.update_status(
        OrderStatus.FILLED, Decimal('0.003'), Decimal('49500'))

    await manager.add_sell_order(sell_order)
    await manager.update_order_status(sell_order)

    print(f"매도 후 포지션: {await manager.get_current_position()}")

    # 4. 통계 출력
    stats = manager.get_statistics()
    print(f"포지션 매니저 통계: {stats}")


if __name__ == "__main__":
    asyncio.run(test_position_manager())
