"""
OKX API 모델 정의
"""

from typing import Optional, List
from pydantic import BaseModel

class OKXBalance(BaseModel):
    """OKX 잔고"""
    ccy: str  # Currency
    bal: str  # Balance
    availBal: str  # Available balance
    frozenBal: str  # Frozen balance

class OKXTicker(BaseModel):
    """OKX 시세"""
    instId: str  # Instrument ID
    last: str  # Last price
    bidPx: str  # Bid price
    askPx: str  # Ask price
    vol24h: str  # 24h volume
    sodUtc0: str  # Open price UTC 0
    ts: str  # Timestamp

class OKXOrderRequest(BaseModel):
    """OKX 주문 요청"""
    instId: str  # Instrument ID
    tdMode: str  # Trade mode (cash, cross, isolated)
    side: str  # buy/sell
    ordType: str  # Order type
    sz: str  # Size
    px: Optional[str] = None  # Price (for limit orders)
    
class OKXOrderResponse(BaseModel):
    """OKX 주문 응답"""
    ordId: str  # Order ID
    clOrdId: str  # Client Order ID
    sCode: str  # Response code
    sMsg: str  # Response message

class OKXPosition(BaseModel):
    """OKX 포지션 (선물)"""
    instId: str
    posSide: str  # long/short
    pos: str  # Position size
    avgPx: str  # Average price
    markPx: str  # Mark price
    upl: str  # Unrealized PnL
    uplRatio: str  # PnL ratio
    margin: str  # Margin
    lever: str  # Leverage