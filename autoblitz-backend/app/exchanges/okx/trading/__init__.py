"""
OKX 거래 모듈

통합된 기능:
- 핵심 거래 로직 (okx_multi_coin_test.py 통합)
- 완전한 매수→매도 사이클
- 정밀도 기반 수량 계산
"""

from .core_trading import OKXTrader

__all__ = ['OKXTrader']
