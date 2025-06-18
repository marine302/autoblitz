"""
거래소 기본 추상 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel

class OrderType:
    """주문 타입"""
    MARKET = "market"
    LIMIT = "limit"

class PositionSide:
    """포지션 방향 (선물)"""
    LONG = "long"
    SHORT = "short"
    
class Balance(BaseModel):
    """잔고 정보"""
    currency: str
    total: float
    available: float
    frozen: float = 0.0

class Ticker(BaseModel):
    """시세 정보"""
    symbol: str
    last_price: float
    bid_price: float
    ask_price: float
    volume_24h: float
    change_24h: float
    timestamp: datetime

class Order(BaseModel):
    """주문 정보"""
    order_id: str
    symbol: str
    side: str  # buy/sell
    order_type: str  # market/limit
    price: Optional[float] = None
    amount: float
    filled: float = 0.0
    status: str  # pending/filled/cancelled
    created_at: datetime

class Position(BaseModel):
    """포지션 정보 (선물)"""
    symbol: str
    side: str  # long/short
    amount: float
    entry_price: float
    mark_price: float
    pnl: float
    pnl_ratio: float
    margin: float
    leverage: int

class BaseExchange(ABC):
    """거래소 기본 추상 클래스"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: Optional[str] = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
    
    @abstractmethod
    async def get_balance(self, currency: Optional[str] = None) -> List[Balance]:
        """잔고 조회"""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """시세 조회"""
        pass
    
    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = OrderType.MARKET,
        price: Optional[float] = None
    ) -> Order:
        """주문 실행"""
        pass
    
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """주문 취소"""
        pass
    
    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> Order:
        """주문 조회"""
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """미체결 주문 목록"""
        pass