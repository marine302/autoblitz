# okx_coin_info_collector.py - OKX 코인 정보 수집 및 관리
import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('/workspaces/autoblitz/autoblitz-backend/.env')

class OKXCoinInfoCollector:
    """OKX 거래소 모든 코인 정보 수집 및 관리"""
    
    def __init__(self, data_dir="./coin_data"):
        self.base_url = "https://www.okx.com"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # 캐시 설정
        self.cache_duration = timedelta(hours=6)  # 6시간마다 갱신
        self.coin_info_cache = {}
        
    async def make_public_request(self, endpoint):
        """공개 API 요청 (API 키 불필요)"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url + endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('code') == '0':
                        return data['data']
                return None
    
    def count_decimal_places(self, value):
        """소수점 이하 자리수만 정확히 계산 (수정판)"""
        if value == 0:
            return 0
        
        # 문자열로 받은 경우와 숫자로 받은 경우 모두 처리
        if isinstance(value, str):
            str_val = value
        else:
            # 부동소수점 정밀도 문제 해결
            str_val = f"{value:.20f}"
        
        # 불필요한 0 제거
        str_val = str_val.rstrip('0').rstrip('.')
        
        if '.' in str_val:
            decimal_part = str_val.split('.')[1]
            return len(decimal_part)
        return 0
    
    async def explore_okx_data_structure(self):
        """OKX API 실제 데이터 구조 탐색"""
        print("🔍 OKX API 데이터 구조 탐색")
        print("=" * 60)
        
        # 1. 거래쌍 정보 샘플 조회
        print("📊 거래쌍 정보 (instruments) 구조:")
        endpoint = "/api/v5/public/instruments?instType=SPOT"
        instruments = await self.make_public_request(endpoint)
        
        if instruments and len(instruments) > 0:
            # 첫 번째 샘플 출력
            sample = instruments[0]
            print(f"   샘플 심볼: {sample.get('instId', 'Unknown')}")
            print("   전체 필드:")
            for key, value in sample.items():
                print(f"     {key}: {value} ({type(value).__name__})")
            
            # VENOM-USDT 특별히 조회
            venom_data = None
            for inst in instruments:
                if inst.get('instId') == 'VENOM-USDT':
                    venom_data = inst
                    break
            
            if venom_data:
                print(f"\n🐍 VENOM-USDT 상세 정보:")
                for key, value in venom_data.items():
                    print(f"     {key}: {value}")
        
        # 2. 시세 정보 샘플 조회  
        print(f"\n💰 시세 정보 (ticker) 구조:")
        ticker_endpoint = "/api/v5/market/ticker?instId=VENOM-USDT"
        ticker = await self.make_public_request(ticker_endpoint)
        
        if ticker and len(ticker) > 0:
            sample_ticker = ticker[0]
            print("   전체 필드:")
            for key, value in sample_ticker.items():
                print(f"     {key}: {value} ({type(value).__name__})")
        
        # 3. 여러 코인 타입별 샘플 조회 (가격대별)
        print(f"\n🎯 다양한 코인 타입 샘플:")
        test_symbols = [
            "BTC-USDT",    # 고가 코인
            "ETH-USDT",    # 중고가 코인  
            "VENOM-USDT",  # 저가 코인
            "PEPE-USDT",   # 초저가 코인
            "SHIB-USDT"    # 극초저가 코인
        ]
        
        for symbol in test_symbols:
            # 거래쌍 정보
            inst_data = None
            for inst in instruments:
                if inst.get('instId') == symbol:
                    inst_data = inst
                    break
            
            if inst_data:
                print(f"\n   📋 {symbol}:")
                print(f"      minSz: {inst_data.get('minSz')}")
                print(f"      lotSz: {inst_data.get('lotSz')}")
                print(f"      tickSz: {inst_data.get('tickSz')}")
                print(f"      state: {inst_data.get('state')}")
                
                # 소수점 계산
                lot_sz = float(inst_data.get('lotSz', 0))
                tick_sz = float(inst_data.get('tickSz', 0))
                lot_decimals = self.count_decimal_places(lot_sz)
                tick_decimals = self.count_decimal_places(tick_sz)
                print(f"      lot 소수점: {lot_decimals}자리")
                print(f"      tick 소수점: {tick_decimals}자리")
                
                # 현재가 조회
                symbol_ticker_endpoint = f"/api/v5/market/ticker?instId={symbol}"
                symbol_ticker = await self.make_public_request(symbol_ticker_endpoint)
                if symbol_ticker and len(symbol_ticker) > 0:
                    price = float(symbol_ticker[0].get('last', 0))
                    min_sz = float(inst_data.get('minSz', 0))
                    min_order_usdt = min_sz * price
                    print(f"      현재가: ${price}")
                    print(f"      최소주문: {min_sz} = ${min_order_usdt:.2f} USDT")
            else:
                print(f"   ❌ {symbol} 정보 없음")
        
        # 4. 특이한 필드들 찾기
        print(f"\n🔬 모든 필드 종류 분석:")
        all_fields = set()
        field_types = {}
        
        for inst in instruments[:50]:  # 처음 50개만 분석
            for key, value in inst.items():
                all_fields.add(key)
                if key not in field_types:
                    field_types[key] = set()
                field_types[key].add(type(value).__name__)
        
        print("   발견된 모든 필드:")
        for field in sorted(all_fields):
            types = ', '.join(field_types[field])
            print(f"     {field}: {types}")
        
        return {
            'sample_instrument': sample if instruments else None,
            'sample_ticker': sample_ticker if ticker else None,
            'all_fields': all_fields,
            'field_types': field_types
        }

    def safe_float_convert(self, value, default=0.0):
        """안전한 float 변환 (빈 문자열, None 처리)"""
        if value is None or value == '' or value == 'None':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    async def collect_all_spot_instruments(self):
        """모든 현물 거래쌍 정보 수집"""
        print("📊 OKX 현물 거래쌍 정보 수집 중...")
        
        endpoint = "/api/v5/public/instruments?instType=SPOT"
        instruments = await self.make_public_request(endpoint)
        
        if not instruments:
            print("❌ 거래쌍 정보 수집 실패")
            return {}
        
        print(f"✅ {len(instruments)}개 거래쌍 발견")
        
        coin_specs = {}
        skipped_count = 0
        
        for instrument in instruments:
            symbol = instrument['instId']
            base_ccy = instrument['baseCcy']
            quote_ccy = instrument['quoteCcy']
            
            # 안전한 숫자 변환
            min_sz_str = instrument.get('minSz', '0')
            lot_sz_str = instrument.get('lotSz', '0')
            tick_sz_str = instrument.get('tickSz', '0')
            
            min_sz = self.safe_float_convert(min_sz_str)
            lot_sz = self.safe_float_convert(lot_sz_str)
            tick_sz = self.safe_float_convert(tick_sz_str)
            
            # 필수 값이 없는 경우 건너뛰기
            if min_sz == 0 or lot_sz == 0 or tick_sz == 0:
                print(f"⚠️ 건너뜀: {symbol} (min:{min_sz_str}, lot:{lot_sz_str}, tick:{tick_sz_str})")
                skipped_count += 1
                continue
            
            # 소수점 자리수 계산 (문자열 기준으로 정확하게)
            lot_decimals = self.count_decimal_places(lot_sz_str)
            tick_decimals = self.count_decimal_places(tick_sz_str)
            
            # 상태 및 제한사항
            state = instrument.get('state', 'unknown')
            max_lmt_sz = instrument.get('maxLmtSz', 'unlimited')
            max_mkt_sz = instrument.get('maxMktSz', 'unlimited')
            
            coin_spec = {
                'symbol': symbol,
                'base_currency': base_ccy,
                'quote_currency': quote_ccy,
                'trading_rules': {
                    'min_order_size': min_sz,
                    'lot_size': lot_sz,
                    'tick_size': tick_sz,
                    'lot_size_str': lot_sz_str,  # 원본 문자열 보존
                    'tick_size_str': tick_sz_str,  # 원본 문자열 보존
                    'lot_decimals': lot_decimals,
                    'tick_decimals': tick_decimals
                },
                'limits': {
                    'max_limit_order': max_lmt_sz,
                    'max_market_order': max_mkt_sz,
                    'max_limit_amount': instrument.get('maxLmtAmt', 'unlimited'),
                    'max_market_amount': instrument.get('maxMktAmt', 'unlimited')
                },
                'status': {
                    'state': state,
                    'is_tradable': state == 'live'
                },
                'extra_info': {
                    'list_time': instrument.get('listTime', ''),
                    'exp_time': instrument.get('expTime', ''),
                    'category': instrument.get('category', ''),
                    'rule_type': instrument.get('ruleType', '')
                },
                'metadata': {
                    'last_updated': datetime.now().isoformat(),
                    'data_source': 'okx_public_api'
                }
            }
            
            coin_specs[symbol] = coin_spec
        
        print(f"✅ {len(coin_specs)}개 유효한 거래쌍 수집 완료")
        if skipped_count > 0:
            print(f"⚠️ {skipped_count}개 거래쌍 건너뜀 (데이터 불완전)")
        
        return coin_specs
        """모든 현물 거래쌍 정보 수집"""
        print("📊 OKX 현물 거래쌍 정보 수집 중...")
        
        endpoint = "/api/v5/public/instruments?instType=SPOT"
        instruments = await self.make_public_request(endpoint)
        
        if not instruments:
            print("❌ 거래쌍 정보 수집 실패")
            return {}
        
        print(f"✅ {len(instruments)}개 거래쌍 발견")
        
        coin_specs = {}
        
        for instrument in instruments:
            symbol = instrument['instId']
            base_ccy = instrument['baseCcy']
            quote_ccy = instrument['quoteCcy']
            
            # 주요 정보 추출
            min_sz = float(instrument.get('minSz', 0))
            lot_sz = float(instrument.get('lotSz', 0))
            tick_sz = float(instrument.get('tickSz', 0))
            
            # 소수점 자리수 계산
            lot_decimals = self.count_decimal_places(lot_sz)
            tick_decimals = self.count_decimal_places(tick_sz)
            
            # 상태 및 제한사항
            state = instrument.get('state', 'unknown')
            max_lmt_sz = instrument.get('maxLmtSz', 'unlimited')
            max_mkt_sz = instrument.get('maxMktSz', 'unlimited')
            
            coin_spec = {
                'symbol': symbol,
                'base_currency': base_ccy,
                'quote_currency': quote_ccy,
                'trading_rules': {
                    'min_order_size': min_sz,
                    'lot_size': lot_sz,
                    'tick_size': tick_sz,
                    'lot_decimals': lot_decimals,
                    'tick_decimals': tick_decimals
                },
                'limits': {
                    'max_limit_order': max_lmt_sz,
                    'max_market_order': max_mkt_sz
                },
                'status': {
                    'state': state,
                    'is_tradable': state == 'live'
                },
                'metadata': {
                    'last_updated': datetime.now().isoformat(),
                    'data_source': 'okx_public_api'
                }
            }
            
            coin_specs[symbol] = coin_spec
        
        return coin_specs
    
    async def collect_current_prices(self, symbols=None):
        """현재 시세 정보 수집"""
        print("💰 현재 시세 정보 수집 중...")
        
        if symbols:
            # 특정 심볼들만
            prices = {}
            for symbol in symbols:
                endpoint = f"/api/v5/market/ticker?instId={symbol}"
                ticker = await self.make_public_request(endpoint)
                if ticker and len(ticker) > 0:
                    price_data = ticker[0]
                    prices[symbol] = {
                        'last_price': float(price_data.get('last', 0)),
                        'bid_price': float(price_data.get('bidPx', 0)),
                        'ask_price': float(price_data.get('askPx', 0)),
                        'volume_24h': float(price_data.get('vol24h', 0)),
                        'timestamp': price_data.get('ts', '0')
                    }
        else:
            # 모든 심볼
            endpoint = "/api/v5/market/tickers?instType=SPOT"
            tickers = await self.make_public_request(endpoint)
            
            prices = {}
            if tickers:
                for ticker in tickers:
                    symbol = ticker['instId']
                    prices[symbol] = {
                        'last_price': float(ticker.get('last', 0)),
                        'bid_price': float(ticker.get('bidPx', 0)),
                        'ask_price': float(ticker.get('askPx', 0)),
                        'volume_24h': float(ticker.get('vol24h', 0)),
                        'timestamp': ticker.get('ts', '0')
                    }
        
        print(f"✅ {len(prices)}개 코인 시세 수집 완료")
        return prices
    
    def enhance_coin_specs_with_prices(self, coin_specs, prices):
        """코인 스펙에 시세 정보 추가 및 USDT 금액 계산"""
        print("🔄 코인 정보와 시세 정보 결합 중...")
        
        enhanced_specs = {}
        
        for symbol, spec in coin_specs.items():
            enhanced_spec = spec.copy()
            
            # 시세 정보 추가
            if symbol in prices:
                price_info = prices[symbol]
                enhanced_spec['market_data'] = price_info
                
                # USDT 기준 최소 주문 금액 계산
                if price_info['last_price'] > 0:
                    min_order_usdt = spec['trading_rules']['min_order_size'] * price_info['last_price']
                    enhanced_spec['trading_rules']['min_order_usdt'] = min_order_usdt
                    
                    # 가격대별 분류
                    last_price = price_info['last_price']
                    if last_price >= 100:
                        price_tier = 'high'  # $100+
                    elif last_price >= 1:
                        price_tier = 'medium'  # $1-$100
                    elif last_price >= 0.01:
                        price_tier = 'low'  # $0.01-$1
                    else:
                        price_tier = 'micro'  # <$0.01
                    
                    enhanced_spec['market_data']['price_tier'] = price_tier
            
            enhanced_specs[symbol] = enhanced_spec
        
        return enhanced_specs
    
    def save_coin_data(self, coin_specs, filename=None):
        """코인 정보를 JSON 파일로 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"okx_coins_{timestamp}.json"
        
        filepath = self.data_dir / filename
        
        # 저장용 데이터 준비
        save_data = {
            'metadata': {
                'total_coins': len(coin_specs),
                'collected_at': datetime.now().isoformat(),
                'collector_version': '1.0.0'
            },
            'coins': coin_specs
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 코인 정보 저장 완료: {filepath}")
        
        # 최신 파일로 심볼릭 링크 생성
        latest_filepath = self.data_dir / "okx_coins_latest.json"
        if latest_filepath.exists():
            latest_filepath.unlink()
        latest_filepath.symlink_to(filename)
        
        return filepath
    
    def load_coin_data(self, filename="okx_coins_latest.json"):
        """저장된 코인 정보 로드"""
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {filepath}")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📖 코인 정보 로드 완료: {len(data['coins'])}개 코인")
        return data
    
    def analyze_coin_characteristics(self, coin_specs):
        """코인들의 특성 분석"""
        print("\n📊 코인 특성 분석")
        print("=" * 60)
        
        # 가격대별 분류
        price_tiers = {'high': [], 'medium': [], 'low': [], 'micro': []}
        lot_decimal_stats = {}
        
        tradable_coins = 0
        usdt_pairs = 0
        
        for symbol, spec in coin_specs.items():
            if spec['status']['is_tradable']:
                tradable_coins += 1
            
            if spec['quote_currency'] == 'USDT':
                usdt_pairs += 1
                
                # 가격대별 분류
                if 'market_data' in spec and 'price_tier' in spec['market_data']:
                    tier = spec['market_data']['price_tier']
                    price_tiers[tier].append(symbol)
                
                # lot 소수점 통계
                lot_decimals = spec['trading_rules']['lot_decimals']
                if lot_decimals not in lot_decimal_stats:
                    lot_decimal_stats[lot_decimals] = []
                lot_decimal_stats[lot_decimals].append(symbol)
        
        print(f"📈 전체 통계:")
        print(f"   총 거래쌍: {len(coin_specs)}개")
        print(f"   거래 가능: {tradable_coins}개")
        print(f"   USDT 페어: {usdt_pairs}개")
        
        print(f"\n💰 USDT 페어 가격대별 분포:")
        for tier, coins in price_tiers.items():
            if coins:
                print(f"   {tier.upper():6s}: {len(coins):3d}개")
                # 예시 코인 3개 표시
                examples = coins[:3]
                print(f"           예시: {', '.join(examples)}")
        
        print(f"\n📏 수량 소수점 자리수 분포:")
        for decimals in sorted(lot_decimal_stats.keys()):
            coins = lot_decimal_stats[decimals]
            print(f"   {decimals}자리: {len(coins):3d}개")
            if len(coins) <= 5:
                print(f"         {', '.join(coins)}")
            else:
                print(f"         {', '.join(coins[:3])} ... (+{len(coins)-3}개)")
    
    def get_coin_info(self, symbol):
        """특정 코인 정보 조회 (캐시 우선)"""
        # 캐시에서 조회
        if symbol in self.coin_info_cache:
            cached_data = self.coin_info_cache[symbol]
            cache_time = datetime.fromisoformat(cached_data['cached_at'])
            
            if datetime.now() - cache_time < self.cache_duration:
                return cached_data['data']
        
        # 캐시 미스 시 파일에서 로드
        data = self.load_coin_data()
        if data and symbol in data['coins']:
            coin_info = data['coins'][symbol]
            
            # 캐시에 저장
            self.coin_info_cache[symbol] = {
                'data': coin_info,
                'cached_at': datetime.now().isoformat()
            }
            
            return coin_info
        
        return None
    
    async def update_specific_coins(self, symbols):
        """특정 코인들만 업데이트"""
        print(f"🔄 {len(symbols)}개 코인 정보 업데이트 중...")
        
        # 기존 데이터 로드
        existing_data = self.load_coin_data()
        if not existing_data:
            print("❌ 기존 데이터 없음. 전체 수집을 먼저 실행하세요.")
            return
        
        # 특정 코인들의 최신 시세 수집
        updated_prices = await self.collect_current_prices(symbols)
        
        # 기존 데이터 업데이트
        updated_count = 0
        for symbol in symbols:
            if symbol in existing_data['coins'] and symbol in updated_prices:
                existing_data['coins'][symbol]['market_data'] = updated_prices[symbol]
                existing_data['coins'][symbol]['metadata']['last_updated'] = datetime.now().isoformat()
                updated_count += 1
        
        # 저장
        if updated_count > 0:
            self.save_coin_data(existing_data['coins'], "okx_coins_updated.json")
            print(f"✅ {updated_count}개 코인 정보 업데이트 완료")
        else:
            print("❌ 업데이트할 코인이 없습니다")

    async def collect_all_data(self):
        """전체 코인 정보 수집 (거래 규칙 + 시세)"""
        print("🚀 OKX 전체 코인 정보 수집 시작")
        print("=" * 60)
        
        # 1. 거래 규칙 수집
        coin_specs = await self.collect_all_spot_instruments()
        if not coin_specs:
            return None
        
        # 2. 시세 정보 수집  
        prices = await self.collect_current_prices()
        
        # 3. 정보 결합
        enhanced_specs = self.enhance_coin_specs_with_prices(coin_specs, prices)
        
        # 4. 분석
        self.analyze_coin_characteristics(enhanced_specs)
        
        # 5. 저장
        filepath = self.save_coin_data(enhanced_specs)
        
        print(f"\n🎉 전체 수집 완료!")
        print(f"📁 저장 위치: {filepath}")
        
        return enhanced_specs

async def main():
    """메인 실행 함수"""
    collector = OKXCoinInfoCollector()
    
    print("🔍 OKX 코인 정보 수집기")
    print("목표: 모든 코인의 정확한 거래 규칙과 시세 정보 수집")
    print()
    
    # 실행 옵션 선택
    print("실행 옵션을 선택하세요:")
    print("1. 🔍 OKX 데이터 구조 탐색 (처음 실행 권장)")
    print("2. 전체 코인 정보 새로 수집")
    print("3. 기존 데이터 로드 및 분석")
    print("4. 특정 코인만 업데이트")
    
    choice = input("선택 (1/2/3/4): ").strip()
    
    if choice == "1":
        # 데이터 구조 탐색
        await collector.explore_okx_data_structure()
        
    elif choice == "2":
        # 전체 수집
        await collector.collect_all_data()
        
    elif choice == "3":
        # 기존 데이터 분석
        data = collector.load_coin_data()
        if data:
            collector.analyze_coin_characteristics(data['coins'])
        
    elif choice == "4":
        # 특정 코인 업데이트
        symbols_input = input("업데이트할 심볼들 (쉼표로 구분): ").strip()
        symbols = [s.strip().upper() for s in symbols_input.split(",")]
        await collector.update_specific_coins(symbols)
        
    else:
        print("❌ 잘못된 선택입니다.")

if __name__ == "__main__":
    asyncio.run(main())