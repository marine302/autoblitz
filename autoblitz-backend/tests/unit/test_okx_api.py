import asyncio
import aiohttp
import json

async def test_okx_public_api():
    """OKX 공개 API 간단 테스트"""
    try:
        print("🔍 OKX 공개 API 테스트")
        print("=" * 30)
        
        async with aiohttp.ClientSession() as session:
            # BTC-USDT 현재가 조회
            url = "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"
            async with session.get(url) as response:
                data = await response.json()
                
                if data['code'] == '0' and data['data']:
                    price = data['data'][0]['last']
                    print(f"✅ BTC-USDT 현재가: {price} USDT")
                else:
                    print("❌ 현재가 조회 실패")
                    return
            
            # SPOT 종목 수 조회
            url = "https://www.okx.com/api/v5/public/instruments?instType=SPOT"
            async with session.get(url) as response:
                data = await response.json()
                
                if data['code'] == '0' and data['data']:
                    count = len(data['data'])
                    print(f"✅ 총 {count}개 SPOT 종목 확인")
                else:
                    print("❌ 종목 조회 실패")
        
        print("\n🎉 OKX API 연결 성공!")
        print("✅ 공통 API 클라이언트 기반 준비 완료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")

# 테스트 실행
asyncio.run(test_okx_public_api())
