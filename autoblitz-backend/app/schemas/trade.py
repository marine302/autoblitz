"""
거래 관련 스키마
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class TradeBase(BaseModel):
    """거래 기본 스키마"""
    exchange: str
    symbol: str
    side: str
    order_type: str
    price: float
    amount: float
    cost: float

class TradeCreate(TradeBase):
    """거래 생성 스키마"""
    bot_id: str
    order_id: str
    fee: float = 0.0
    strategy_signal: Optional[Dict[str, Any]] = None

class TradeResponse(TradeBase):
    """거래 응답 스키마"""
    id: int
    bot_id: str
    order_id: str
    status: str
    fee: float
    profit: Optional[float] = None
    profit_rate: Optional[float] = None
    created_at: datetime
    executed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class GridOrderResponse(BaseModel):
    """그리드 주문 응답 스키마"""
    id: int
    bot_id: str
    grid_level: int
    order_type: str
    price: float
    amount: float
    status: str
    order_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True