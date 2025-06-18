# app/trading/live_client.py
import os
import time
import hmac
import hashlib
import base64
import json
import requests
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SimpleOKXClient:
    """간단한 OKX 실거래 클라이언트"""
    
    def __init__(self):
        # API 키 로드 (환경변수에서)
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY') 
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        
        # 기본 설정
        self.base_url = 'https://www.okx.com'
        self.demo_mode = True  # 일단 데모 모드로 시작
        
        # API 키 확인
        if not all([self.api_key, self.secret_key, self.passphrase]):
            logger.warning("OKX API 키가 설정되지 않았습니다. 데모 모드로 작동합니다.")
            self.demo_mode = True
        else:
            logger.info("OKX API 키 확인됨")
            
        # 실거래 모드 확인
        live_mode = os.getenv('LIVE_TRADING_MODE', 'false').lower() == 'true'
        if live_mode and not self.demo_mode:
            self.demo_mode = False
            logger.warning("🚨 실거래 모드 활성화됨!")
        else:
            logger.info("💡 데모 모드로 작동 중")
    
    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """API 서명 생성"""
        if self.demo_mode:
            return "demo_signature"
            
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _get_headers(self, method: str, request_path: str, body: str = '') -> Dict[str, str]:
        """API 헤더 생성"""
        if self.demo_mode:
            return {'Content-Type': 'application/json'}
            
        timestamp = str(time.time())
        signature = self._generate_signature(timestamp, method, request_path, body)
        
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
    
    def get_account_balance(self) -> Dict:
        """계좌 잔고 조회"""
        if self.demo_mode:
            logger.info("데모 모드: 가상 잔고 반환")
            return {
                'USDT': {
                    'available': 1000.0,
                    'total': 1000.0,
                    'frozen': 0.0
                }
            }
        
        try:
            # 실제 API 호출 로직
            logger.info("실제 계좌 잔고 조회 중...")
            # TODO: 실제 OKX API 호출 구현
            return {'USDT': {'available': 100.0, 'total': 100.0, 'frozen': 0.0}}
        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            return {}
    
    def get_ticker(self, symbol: str) -> Dict:
        """시세 조회"""
        if self.demo_mode:
            logger.info(f"데모 모드: {symbol} 가상 시세 반환")
            return {
                'symbol': symbol,
                'last_price': 50000.0,  # 가상 BTC 가격
                'bid_price': 49990.0,
                'ask_price': 50010.0,
                'high_24h': 52000.0,
                'low_24h': 48000.0,
                'volume_24h': 1000.0,
                'timestamp': int(time.time() * 1000)
            }
        
        try:
            # 실제 시세 조회 (공개 API, 인증 불필요)
            url = f"{self.base_url}/api/v5/market/ticker?instId={symbol}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == '0' and data.get('data'):
                ticker_data = data['data'][0]
                return {
                    'symbol': ticker_data['instId'],
                    'last_price': float(ticker_data['last']),
                    'bid_price': float(ticker_data['bidPx']),
                    'ask_price': float(ticker_data['askPx']),
                    'high_24h': float(ticker_data['high24h']),
                    'low_24h': float(ticker_data['low24h']),
                    'volume_24h': float(ticker_data['vol24h']),
                    'timestamp': int(ticker_data['ts'])
                }
            else:
                raise Exception(f"API 응답 오류: {data}")
                
        except Exception as e:
            logger.error(f"시세 조회 실패: {e}")
            # 에러 시 가상 데이터 반환
            return self.get_ticker(symbol) if not self.demo_mode else {
                'symbol': symbol, 'last_price': 50000.0, 'bid_price': 49990.0,
                'ask_price': 50010.0, 'high_24h': 52000.0, 'low_24h': 48000.0,
                'volume_24h': 1000.0, 'timestamp': int(time.time() * 1000)
            }
    
    def place_market_order(self, symbol: str, side: str, size: float) -> Dict:
        """시장가 주문"""
        logger.info(f"주문 실행: {symbol} {side} {size}")
        
        if self.demo_mode:
            logger.info("데모 모드: 가상 주문 실행")
            return {
                'order_id': f"demo_{int(time.time())}",
                'symbol': symbol,
                'side': side,
                'size': size,
                'status': 'filled',
                'filled_size': size,
                'avg_price': 50000.0,  # 가상 체결가
                'timestamp': int(time.time() * 1000),
                'demo': True
            }
        
        try:
            # 실제 주문 실행
            logger.warning(f"🚨 실거래 주문 실행: {symbol} {side} {size}")
            
            # TODO: 실제 OKX API 주문 로직 구현
            # 지금은 데모 응답 반환
            return {
                'order_id': f"real_{int(time.time())}",
                'symbol': symbol,
                'side': side,
                'size': size,
                'status': 'submitted',
                'timestamp': int(time.time() * 1000),
                'demo': False
            }
            
        except Exception as e:
            logger.error(f"주문 실행 실패: {e}")
            raise
    
    def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """주문 상태 조회"""
        if self.demo_mode:
            return {
                'order_id': order_id,
                'symbol': symbol,
                'status': 'filled',
                'filled_size': 20.0,
                'avg_price': 50000.0,
                'timestamp': int(time.time() * 1000)
            }
        
        try:
            # 실제 주문 상태 조회
            logger.info(f"주문 상태 조회: {order_id}")
            # TODO: 실제 API 구현
            return {
                'order_id': order_id,
                'symbol': symbol,
                'status': 'filled',
                'filled_size': 20.0,
                'avg_price': 50000.0,
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            logger.error(f"주문 상태 조회 실패: {e}")
            return {}
    
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """주문 취소"""
        if self.demo_mode:
            logger.info(f"데모 모드: 주문 취소 {order_id}")
            return True
        
        try:
            # 실제 주문 취소
            logger.info(f"주문 취소: {order_id}")
            # TODO: 실제 API 구현
            return True
            
        except Exception as e:
            logger.error(f"주문 취소 실패: {e}")
            return False