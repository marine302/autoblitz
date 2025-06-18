# coin_data_manager.py - 코인 데이터 사용법 및 자동 관리
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp

class CoinDataManager:
    """코인 데이터 사용 및 자동 관리 시스템"""
    
    def __init__(self, data_dir="./coin_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # 캐시 설정
        self.coin_cache = {}
        self.last_update = None
        self.update_interval = timedelta(hours=6)  # 6시간마다 갱신
        
    def load_latest_data(self):
        """최신 코인 데이터 로드"""
        latest_file = self.data_dir / "okx_coins_latest.json"
        
        if not latest_file.exists():
            print("❌ 코인 데이터가 없습니다. 먼저 수집을 실행하세요.")
            return None
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.coin_cache = data['coins']
        self.last_update = datetime.now()
        
        print(f"✅ {len(self.coin_cache)}개 코인 데이터 로드 완료")
        return data
    
    def get_coin_info(self, symbol: str) -> Optional[Dict]:
        """특정 코인 정보 조회"""
        if not self.coin_cache:
            self.load_latest_data()
        
        return self.coin_cache.get(symbol.upper())
    
    def get_trading_rules(self, symbol: str) -> Optional[Dict]:
        """거래 규칙만 추출"""
        coin_info = self.get_coin_info(symbol)
        if coin_info:
            return coin_info.get('trading_rules')
        return None
    
    def calculate_sellable_amount(self, symbol: str, total_amount: float) -> Dict:
        """정확한 매도 가능 수량 계산"""
        from decimal import Decimal, ROUND_DOWN
        
        rules = self.get_trading_rules(symbol)
        if not rules:
            return {'error': f'코인 {symbol} 정보를 찾을 수 없습니다'}
        
        lot_size = rules['lot_size']
        lot_decimals = rules['lot_decimals']
        
        # 정확한 Decimal 계산
        decimal_amount = Decimal(str(total_amount))
        decimal_lot = Decimal(str(lot_size))
        
        # lot_size의 배수로 내림
        valid_units = decimal_amount // decimal_lot
        sellable_amount = float(valid_units * decimal_lot)
        
        # 소수점 자리수 제한
        quantize_format = '0.' + '0' * lot_decimals
        sellable_amount = float(Decimal(str(sellable_amount)).quantize(
            Decimal(quantize_format), rounding=ROUND_DOWN
        ))
        
        dust_amount = total_amount - sellable_amount
        
        return {
            'sellable_amount': sellable_amount,
            'dust_amount': dust_amount,
            'lot_size': lot_size,
            'lot_decimals': lot_decimals,
            'dust_percentage': (dust_amount / total_amount) * 100 if total_amount > 0 else 0
        }
    
    def get_min_order_info(self, symbol: str) -> Optional[Dict]:
        """최소 주문 정보 조회"""
        coin_info = self.get_coin_info(symbol)
        if not coin_info:
            return None
        
        rules = coin_info['trading_rules']
        market_data = coin_info.get('market_data', {})
        
        min_size = rules['min_order_size']
        current_price = market_data.get('last_price', 0)
        min_usdt = rules.get('min_order_usdt', min_size * current_price)
        
        return {
            'min_order_size': min_size,
            'min_order_usdt': min_usdt,
            'current_price': current_price,
            'symbol': symbol
        }
    
    def find_coins_by_criteria(self, **criteria) -> List[Dict]:
        """조건별 코인 검색"""
        if not self.coin_cache:
            self.load_latest_data()
        
        results = []
        
        for symbol, coin_info in self.coin_cache.items():
            match = True
            
            # 가격대 필터
            if 'price_tier' in criteria:
                tier = coin_info.get('market_data', {}).get('price_tier')
                if tier != criteria['price_tier']:
                    match = False
            
            # 소수점 자리수 필터
            if 'lot_decimals' in criteria:
                decimals = coin_info['trading_rules']['lot_decimals']
                if decimals != criteria['lot_decimals']:
                    match = False
            
            # 최소 주문 금액 범위
            if 'min_usdt_range' in criteria:
                min_range, max_range = criteria['min_usdt_range']
                min_usdt = coin_info['trading_rules'].get('min_order_usdt', 0)
                if not (min_range <= min_usdt <= max_range):
                    match = False
            
            # 거래 상태
            if 'is_tradable' in criteria:
                is_tradable = coin_info['status']['is_tradable']
                if is_tradable != criteria['is_tradable']:
                    match = False
            
            # USDT 페어만
            if 'usdt_only' in criteria and criteria['usdt_only']:
                if coin_info['quote_currency'] != 'USDT':
                    match = False
            
            if match:
                results.append({
                    'symbol': symbol,
                    'info': coin_info
                })
        
        return results
    
    def detect_new_and_delisted_coins(self, old_data_file: str = None) -> Dict:
        """신규 상장 및 상장폐지 코인 감지"""
        current_coins = set(self.coin_cache.keys()) if self.coin_cache else set()
        
        if old_data_file:
            old_file_path = self.data_dir / old_data_file
            if old_file_path.exists():
                with open(old_file_path, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                old_coins = set(old_data['coins'].keys())
            else:
                print(f"❌ 이전 데이터 파일을 찾을 수 없습니다: {old_data_file}")
                return {'error': 'Previous data not found'}
        else:
            # 가장 최근 2개 파일 비교
            json_files = sorted([f for f in self.data_dir.glob("okx_coins_*.json") 
                               if f.name != "okx_coins_latest.json"], 
                               key=lambda x: x.stat().st_mtime, reverse=True)
            
            if len(json_files) < 2:
                return {'error': 'Not enough historical data for comparison'}
            
            with open(json_files[1], 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            old_coins = set(old_data['coins'].keys())
        
        # 신규 상장
        new_coins = current_coins - old_coins
        # 상장폐지
        delisted_coins = old_coins - current_coins
        
        return {
            'new_coins': list(new_coins),
            'delisted_coins': list(delisted_coins),
            'new_count': len(new_coins),
            'delisted_count': len(delisted_coins),
            'total_current': len(current_coins),
            'total_old': len(old_coins)
        }
    
    async def auto_update_check(self):
        """자동 업데이트 필요 여부 확인"""
        if not self.last_update:
            return True
        
        return datetime.now() - self.last_update > self.update_interval
    
    def get_statistics(self) -> Dict:
        """코인 데이터 통계"""
        if not self.coin_cache:
            self.load_latest_data()
        
        stats = {
            'total_coins': len(self.coin_cache),
            'usdt_pairs': 0,
            'tradable_coins': 0,
            'price_tiers': {'high': 0, 'medium': 0, 'low': 0, 'micro': 0},
            'decimal_distribution': {},
            'min_order_ranges': {'under_1': 0, '1_to_5': 0, '5_to_10': 0, 'over_10': 0}
        }
        
        for coin_info in self.coin_cache.values():
            # USDT 페어 카운트
            if coin_info['quote_currency'] == 'USDT':
                stats['usdt_pairs'] += 1
            
            # 거래 가능 카운트
            if coin_info['status']['is_tradable']:
                stats['tradable_coins'] += 1
            
            # 가격대 분포
            tier = coin_info.get('market_data', {}).get('price_tier', 'unknown')
            if tier in stats['price_tiers']:
                stats['price_tiers'][tier] += 1
            
            # 소수점 분포
            decimals = coin_info['trading_rules']['lot_decimals']
            stats['decimal_distribution'][decimals] = stats['decimal_distribution'].get(decimals, 0) + 1
            
            # 최소 주문 금액 분포
            min_usdt = coin_info['trading_rules'].get('min_order_usdt', 0)
            if min_usdt < 1:
                stats['min_order_ranges']['under_1'] += 1
            elif min_usdt < 5:
                stats['min_order_ranges']['1_to_5'] += 1
            elif min_usdt < 10:
                stats['min_order_ranges']['5_to_10'] += 1
            else:
                stats['min_order_ranges']['over_10'] += 1
        
        return stats


# 사용 예시 및 테스트
def demo_usage():
    """사용법 데모"""
    print("🎯 코인 데이터 사용법 데모")
    print("=" * 60)
    
    manager = CoinDataManager()
    
    # 1. 기본 사용법
    print("1️⃣ 특정 코인 정보 조회:")
    venom_info = manager.get_coin_info("VENOM-USDT")
    if venom_info:
        rules = venom_info['trading_rules']
        print(f"   VENOM-USDT 거래 규칙:")
        print(f"   - 최소 주문: {rules['min_order_size']} VENOM")
        print(f"   - 수량 단위: {rules['lot_size']} ({rules['lot_decimals']}자리)")
        print(f"   - 최소 금액: ${rules.get('min_order_usdt', 0):.2f}")
    
    # 2. 매도 가능 수량 계산
    print(f"\n2️⃣ 매도 가능 수량 계산:")
    result = manager.calculate_sellable_amount("VENOM-USDT", 65.789123)
    print(f"   보유량: 65.789123 VENOM")
    print(f"   매도가능: {result['sellable_amount']} VENOM")
    print(f"   더스트: {result['dust_amount']} VENOM ({result['dust_percentage']:.4f}%)")
    
    # 3. 조건별 코인 검색
    print(f"\n3️⃣ 조건별 코인 검색:")
    
    # 6자리 소수점 코인들 (가장 흔한 패턴)
    coins_6_decimal = manager.find_coins_by_criteria(
        lot_decimals=6,
        usdt_only=True,
        is_tradable=True
    )
    print(f"   6자리 소수점 USDT 코인: {len(coins_6_decimal)}개")
    if coins_6_decimal:
        examples = [c['symbol'] for c in coins_6_decimal[:5]]
        print(f"   예시: {', '.join(examples)}")
    
    # 저가 코인들 ($0.01-$1)
    low_price_coins = manager.find_coins_by_criteria(
        price_tier='low',
        usdt_only=True
    )
    print(f"   저가 코인 (0.01-1$): {len(low_price_coins)}개")
    
    # 4. 통계 정보
    print(f"\n4️⃣ 전체 통계:")
    stats = manager.get_statistics()
    print(f"   총 코인: {stats['total_coins']}개")
    print(f"   USDT 페어: {stats['usdt_pairs']}개")
    print(f"   거래 가능: {stats['tradable_coins']}개")
    
    print(f"   소수점 분포:")
    for decimals, count in sorted(stats['decimal_distribution'].items()):
        print(f"     {decimals}자리: {count}개")
    
    # 5. 신규/폐지 코인 감지 (데이터가 있는 경우)
    print(f"\n5️⃣ 코인 변동 감지:")
    changes = manager.detect_new_and_delisted_coins()
    if 'error' not in changes:
        print(f"   신규 상장: {changes['new_count']}개")
        print(f"   상장 폐지: {changes['delisted_count']}개")
        if changes['new_coins']:
            print(f"   신규 코인: {', '.join(changes['new_coins'][:5])}")
    else:
        print(f"   {changes['error']}")


# 봇에서 실제 사용하는 방법
class TradingBot:
    """거래 봇에서 코인 데이터 활용 예시"""
    
    def __init__(self):
        self.coin_manager = CoinDataManager()
    
    async def prepare_sell_order(self, symbol: str, current_balance: float):
        """매도 주문 준비 (정확한 수량 계산)"""
        print(f"🔧 {symbol} 매도 주문 준비")
        
        # 1. 매도 가능 수량 계산
        calc_result = self.coin_manager.calculate_sellable_amount(symbol, current_balance)
        
        if calc_result.get('error'):
            return {'error': calc_result['error']}
        
        sellable = calc_result['sellable_amount']
        dust = calc_result['dust_amount']
        
        print(f"   보유량: {current_balance}")
        print(f"   매도가능: {sellable}")
        print(f"   더스트: {dust} ({calc_result['dust_percentage']:.4f}%)")
        
        # 2. 최소 주문량 체크
        min_info = self.coin_manager.get_min_order_info(symbol)
        if sellable < min_info['min_order_size']:
            return {'error': f'매도량이 최소 주문량 미만: {sellable} < {min_info["min_order_size"]}'}
        
        # 3. 주문 데이터 생성
        order_data = {
            "instId": symbol,
            "tdMode": "cash",
            "side": "sell",
            "ordType": "market",
            "sz": str(sellable)
        }
        
        return {
            'order_data': order_data,
            'sellable_amount': sellable,
            'dust_amount': dust,
            'min_order_info': min_info
        }


if __name__ == "__main__":
    # 데모 실행
    demo_usage()
    
    print("\n" + "=" * 80)
    print("🤖 봇에서 사용 예시:")
    
    # 봇 사용 예시
    bot = TradingBot()
    asyncio.run(bot.prepare_sell_order("VENOM-USDT", 65.789123))