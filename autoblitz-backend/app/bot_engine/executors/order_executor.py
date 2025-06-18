# app/bot_engine/executors/order_executor.py

import logging
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from decimal import Decimal
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    NEW = "new"
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

@dataclass
class OrderInfo:
    """주문 정보 데이터 클래스"""
    order_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    
    # 상태 정보
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: Decimal = Decimal('0')
    remaining_quantity: Optional[Decimal] = None
    average_price: Optional[Decimal] = None
    cost: Decimal = Decimal('0')
    
    # 수수료 정보
    fee: Optional[Dict] = None
    
    # 시간 정보
    created_at: datetime = None
    updated_at: datetime = None
    filled_at: Optional[datetime] = None
    
    # 메타데이터
    client_order_id: Optional[str] = None
    strategy_info: Optional[Dict] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity

    def update_status(self, new_status: OrderStatus, filled_qty: Decimal = None, avg_price: Decimal = None):
        """주문 상태 업데이트"""
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)
        
        if filled_qty is not None:
            self.filled_quantity = filled_qty
            self.remaining_quantity = self.quantity - filled_qty
        
        if avg_price is not None:
            self.average_price = avg_price
            self.cost = self.filled_quantity * avg_price
        
        if new_status == OrderStatus.FILLED:
            self.filled_at = datetime.now(timezone.utc)
            self.remaining_quantity = Decimal('0')

    def is_active(self) -> bool:
        """활성 주문인지 확인"""
        return self.status in [OrderStatus.NEW, OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]
    
    def is_completed(self) -> bool:
        """완료된 주문인지 확인"""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.EXPIRED]

class OrderExecutor:
    """주문 실행기 - 실제 거래소에 주문을 전송하고 관리"""
    
    def __init__(self, exchange_client, symbol: str):
        self.exchange_client = exchange_client
        self.symbol = symbol
        
        # 주문 추적
        self.active_orders: Dict[str, OrderInfo] = {}
        self.completed_orders: List[OrderInfo] = []
        
        # 설정
        self.max_retries = 3
        self.retry_delay = 1.0  # 초
        
        # 통계
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_orders = 0
        
    async def create_market_order(self, side: str, quantity: Decimal, strategy_info: Dict = None) -> Optional[OrderInfo]:
        """시장가 주문 생성"""
        try:
            logger.info(f"시장가 주문 생성: {side} {quantity} {self.symbol}")
            
            # 주문 정보 생성
            order_info = OrderInfo(
                order_id="",  # 거래소에서 받을 ID
                symbol=self.symbol,
                side=OrderSide(side.lower()),
                type=OrderType.MARKET,
                quantity=quantity,
                strategy_info=strategy_info or {}
            )
            
            # 거래소에 주문 전송
            exchange_order = await self._execute_exchange_order(
                side=side,
                quantity=float(quantity),
                order_type="market"
            )
            
            if exchange_order:
                # 거래소 응답으로 주문 정보 업데이트
                order_info.order_id = exchange_order['id']
                order_info.status = OrderStatus(exchange_order['status'])
                order_info.average_price = Decimal(str(exchange_order.get('price', 0))) if exchange_order.get('price') else None
                order_info.cost = Decimal(str(exchange_order.get('cost', 0)))
                
                # 시장가 주문은 즉시 체결되는 경우가 많음
                if exchange_order['status'] == 'closed':
                    order_info.update_status(
                        OrderStatus.FILLED,
                        filled_qty=Decimal(str(exchange_order.get('filled', 0))),
                        avg_price=Decimal(str(exchange_order.get('average', 0))) if exchange_order.get('average') else None
                    )
                    self.completed_orders.append(order_info)
                    self.successful_orders += 1
                else:
                    self.active_orders[order_info.order_id] = order_info
                
                self.total_orders += 1
                logger.info(f"시장가 주문 성공: {order_info.order_id}")
                return order_info
            
            else:
                self.failed_orders += 1
                logger.error("시장가 주문 실패: 거래소 응답 없음")
                return None
                
        except Exception as e:
            self.failed_orders += 1
            logger.error(f"시장가 주문 생성 실패: {e}")
            return None
    
    async def create_limit_order(self, side: str, quantity: Decimal, price: Decimal, strategy_info: Dict = None) -> Optional[OrderInfo]:
        """지정가 주문 생성"""
        try:
            logger.info(f"지정가 주문 생성: {side} {quantity} {self.symbol} @ {price}")
            
            # 주문 정보 생성
            order_info = OrderInfo(
                order_id="",
                symbol=self.symbol,
                side=OrderSide(side.lower()),
                type=OrderType.LIMIT,
                quantity=quantity,
                price=price,
                strategy_info=strategy_info or {}
            )
            
            # 거래소에 주문 전송
            exchange_order = await self._execute_exchange_order(
                side=side,
                quantity=float(quantity),
                price=float(price),
                order_type="limit"
            )
            
            if exchange_order:
                order_info.order_id = exchange_order['id']
                order_info.status = OrderStatus(exchange_order['status'])
                
                # 활성 주문 목록에 추가
                self.active_orders[order_info.order_id] = order_info
                self.total_orders += 1
                
                logger.info(f"지정가 주문 성공: {order_info.order_id}")
                return order_info
            
            else:
                self.failed_orders += 1
                logger.error("지정가 주문 실패: 거래소 응답 없음")
                return None
                
        except Exception as e:
            self.failed_orders += 1
            logger.error(f"지정가 주문 생성 실패: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        try:
            if order_id not in self.active_orders:
                logger.warning(f"취소할 주문을 찾을 수 없음: {order_id}")
                return False
            
            order_info = self.active_orders[order_id]
            
            # 거래소에 취소 요청
            success = await self.exchange_client.cancel_order(order_id, self.symbol)
            
            if success:
                # 주문 상태 업데이트
                order_info.update_status(OrderStatus.CANCELED)
                
                # 활성 주문에서 제거하고 완료 주문에 추가
                del self.active_orders[order_id]
                self.completed_orders.append(order_info)
                
                logger.info(f"주문 취소 성공: {order_id}")
                return True
            else:
                logger.error(f"주문 취소 실패: {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"주문 취소 중 오류: {e}")
            return False
    
    async def cancel_all_orders(self) -> int:
        """모든 활성 주문 취소"""
        canceled_count = 0
        order_ids = list(self.active_orders.keys())
        
        for order_id in order_ids:
            if await self.cancel_order(order_id):
                canceled_count += 1
        
        logger.info(f"총 {canceled_count}개 주문 취소 완료")
        return canceled_count
    
    async def get_order_status(self, order_id: str) -> Optional[OrderInfo]:
        """주문 상태 조회"""
        try:
            if order_id in self.active_orders:
                order_info = self.active_orders[order_id]
                
                # 거래소에서 최신 상태 조회
                exchange_order = await self.exchange_client.get_order_status(order_id, self.symbol)
                
                if exchange_order:
                    # 주문 정보 업데이트
                    old_status = order_info.status
                    new_status = OrderStatus(exchange_order['status'])
                    
                    order_info.update_status(
                        new_status,
                        filled_qty=Decimal(str(exchange_order.get('filled', 0))),
                        avg_price=Decimal(str(exchange_order.get('average', 0))) if exchange_order.get('average') else None
                    )
                    
                    # 주문이 완료되면 활성 목록에서 제거
                    if order_info.is_completed() and old_status != new_status:
                        del self.active_orders[order_id]
                        self.completed_orders.append(order_info)
                        
                        if new_status == OrderStatus.FILLED:
                            self.successful_orders += 1
                
                return order_info
            
            # 완료된 주문에서 찾기
            for order in self.completed_orders:
                if order.order_id == order_id:
                    return order
            
            logger.warning(f"주문을 찾을 수 없음: {order_id}")
            return None
            
        except Exception as e:
            logger.error(f"주문 상태 조회 실패: {e}")
            return None
    
    async def update_all_orders(self):
        """모든 활성 주문 상태 업데이트"""
        updated_count = 0
        order_ids = list(self.active_orders.keys())
        
        for order_id in order_ids:
            updated_order = await self.get_order_status(order_id)
            if updated_order:
                updated_count += 1
        
        logger.debug(f"{updated_count}개 주문 상태 업데이트 완료")
        return updated_count
    
    async def _execute_exchange_order(self, side: str, quantity: float, price: float = None, order_type: str = "market") -> Optional[Dict]:
        """거래소에 실제 주문 전송 (재시도 로직 포함)"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                if order_type == "market":
                    if hasattr(self.exchange_client, 'create_market_order'):
                        result = await self.exchange_client.create_market_order(self.symbol, side, quantity)
                    else:
                        # 더미 응답 (테스트용)
                        result = {
                            'id': f"test_order_{datetime.now().timestamp()}",
                            'symbol': self.symbol,
                            'side': side,
                            'amount': quantity,
                            'price': price,
                            'cost': quantity * (price or 50000),
                            'filled': quantity,
                            'status': 'closed',
                            'timestamp': int(datetime.now().timestamp() * 1000)
                        }
                elif order_type == "limit":
                    if hasattr(self.exchange_client, 'create_limit_order'):
                        result = await self.exchange_client.create_limit_order(self.symbol, side, quantity, price)
                    else:
                        # 더미 응답 (테스트용)
                        result = {
                            'id': f"test_limit_{datetime.now().timestamp()}",
                            'symbol': self.symbol,
                            'side': side,
                            'amount': quantity,
                            'price': price,
                            'cost': 0,
                            'filled': 0,
                            'status': 'open',
                            'timestamp': int(datetime.now().timestamp() * 1000)
                        }
                
                if result:
                    return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"주문 전송 실패 (시도 {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
        
        logger.error(f"주문 전송 최종 실패: {last_error}")
        return None
    
    def get_active_orders(self) -> List[OrderInfo]:
        """활성 주문 목록 반환"""
        return list(self.active_orders.values())
    
    def get_completed_orders(self, limit: int = 50) -> List[OrderInfo]:
        """완료된 주문 목록 반환"""
        return self.completed_orders[-limit:] if limit else self.completed_orders
    
    def get_order_by_strategy_info(self, key: str, value: Any) -> List[OrderInfo]:
        """전략 정보로 주문 검색"""
        matching_orders = []
        
        # 활성 주문에서 검색
        for order in self.active_orders.values():
            if order.strategy_info and order.strategy_info.get(key) == value:
                matching_orders.append(order)
        
        # 완료된 주문에서 검색
        for order in self.completed_orders:
            if order.strategy_info and order.strategy_info.get(key) == value:
                matching_orders.append(order)
        
        return matching_orders
    
    def calculate_total_cost(self, side: str, status_filter: List[OrderStatus] = None) -> Decimal:
        """총 거래 비용 계산"""
        total = Decimal('0')
        
        all_orders = list(self.active_orders.values()) + self.completed_orders
        
        for order in all_orders:
            if order.side.value == side.lower():
                if status_filter is None or order.status in status_filter:
                    total += order.cost
        
        return total
    
    def calculate_total_quantity(self, side: str, filled_only: bool = True) -> Decimal:
        """총 거래 수량 계산"""
        total = Decimal('0')
        
        all_orders = list(self.active_orders.values()) + self.completed_orders
        
        for order in all_orders:
            if order.side.value == side.lower():
                if filled_only:
                    total += order.filled_quantity
                else:
                    total += order.quantity
        
        return total
    
    def get_statistics(self) -> Dict:
        """주문 실행기 통계"""
        active_buy_orders = sum(1 for o in self.active_orders.values() if o.side == OrderSide.BUY)
        active_sell_orders = sum(1 for o in self.active_orders.values() if o.side == OrderSide.SELL)
        
        filled_orders = sum(1 for o in self.completed_orders if o.status == OrderStatus.FILLED)
        canceled_orders = sum(1 for o in self.completed_orders if o.status == OrderStatus.CANCELED)
        
        return {
            'symbol': self.symbol,
            'total_orders': self.total_orders,
            'successful_orders': self.successful_orders,
            'failed_orders': self.failed_orders,
            'success_rate': (self.successful_orders / self.total_orders * 100) if self.total_orders > 0 else 0,
            'active_orders': {
                'total': len(self.active_orders),
                'buy_orders': active_buy_orders,
                'sell_orders': active_sell_orders
            },
            'completed_orders': {
                'total': len(self.completed_orders),
                'filled': filled_orders,
                'canceled': canceled_orders
            },
            'trading_volume': {
                'buy_cost': float(self.calculate_total_cost('buy', [OrderStatus.FILLED])),
                'sell_cost': float(self.calculate_total_cost('sell', [OrderStatus.FILLED])),
                'buy_quantity': float(self.calculate_total_quantity('buy')),
                'sell_quantity': float(self.calculate_total_quantity('sell'))
            }
        }
    
    async def cleanup(self):
        """정리 작업"""
        logger.info("주문 실행기 정리 작업 시작")
        
        # 모든 활성 주문 취소
        if self.active_orders:
            await self.cancel_all_orders()
        
        # 메모리 정리
        self.active_orders.clear()
        self.completed_orders.clear()
        
        logger.info("주문 실행기 정리 작업 완료")


# ===== 팩토리 함수 =====

def create_order_executor(exchange_client, symbol: str) -> OrderExecutor:
    """주문 실행기 팩토리 함수"""
    return OrderExecutor(exchange_client, symbol)


# ===== 테스트 함수 =====

async def test_order_executor():
    """주문 실행기 테스트"""
    print("=== 주문 실행기 테스트 ===")
    
    # 더미 거래소 클라이언트
    class DummyExchangeClient:
        async def create_market_order(self, symbol, side, amount):
            return {
                'id': f"test_market_{datetime.now().timestamp()}",
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'cost': amount * 50000,
                'filled': amount,
                'status': 'closed',
                'average': 50000
            }
        
        async def create_limit_order(self, symbol, side, amount, price):
            return {
                'id': f"test_limit_{datetime.now().timestamp()}",
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': price,
                'cost': 0,
                'filled': 0,
                'status': 'open'
            }
        
        async def cancel_order(self, order_id, symbol):
            return True
        
        async def get_order_status(self, order_id, symbol):
            return {
                'id': order_id,
                'status': 'filled',
                'filled': 0.001,
                'average': 49500
            }
    
    # 테스트 실행
    dummy_client = DummyExchangeClient()
    executor = OrderExecutor(dummy_client, "BTC/USDT")
    
    # 1. 시장가 매수 주문
    buy_order = await executor.create_market_order("buy", Decimal('0.001'))
    print(f"시장가 매수 주문: {buy_order.order_id if buy_order else 'Failed'}")
    
    # 2. 지정가 매도 주문
    sell_order = await executor.create_limit_order("sell", Decimal('0.001'), Decimal('51000'))
    print(f"지정가 매도 주문: {sell_order.order_id if sell_order else 'Failed'}")
    
    # 3. 주문 상태 업데이트
    if sell_order:
        updated = await executor.get_order_status(sell_order.order_id)
        print(f"주문 상태 업데이트: {updated.status if updated else 'Failed'}")
    
    # 4. 통계 출력
    stats = executor.get_statistics()
    print(f"주문 통계: {stats}")
    
    # 5. 정리
    await executor.cleanup()


if __name__ == "__main__":
    asyncio.run(test_order_executor())