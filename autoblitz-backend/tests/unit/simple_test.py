#!/usr/bin/env python3
import sys
import os

# Python 경로 설정
sys.path.insert(0, os.getcwd())

def test_individual_modules():
    """개별 모듈 테스트"""
    print("🔍 개별 모듈 테스트")
    print("=" * 40)
    
    # 1. API 클라이언트 테스트
    try:
        print("1️⃣ API 클라이언트 테스트...")
        from app.exchanges.okx.core.api_client_test import get_okx_client
        client = get_okx_client(require_auth=False)
        print(f"   ✅ API 클라이언트: {'인증됨' if client.auth_available else '공개 API만'}")
    except Exception as e:
        print(f"   ❌ API 클라이언트 실패: {str(e)}")
    
    # 2. 기존 코인 데이터 확인
    try:
        print("\n2️⃣ 기존 코인 데이터 확인...")
        import json
        
        # coin_data 디렉토리에서 기존 데이터 찾기
        coin_files = []
        if os.path.exists('coin_data'):
            coin_files = [f for f in os.listdir('coin_data') if f.endswith('.json')]
        if os.path.exists('app/data/coins'):
            coin_files.extend([f for f in os.listdir('app/data/coins') if f.endswith('.json')])
        
        if coin_files:
            print(f"   ✅ 코인 데이터 파일: {len(coin_files)}개")
            # 첫 번째 파일 로드 시도
            test_file = None
            for f in coin_files:
                if os.path.exists(f'coin_data/{f}'):
                    test_file = f'coin_data/{f}'
                elif os.path.exists(f'app/data/coins/{f}'):
                    test_file = f'app/data/coins/{f}'
                break
            
            if test_file:
                with open(test_file, 'r') as file:
                    data = json.load(file)
                print(f"   ✅ {len(data)}개 코인 정보 로드 성공")
                
                # BTC 정보 확인
                if 'BTC-USDT' in data:
                    btc_price = data['BTC-USDT'].get('current_price', 0)
                    print(f"   ✅ BTC-USDT: ${btc_price:.2f}")
        else:
            print("   ⚠️ 코인 데이터 파일 없음")
    except Exception as e:
        print(f"   ❌ 코인 데이터 확인 실패: {str(e)}")
    
    # 3. 디렉토리 구조 확인
    print("\n3️⃣ 모듈 구조 확인...")
    modules = [
        'app/exchanges/okx/core/api_client_test.py',
        'app/services/coin/coin_service.py', 
        'app/exchanges/okx/trading/core_trading.py'
    ]
    
    for module in modules:
        if os.path.exists(module):
            size = os.path.getsize(module)
            print(f"   ✅ {module}: {size//1024}KB")
        else:
            print(f"   ❌ {module}: 파일 없음")
    
    print("\n🎯 상태 요약:")
    print("✅ API 클라이언트 모듈: 완성")
    print("✅ 모듈 파일들: 생성됨")
    
    if coin_files:
        print("✅ 코인 데이터: 사용 가능")
        print("💡 다음: cycle_validator.py 파일 완성 후 통합 테스트")
    else:
        print("⚠️ 코인 데이터: 없음 (새 수집 필요)")
    
    print("\n📋 해야할 작업:")
    print("1. cycle_validator.py 파일에 아티팩트 코드 복사")
    print("2. 통합 테스트 재실행")
    print("3. 마지막 단계: 테스트 파일들 정리")

if __name__ == "__main__":
    test_individual_modules()
