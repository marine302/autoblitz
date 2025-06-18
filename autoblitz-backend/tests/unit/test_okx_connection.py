# test_okx_connection.py
import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

async def test_okx_connection():
    """OKX API 연결 테스트"""
    
    print("🔌 OKX API 연결 테스트 시작...")
    print("=" * 50)
    
    # API 키 확인
    api_key = os.getenv('OKX_API_KEY')
    secret_key = os.getenv('OKX_SECRET_KEY') 
    passphrase = os.getenv('OKX_PASSPHRASE')
    sandbox = os.getenv('OKX_SANDBOX', 'false').lower() == 'true'
    
    if not all([api_key, secret_key, passphrase]):
        print("❌ API 키가 설정되지 않았습니다!")
        print("📝 .env 파일에 OKX API 정보를 확인해주세요")
        return False
    
    print(f"✅ API 키 확인됨: {api_key[:8]}...")
    print(f"🏖️ 샌드박스 모드: {'ON' if sandbox else 'OFF (실거래 모드)'}")
    print()
    
    try:
        # OKX 클라이언트 테스트를 위한 간단한 HTTP 요청
        import aiohttp
        import hmac
        import hashlib
        import base64
        from datetime import datetime
        
        # OKX API 엔드포인트
        base_url = "https://www.okx.com" if not sandbox else "https://www.okx.com"  # 실제 환경
        endpoint = "/api/v5/account/balance"
        
        # 인증 헤더 생성
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        method = 'GET'
        request_path = endpoint
        body = ''
        
        # 서명 생성
        message = timestamp + method + request_path + body
        signature = base64.b64encode(
            hmac.new(
                secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        print("🔗 OKX API 서버에 연결 중...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url + endpoint, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ OKX API 연결 성공!")
                    print(f"📊 응답 코드: {data.get('code', 'Unknown')}")
                    
                    if data.get('code') == '0':  # 성공
                        balances = data.get('data', [])
                        print("💰 계정 잔고:")
                        
                        for balance_info in balances:
                            for detail in balance_info.get('details', []):
                                ccy = detail.get('ccy')
                                available = detail.get('availBal', '0')
                                if float(available) > 0:
                                    print(f"   {ccy}: {available}")
                        
                        print()
                        print("🎉 모든 테스트 통과! OKX 연동 준비 완료!")
                        return True
                    else:
                        print(f"❌ API 오류: {data.get('msg', 'Unknown error')}")
                        return False
                else:
                    print(f"❌ HTTP 오류: {response.status}")
                    error_text = await response.text()
                    print(f"오류 내용: {error_text}")
                    return False
        
    except Exception as e:
        print(f"❌ 연결 실패: {str(e)}")
        print()
        print("🔧 다음을 확인해주세요:")
        print("   1. API 키가 정확한지")
        print("   2. API 권한이 올바른지 (Trade, Read 권한)")
        print("   3. IP 제한 설정이 맞는지")
        print("   4. 네트워크 연결 상태")
        return False

if __name__ == "__main__":
    asyncio.run(test_okx_connection())
