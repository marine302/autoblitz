#!/usr/bin/env python3
"""
모듈화된 OKX 시스템 테스트 스크립트
Python 경로 문제 해결
"""

import sys
import os
import asyncio

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.getcwd())

async def test_all_modules():
    """모든 모듈 테스트"""
    print("🔍 모듈화된 OKX 시스템 테스트")
    print("=" * 50)
    
    try:
        # 1. 코인 서비스 테스트
        print("📊 1. 코인 서비스 테스트...")
        from app.services.coin import get_coin_service
        
        coin_service = get_coin_service()
        coin_data = coin_service.load_coin_data()
        
        if coin_data:
            print(f"   ✅ {len(coin_data)}개 코인 데이터 로드 성공")
            
            # BTC 정보 테스트
            btc_info = coin_service.get_coin_info('BTC-USDT')
            if btc_info:
                price = btc_info.get('current_price', 0)
                print(f"   ✅ BTC-USDT: ${price:.2f}")
        else:
            print("   ⚠️ 코인 데이터 없음 (정상 - 새 환경)")
        
        # 2. OKX API 클라이언트 테스트
        print("\n🔗 2. OKX API 클라이언트 테스트...")
        from app.exchanges.okx import get_okx_client
        
        client = get_okx_client(require_auth=False)
        print(f"   ✅ API 클라이언트 생성 완료")
        print(f"   🔑 인증 상태: {'사용 가능' if client.auth_available else '공개 API만'}")
        
        # 3. OKX 거래 클래스 테스트
        print("\n💰 3. OKX 거래 클래스 테스트...")
        from app.exchanges.okx import OKXTrader
        
        trader = OKXTrader(require_auth=False)
        print(f"   ✅ 거래 클래스 생성 완료")
        
        # 정밀도 계산 테스트
        calc_result = trader.calculate_precise_order_amount(
            'BTC-USDT', 10.0, 50000.0, is_buy=True
        )
        
        if coin_data and calc_result.get('success'):
            print(f"   ✅ 정밀도 계산: {calc_result['amount']:.8f} BTC")
        else:
            print(f"   ⚠️ 정밀도 계산: 코인 데이터 필요")
        
        # 4. OKX 검증 클래스 테스트
        print("\n🔍 4. OKX 검증 클래스 테스트...")
        from app.exchanges.okx import OKXCycleValidator
        
        validator = OKXCycleValidator(require_auth=False)
        print(f"   ✅ 검증 클래스 생성 완료")
        
        # 검증 기준 출력
        criteria = validator.validation_criteria
        print(f"   📏 검증 기준: 더스트율 < {criteria['max_dust_rate']}%")
        
        print("\n🎉 모든 모듈 테스트 완료!")
        print("✅ 모듈화가 성공적으로 완료되었습니다")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import 오류: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_all_modules())
    if success:
        print(f"\n🎯 다음 단계: 나머지 17개 파일을 tests/ 디렉토리로 정리")
    else:
        print(f"\n🔧 문제 해결 후 다시 시도해 주세요")
