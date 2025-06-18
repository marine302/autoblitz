"""
코인 데이터 서비스 모듈

통합된 기능:
- 코인 정보 관리 (coin_data_manager.py 로직)
- 코인 정보 수집 (okx_coin_info_collector.py 로직)
- 정밀도 계산 (더스트 최소화)
"""

from .coin_service import CoinService, CoinCollector, get_coin_service

__all__ = ['CoinService', 'CoinCollector', 'get_coin_service']
