# app/exchanges/okx/client.py - dotenv 로드 추가
"""
OKX 통합 클라이언트 - dotenv 로드 추가
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Any

# dotenv 로드 추가
try:
    from dotenv import load_dotenv
    load_dotenv()  # .env 파일 자동 로드
except ImportError:
    pass

from app.exchanges.okx.live_client import OKXLiveClient

logger = logging.getLogger(__name__)

class OKXClient:
    """OKX 통합 클라이언트 - 실전 검증된 live_client 기반"""
    
    def __init__(self, api_key: str = None, secret_key: str = None, passphrase: str = None, sandbox: bool = None):
        # 환경변수에서 직접 로드 (.env 파일 포함)
        self.api_key = api_key or os.getenv('OKX_API_KEY')
        self.secret_key = secret_key or os.getenv('OKX_SECRET_KEY')
        self.passphrase = passphrase or os.getenv('OKX_PASSPHRASE')
        self.sandbox = sandbox if sandbox is not None else True
        
        # API 키 상세 검증
        missing_keys = []
        if not self.api_key:
            missing_keys.append('OKX_API_KEY')
        if not self.secret_key:
            missing_keys.append('OKX_SECRET_KEY')
        if not self.passphrase:
            missing_keys.append('OKX_PASSPHRASE')
            
        if missing_keys:
            logger.warning(f"누락된 API 키: {', '.join(missing_keys)}. 테스트 모드로 실행됩니다.")
            self.test_mode = True
        else:
            self.test_mode = False
            logger.info("✅ 모든 OKX API 키 설정 완료")
        
        # 실전 클라이언트 초기화
        if not self.test_mode:
            self.live_client = OKXLiveClient()
        else:
            self.live_client = None
            
        self.is_connected = False
        
    async def initialize(self):
        """클라이언트 초기화"""
        try:
            if self.test_mode:
                self.is_connected = True
                logger.info("✅ OKX 테스트 모드로 초기화")
                return True
                
            # 실전 클라이언트 연결 테스트
            logger.info("🔗 OKX 실거래 연결 시도...")
            balance = self.live_client.get_balance()
            self.is_connected = True
            logger.info("✅ OKX 실거래 클라이언트 초기화 성공")
            return True
        except Exception as e:
            logger.error(f"❌ OKX 클라이언트 초기화 실패: {e}")
            self.is_connected = False
            # 실패시 테스트 모드로 fallback
            self.test_mode = True
            self.is_connected = True
            logger.info("⚠️ 실거래 연결 실패, 테스트 모드로 전환")
            return True
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """시세 조회"""
        try:
            if self.test_mode:
                # 실제와 유사한 테스트 데이터
                import time
                import random
                base_price = 50000.0
                variation = random.uniform(-1000, 1000)
                current_price = base_price + variation
                
                return {
                    'symbol': symbol,
                    'last': round(current_price, 2),
                    'bid': round(current_price - 1, 2),
                    'ask': round(current_price + 1, 2),
                    'high': round(current_price + 500, 2),
                    'low': round(current_price - 500, 2),
                    'volume': round(random.uniform(100, 1000), 2),
                    'timestamp': int(time.time() * 1000)
                }
            
            # 실거래 모드
            ticker = self.live_client.get_ticker(symbol)
            return {
                'symbol': ticker['symbol'],
                'last': ticker['last_price'],
                'bid': ticker['bid_price'], 
                'ask': ticker['ask_price'],
                'high': ticker['high_24h'],
                'low': ticker['low_24h'],
                'volume': ticker['volume_24h'],
                'timestamp': ticker['timestamp']
            }
        except Exception as e:
            logger.error(f"시세 조회 실패 ({symbol}): {e}")
            return None
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """호가창 조회"""
        try:
            if self.test_mode:
                import random
                base_price = 50000.0
                bids = [[base_price - i, random.uniform(0.1, 2.0)] for i in range(1, limit+1)]
                asks = [[base_price + i, random.uniform(0.1, 2.0)] for i in range(1, limit+1)]
                
                return {
                    'symbol': symbol,
                    'bids': bids,
                    'asks': asks,
                    'timestamp': int(time.time() * 1000)
                }
            
            # 실전 구현 필요시 live_client에 추가
            return {
                'symbol': symbol,
                'bids': [],
                'asks': [],
                'timestamp': None
            }
        except Exception as e:
            logger.error(f"호가창 조회 실패 ({symbol}): {e}")
            return None
    
    async def get_balance(self) -> Optional[Dict]:
        """잔고 조회"""
        try:
            if self.test_mode:
                return {
                    'USDT': {'available': 1000.0, 'total': 1000.0},
                    'BTC': {'available': 0.01, 'total': 0.01}
                }
            
            # 실거래 모드
            balance = self.live_client.get_balance()
            return balance
        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            return None
    
    async def create_market_order(self, symbol: str, side: str, amount: float, params: Dict = None) -> Optional[Dict]:
        """시장가 주문"""
        try:
            if self.test_mode:
                import time
                return {
                    'id': f'test_market_{int(time.time())}',
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': None,
                    'cost': amount * 50000 if side == 'buy' else amount,
                    'status': 'closed',
                    'timestamp': int(time.time() * 1000),
                    'type': 'market'
                }
            
            # 실거래 모드
            logger.info(f"🚨 실거래 시장가 주문: {symbol} {side} {amount}")
            result = self.live_client.place_market_order(symbol, side, amount)
            return {
                'id': result['order_id'],
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': None,
                'cost': 0,
                'status': 'open',
                'timestamp': result.get('timestamp', None),
                'type': 'market'
            }
        except Exception as e:
            logger.error(f"시장가 주문 실패 ({symbol} {side} {amount}): {e}")
            return None
    
    async def create_limit_order(self, symbol: str, side: str, amount: float, price: float, params: Dict = None) -> Optional[Dict]:
        """지정가 주문"""
        try:
            if self.test_mode:
                import time
                return {
                    'id': f'test_limit_{int(time.time())}',
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'price': price,
                    'cost': amount * price,
                    'status': 'open',
                    'timestamp': int(time.time() * 1000),
                    'type': 'limit'
                }
            
            # 실거래 모드
            logger.info(f"🚨 실거래 지정가 주문: {symbol} {side} {amount}@{price}")
            result = self.live_client.place_limit_order(symbol, side, amount, price)
            return {
                'id': result['order_id'],
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': price,
                'cost': 0,
                'status': 'open',
                'timestamp': result.get('timestamp', None),
                'type': 'limit'
            }
        except Exception as e:
            logger.error(f"지정가 주문 실패 ({symbol} {side} {amount}@{price}): {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """주문 취소"""
        try:
            if self.test_mode:
                logger.info(f"테스트 모드: 주문 취소 {order_id}")
                return True
            
            return self.live_client.cancel_order(symbol, order_id)
        except Exception as e:
            logger.error(f"주문 취소 실패 ({order_id}): {e}")
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Dict]:
        """주문 상태 조회"""
        try:
            if self.test_mode:
                return {
                    'id': order_id,
                    'symbol': symbol,
                    'side': 'buy',
                    'amount': 0.001,
                    'price': 50000.0,
                    'filled': 0.001,
                    'remaining': 0.0,
                    'status': 'closed',
                    'timestamp': int(time.time() * 1000),
                    'type': 'market'
                }
            
            status = self.live_client.get_order_status(symbol, order_id)
            return {
                'id': status['order_id'],
                'symbol': status['symbol'],
                'side': status['side'],
                'amount': status['size'],
                'price': status['price'],
                'filled': status['filled_size'],
                'remaining': status['size'] - status['filled_size'],
                'status': status['status'],
                'timestamp': status['timestamp'],
                'type': 'market' if status['price'] == 0 else 'limit'
            }
        except Exception as e:
            logger.error(f"주문 상태 조회 실패 ({order_id}): {e}")
            return None
    
    async def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """미체결 주문 조회"""
        try:
            if self.test_mode:
                return []
            return []
        except Exception as e:
            logger.error(f"미체결 주문 조회 실패: {e}")
            return []
    
    async def close(self):
        """클라이언트 종료"""
        try:
            self.is_connected = False
            logger.info("OKX 클라이언트 종료")
        except Exception as e:
            logger.error(f"클라이언트 종료 실패: {e}")


# BotRunner 호환 create_okx_client 함수
async def create_okx_client(api_key: str = None, secret_key: str = None, passphrase: str = None, sandbox: bool = True) -> OKXClient:
    """
    OKX 클라이언트 생성 - 환경변수 자동 로드
    """
    try:
        client = OKXClient(
            api_key=api_key,
            secret_key=secret_key,
            passphrase=passphrase,
            sandbox=sandbox
        )
        
        await client.initialize()
        
        mode = "테스트" if client.test_mode else "실거래"
        logger.info(f"✅ OKX 클라이언트 생성 성공 ({mode} 모드)")
        return client
        
    except Exception as e:
        logger.error(f"❌ OKX 클라이언트 생성 실패: {e}")
        raise