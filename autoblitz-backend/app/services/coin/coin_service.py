import sys, os; sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
"""
통합 코인 데이터 서비스
coin_data_manager.py + okx_coin_info_collector.py 통합

검증된 기능:
- 772개 코인 정보 관리
- 실시간 코인 정보 수집
- 정밀도 기반 매도량 계산
- 동적 코인 선택 시스템
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from decimal import Decimal, ROUND_DOWN

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.exchanges.okx.core.api_client_test import get_okx_client, OKXPrecisionCalculator


class CoinService:
    """통합 코인 데이터 서비스
    
    기능:
    1. 코인 정보 수집 (okx_coin_info_collector 로직)
    2. 코인 데이터 관리 (coin_data_manager 로직)  
    3. 매도량 계산 (정밀도 처리)
    4. 코인 검색 및 필터링
    """
    
    def __init__(self, data_dir: str = "app/data/coins"):
        """초기화
        
        Args:
            data_dir: 코인 데이터 저장 디렉토리
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 캐시된 데이터
        self._coin_data = None
        self._last_update = None
        
        # OKX API 클라이언트
        self.okx_client = get_okx_client(require_auth=False)
        
        # 정밀도 계산기
        self.precision_calc = OKXPrecisionCalculator()
    
    def _get_latest_data_file(self) -> Optional[Path]:
        """최신 코인 데이터 파일 경로 반환
        
        Returns:
            Path: 최신 데이터 파일 경로
        """
        # okx_coins_latest.json 심볼릭 링크 확인
        latest_link = self.data_dir / "okx_coins_latest.json"
        if latest_link.exists():
            return latest_link
        
        # 날짜 패턴으로 최신 파일 찾기
        pattern = "okx_coins_*.json"
        files = list(self.data_dir.glob(pattern))
        
        if files:
            # 파일명에서 날짜 추출하여 최신 파일 선택
            files.sort(key=lambda x: x.name, reverse=True)
            return files[0]
        
        return None
    
    def load_coin_data(self, force_reload: bool = False) -> Dict[str, Any]:
        """코인 데이터 로드 (캐싱 지원)
        
        Args:
            force_reload: 강제 재로드 여부
            
        Returns:
            Dict[str, Any]: 코인 데이터
        """
        if not force_reload and self._coin_data is not None:
            return self._coin_data
        
        data_file = self._get_latest_data_file()
        if not data_file or not data_file.exists():
            print(f"⚠️ 코인 데이터 파일이 없습니다: {self.data_dir}")
            return {}
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                self._coin_data = json.load(f)
                self._last_update = datetime.now()
                
            print(f"✅ 코인 데이터 로드 완료: {len(self._coin_data)}개 코인")
            return self._coin_data
        
        except Exception as e:
            print(f"❌ 코인 데이터 로드 실패: {str(e)}")
            return {}
    
    def get_coin_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """개별 코인 정보 조회
        
        Args:
            symbol: 코인 심볼 (예: BTC-USDT)
            
        Returns:
            Dict[str, Any]: 코인 정보
        """
        coin_data = self.load_coin_data()
        return coin_data.get(symbol)
    
    def get_trading_rules(self, symbol: str) -> Optional[Dict[str, Any]]:
        """코인 거래 규칙 조회
        
        Args:
            symbol: 코인 심볼
            
        Returns:
            Dict[str, Any]: 거래 규칙 (lot_size, min_size, 등)
        """
        coin_info = self.get_coin_info(symbol)
        if coin_info:
            return coin_info.get('trading_rules', {})
        return None
    
    def calculate_sellable_amount(self, symbol: str, total_amount: float) -> Dict[str, Any]:
        """매도 가능 수량 계산 (더스트 최소화)
        
        Args:
            symbol: 코인 심볼
            total_amount: 총 보유량
            
        Returns:
            Dict[str, Any]: 계산 결과
        """
        trading_rules = self.get_trading_rules(symbol)
        if not trading_rules:
            return {
                'success': False,
                'error': f'코인 정보를 찾을 수 없습니다: {symbol}',
                'sellable_amount': 0.0,
                'dust_amount': 0.0,
                'dust_rate': 0.0
            }
        
        try:
            lot_size = trading_rules.get('lot_size', 0.00000001)
            lot_decimals = trading_rules.get('lot_decimals', 8)
            
            # 정밀한 매도량 계산
            sellable_amount = self.precision_calc.calculate_precise_sellable_amount(
                symbol, total_amount, lot_size, lot_decimals
            )
            
            # 더스트 계산
            dust_amount = total_amount - sellable_amount
            dust_rate = (dust_amount / total_amount * 100) if total_amount > 0 else 0
            
            return {
                'success': True,
                'symbol': symbol,
                'total_amount': total_amount,
                'sellable_amount': sellable_amount,
                'dust_amount': dust_amount,
                'dust_rate': dust_rate,
                'lot_size': lot_size,
                'lot_decimals': lot_decimals
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'계산 오류: {str(e)}',
                'sellable_amount': 0.0,
                'dust_amount': 0.0,
                'dust_rate': 0.0
            }
    
    def find_coins_by_criteria(self, **criteria) -> List[Dict[str, Any]]:
        """조건에 맞는 코인 검색
        
        Args:
            **criteria: 검색 조건
                - min_volume: 최소 거래량
                - max_spread: 최대 스프레드
                - tier: 가격 티어 (HIGH, MEDIUM, LOW, MICRO)
                - state: 거래 상태
                
        Returns:
            List[Dict[str, Any]]: 조건에 맞는 코인 목록
        """
        coin_data = self.load_coin_data()
        if not coin_data:
            return []
        
        results = []
        
        for symbol, info in coin_data.items():
            # 기본 정보 확인
            if not info or 'trading_rules' not in info:
                continue
            
            match = True
            
            # 거래량 조건
            if 'min_volume' in criteria:
                volume = info.get('volume_24h', 0)
                if volume < criteria['min_volume']:
                    match = False
            
            # 티어 조건
            if 'tier' in criteria:
                tier = info.get('tier', '')
                if tier != criteria['tier']:
                    match = False
            
            # 상태 조건
            if 'state' in criteria:
                state = info.get('state', '')
                if state != criteria['state']:
                    match = False
            
            # 최대 스프레드 조건
            if 'max_spread' in criteria:
                spread = info.get('spread_rate', float('inf'))
                if spread > criteria['max_spread']:
                    match = False
            
            if match:
                results.append({
                    'symbol': symbol,
                    'info': info
                })
        
        return results
    
    def get_min_order_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """최소 주문 정보 조회
        
        Args:
            symbol: 코인 심볼
            
        Returns:
            Dict[str, Any]: 최소 주문 정보
        """
        trading_rules = self.get_trading_rules(symbol)
        if not trading_rules:
            return None
        
        return {
            'min_size': trading_rules.get('min_size', 0),
            'min_notional': trading_rules.get('min_notional', 0),
            'lot_size': trading_rules.get('lot_size', 0),
            'tick_size': trading_rules.get('tick_size', 0)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """코인 데이터 통계 정보
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        coin_data = self.load_coin_data()
        if not coin_data:
            return {'total_coins': 0}
        
        stats = {
            'total_coins': len(coin_data),
            'by_tier': {},
            'by_state': {},
            'last_update': self._last_update.isoformat() if self._last_update else None
        }
        
        # 티어별 분류
        tier_counts = {}
        state_counts = {}
        
        for symbol, info in coin_data.items():
            if not info:
                continue
            
            # 티어별 카운트
            tier = info.get('tier', 'UNKNOWN')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            
            # 상태별 카운트
            state = info.get('state', 'unknown')
            state_counts[state] = state_counts.get(state, 0) + 1
        
        stats['by_tier'] = tier_counts
        stats['by_state'] = state_counts
        
        return stats


class CoinCollector:
    """코인 정보 수집기 (okx_coin_info_collector 로직)"""
    
    def __init__(self, data_dir: str = "app/data/coins"):
        """초기화
        
        Args:
            data_dir: 데이터 저장 디렉토리
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # OKX API 클라이언트
        self.okx_client = get_okx_client(require_auth=False)
        
        # 가격 티어 기준
        self.price_tiers = {
            'HIGH': (100, float('inf')),      # $100 이상
            'MEDIUM': (1, 100),               # $1 ~ $100
            'LOW': (0.01, 1),                 # $0.01 ~ $1
            'MICRO': (0, 0.01)                # $0.01 미만
        }
    
    def count_decimal_places(self, value: float) -> int:
        """소수점 자리수 계산
        
        Args:
            value: 계산할 값
            
        Returns:
            int: 소수점 자리수
        """
        try:
            decimal_value = Decimal(str(value))
            return abs(decimal_value.as_tuple().exponent)
        except:
            return 0
    
    def safe_float_convert(self, value: Any, default: float = 0.0) -> float:
        """안전한 float 변환
        
        Args:
            value: 변환할 값
            default: 기본값
            
        Returns:
            float: 변환된 값
        """
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    async def collect_spot_instruments(self) -> List[Dict[str, Any]]:
        """SPOT 종목 정보 수집
        
        Returns:
            List[Dict[str, Any]]: 종목 정보 목록
        """
        try:
            print("📊 OKX SPOT 종목 정보 수집 중...")
            response = await self.okx_client.get_instruments('SPOT')
            
            if response and 'data' in response:
                instruments = response['data']
                print(f"✅ {len(instruments)}개 SPOT 종목 수집 완료")
                return instruments
            else:
                print("❌ 종목 정보 수집 실패")
                return []
        
        except Exception as e:
            print(f"❌ 종목 수집 오류: {str(e)}")
            return []
    
    async def collect_current_prices(self, symbols: List[str] = None) -> Dict[str, float]:
        """현재가 정보 수집
        
        Args:
            symbols: 조회할 심볼 목록 (None이면 모든 SPOT)
            
        Returns:
            Dict[str, float]: 심볼별 현재가
        """
        try:
            print("💰 현재가 정보 수집 중...")
            
            if symbols is None:
                # 모든 SPOT 종목의 현재가 수집
                url = '/api/v5/market/tickers?instType=SPOT'
                response = await self.okx_client.make_request('GET', url, is_public=True)
            else:
                # 특정 심볼들의 현재가 수집
                prices = {}
                for symbol in symbols:
                    ticker = await self.okx_client.get_ticker(symbol)
                    if ticker and 'data' in ticker and ticker['data']:
                        prices[symbol] = self.safe_float_convert(ticker['data'][0]['last'])
                return prices
            
            if response and 'data' in response:
                prices = {}
                for ticker in response['data']:
                    symbol = ticker['instId']
                    price = self.safe_float_convert(ticker['last'])
                    prices[symbol] = price
                
                print(f"✅ {len(prices)}개 종목 현재가 수집 완료")
                return prices
            else:
                print("❌ 현재가 수집 실패")
                return {}
        
        except Exception as e:
            print(f"❌ 현재가 수집 오류: {str(e)}")
            return {}
    
    def categorize_by_price(self, price: float) -> str:
        """가격에 따른 티어 분류
        
        Args:
            price: 코인 가격
            
        Returns:
            str: 가격 티어 (HIGH, MEDIUM, LOW, MICRO)
        """
        for tier, (min_price, max_price) in self.price_tiers.items():
            if min_price <= price < max_price:
                return tier
        return 'UNKNOWN'
    
    def enhance_coin_specs_with_prices(self, instruments: List[Dict], prices: Dict[str, float]) -> Dict[str, Any]:
        """코인 정보와 가격 정보 통합
        
        Args:
            instruments: 종목 정보 목록
            prices: 현재가 정보
            
        Returns:
            Dict[str, Any]: 통합된 코인 정보
        """
        enhanced_data = {}
        
        for inst in instruments:
            symbol = inst['instId']
            price = prices.get(symbol, 0.0)
            
            # 거래 규칙 추출
            lot_size = self.safe_float_convert(inst.get('lotSz', '0.00000001'))
            tick_size = self.safe_float_convert(inst.get('tickSz', '0.01'))
            min_size = self.safe_float_convert(inst.get('minSz', '0.00000001'))
            
            # 정밀도 계산
            lot_decimals = self.count_decimal_places(lot_size)
            price_decimals = self.count_decimal_places(tick_size)
            
            # 가격 티어 분류
            tier = self.categorize_by_price(price)
            
            enhanced_data[symbol] = {
                'symbol': symbol,
                'base_currency': inst.get('baseCcy', ''),
                'quote_currency': inst.get('quoteCcy', ''),
                'state': inst.get('state', ''),
                'current_price': price,
                'tier': tier,
                'trading_rules': {
                    'lot_size': lot_size,
                    'lot_decimals': lot_decimals,
                    'tick_size': tick_size,
                    'price_decimals': price_decimals,
                    'min_size': min_size,
                    'min_notional': self.safe_float_convert(inst.get('minSz', '0')) * price
                },
                'last_updated': datetime.now().isoformat()
            }
        
        return enhanced_data
    
    def save_coin_data(self, coin_data: Dict[str, Any], filename: str = None) -> str:
        """코인 데이터 저장
        
        Args:
            coin_data: 저장할 코인 데이터
            filename: 파일명 (None이면 자동 생성)
            
        Returns:
            str: 저장된 파일 경로
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"okx_coins_{timestamp}.json"
        
        file_path = self.data_dir / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(coin_data, f, indent=2, ensure_ascii=False)
            
            # 심볼릭 링크 업데이트
            latest_link = self.data_dir / "okx_coins_latest.json"
            if latest_link.exists():
                latest_link.unlink()
            latest_link.symlink_to(filename)
            
            print(f"✅ 코인 데이터 저장 완료: {file_path}")
            print(f"📄 {len(coin_data)}개 코인 데이터")
            
            return str(file_path)
        
        except Exception as e:
            print(f"❌ 데이터 저장 실패: {str(e)}")
            return ""
    
    async def collect_all_coin_data(self) -> Dict[str, Any]:
        """전체 코인 데이터 수집 (종목 정보 + 현재가)
        
        Returns:
            Dict[str, Any]: 전체 코인 데이터
        """
        try:
            print("🚀 OKX 전체 코인 데이터 수집 시작")
            print("=" * 50)
            
            # 1. SPOT 종목 정보 수집
            instruments = await self.collect_spot_instruments()
            if not instruments:
                print("❌ 종목 정보 수집 실패")
                return {}
            
            # 2. 현재가 정보 수집
            prices = await self.collect_current_prices()
            if not prices:
                print("❌ 현재가 정보 수집 실패")
                return {}
            
            # 3. 데이터 통합 및 가공
            print("🔧 데이터 통합 및 가공 중...")
            enhanced_data = self.enhance_coin_specs_with_prices(instruments, prices)
            
            # 4. 통계 정보 출력
            tier_stats = {}
            for coin_info in enhanced_data.values():
                tier = coin_info['tier']
                tier_stats[tier] = tier_stats.get(tier, 0) + 1
            
            print(f"📊 수집 완료 - 총 {len(enhanced_data)}개 코인")
            for tier, count in tier_stats.items():
                print(f"   {tier}: {count}개")
            
            return enhanced_data
        
        except Exception as e:
            print(f"❌ 전체 데이터 수집 실패: {str(e)}")
            return {}


# 전역 인스턴스 (싱글톤 패턴)
_coin_service = None

def get_coin_service() -> CoinService:
    """코인 서비스 싱글톤 인스턴스 반환
    
    Returns:
        CoinService: 코인 서비스 인스턴스
    """
    global _coin_service
    if _coin_service is None:
        _coin_service = CoinService()
    return _coin_service


if __name__ == "__main__":
    """테스트 코드"""
    async def test_coin_service():
        """코인 서비스 테스트"""
        try:
            print("🔍 통합 코인 서비스 테스트")
            print("=" * 40)
            
            # 1. 코인 서비스 인스턴스 생성
            coin_service = get_coin_service()
            
            # 2. 기존 데이터 로드 테스트
            print("📂 기존 코인 데이터 로드...")
            coin_data = coin_service.load_coin_data()
            
            if coin_data:
                print(f"✅ {len(coin_data)}개 코인 데이터 로드 성공")
                
                # 3. 개별 코인 정보 조회 테스트
                test_symbols = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']
                for symbol in test_symbols:
                    info = coin_service.get_coin_info(symbol)
                    if info:
                        price = info.get('current_price', 0)
                        tier = info.get('tier', 'UNKNOWN')
                        print(f"   {symbol}: ${price:.4f} ({tier})")
                
                # 4. 매도량 계산 테스트
                print("\n🔍 매도량 계산 테스트...")
                test_cases = [
                    ('BTC-USDT', 0.0012345),
                    ('ETH-USDT', 1.23456789),
                    ('SOL-USDT', 12.3456)
                ]
                
                for symbol, amount in test_cases:
                    result = coin_service.calculate_sellable_amount(symbol, amount)
                    if result['success']:
                        sellable = result['sellable_amount']
                        dust_rate = result['dust_rate']
                        print(f"   {symbol}: {amount} → {sellable} (더스트: {dust_rate:.6f}%)")
                
                # 5. 코인 검색 테스트
                print("\n🔍 코인 검색 테스트...")
                high_tier_coins = coin_service.find_coins_by_criteria(tier='HIGH')
                print(f"   HIGH 티어 코인: {len(high_tier_coins)}개")
                
                # 6. 통계 정보 출력
                print("\n📊 코인 데이터 통계:")
                stats = coin_service.get_statistics()
                print(f"   총 코인 수: {stats['total_coins']}")
                print(f"   티어별 분포: {stats['by_tier']}")
            
            else:
                print("❌ 기존 코인 데이터가 없음")
                print("💡 새로운 데이터 수집 테스트...")
                
                # 7. 새 데이터 수집 테스트 (기존 데이터가 없는 경우)
                collector = CoinCollector()
                new_data = await collector.collect_all_coin_data()
                
                if new_data:
                    # 데이터 저장
                    collector.save_coin_data(new_data)
                    print("✅ 새 코인 데이터 수집 및 저장 완료")
                else:
                    print("❌ 새 데이터 수집 실패")
            
            print("\n🎉 통합 코인 서비스 테스트 완료!")
            
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 테스트 실행
    asyncio.run(test_coin_service())