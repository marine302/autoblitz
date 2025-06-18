"""
거래 관련 모델
Position, Order, Signal 등 거래에 필요한 데이터 모델
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"

class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"

class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"

class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class Order(BaseModel):
    """주문 모델"""
    id: Optional[str] = None
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    price: float
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = datetime.now()
    filled_quantity: Optional[float] = None
    filled_price: Optional[float] = None
    metadata: Dict[str, Any] = {}

class Position(BaseModel):
    """포지션 모델"""
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    entry_time: datetime
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    metadata: Dict[str, Any] = {}

class TradingSignal(BaseModel):
    """거래 신호 모델"""
    symbol: str
    signal_type: SignalType
    price: float
    confidence: float = 1.0
    reason: str = ""
    timestamp: datetime = datetime.now()
    metadata: Dict[str, Any] = {}

# 호환성을 위한 별칭
Signal = TradingSignal
