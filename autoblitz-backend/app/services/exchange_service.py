"""
거래소 서비스 레이어
"""

from typing import Optional, Dict, Any
from ..exchanges.base import BaseExchange
from ..exchanges.okx.client import OKXClient
from ..core.config import settings

class ExchangeService:
    """거래소 서비스"""
    
    _instances: Dict[str, BaseExchange] = {}
    
    @classmethod
    async def get_client(
        cls,
        exchange: str,
        api_key: str,
        secret_key: str,
        passphrase: Optional[str] = None
    ) -> BaseExchange:
        """거래소 클라이언트 획득"""
        
        # 키 생성
        instance_key = f"{exchange}:{api_key}"
        
        # 캐시 확인
        if instance_key in cls._instances:
            return cls._instances[instance_key]
        
        # 새 인스턴스 생성
        if exchange == "okx":
            if not passphrase:
                raise ValueError("OKX requires passphrase")
            client = OKXClient(api_key, secret_key, passphrase)
        elif exchange == "upbit":
            # TODO: Upbit 클라이언트 구현
            raise NotImplementedError("Upbit client not implemented yet")
        else:
            raise ValueError(f"Unknown exchange: {exchange}")
        
        # 캐시 저장
        cls._instances[instance_key] = client
        
        return client
    
    @classmethod
    async def close_all(cls):
        """모든 클라이언트 종료"""
        for client in cls._instances.values():
            if hasattr(client, 'close'):
                await client.close()
        cls._instances.clear()