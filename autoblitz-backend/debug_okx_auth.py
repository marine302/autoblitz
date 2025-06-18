import os
import asyncio
import aiohttp
import time
import hmac
import base64
import hashlib
from dotenv import load_dotenv
import json

load_dotenv()

async def test_okx_auth():
    """OKX API 인증 테스트"""
    api_key = os.getenv('OKX_API_KEY')
    secret_key = os.getenv('OKX_SECRET_KEY')
    passphrase = os.getenv('OKX_PASSPHRASE')
    
    print('🔐 OKX API 인증 디버깅')
    print('=' * 50)
    print(f'API Key: {api_key[:8]}...{api_key[-4:]}')
    print(f'Secret Key: {secret_key[:8]}...{secret_key[-4:]}')
    print(f'Passphrase: {passphrase}')
    print('=' * 50)
    
    # 테스트 요청 준비
    timestamp = str(time.time())
    method = 'GET'
    request_path = '/api/v5/account/balance'
    
    # 서명 생성
    message = timestamp + method + request_path
    mac = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    )
    signature = base64.b64encode(mac.digest()).decode()
    
    # 헤더 설정
    headers = {
        'OK-ACCESS-KEY': api_key,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json'
    }
    
    print('📡 API 요청 정보:')
    print(f'URL: https://www.okx.com{request_path}')
    print(f'Timestamp: {timestamp}')
    print(f'Signature: {signature[:20]}...')
    print()
    
    # API 요청
    async with aiohttp.ClientSession() as session:
        url = f'https://www.okx.com{request_path}'
        
        try:
            async with session.get(url, headers=headers) as response:
                print(f'📊 응답 상태: {response.status}')
                text = await response.text()
                
                try:
                    data = json.loads(text)
                    print(f'응답 코드: {data.get("code", "N/A")}')
                    print(f'응답 메시지: {data.get("msg", "N/A")}')
                    
                    if response.status == 200 and data.get('code') == '0':
                        print('✅ API 인증 성공!')
                        if 'data' in data and data['data']:
                            print('\n💰 계좌 잔고:')
                            for item in data['data']:
                                for detail in item.get('details', []):
                                    if float(detail.get('availBal', 0)) > 0:
                                        print(f'  {detail["ccy"]}: {detail["availBal"]}')
                    else:
                        print('❌ API 인증 실패!')
                        print(f'전체 응답: {json.dumps(data, indent=2)}')
                        
                except json.JSONDecodeError:
                    print(f'❌ JSON 파싱 실패: {text[:200]}...')
                    
        except Exception as e:
            print(f'❌ 요청 실패: {e}')
            import traceback
            traceback.print_exc()
    
    # 추가 디버깅 정보
    print('\n🔍 추가 확인사항:')
    print('1. OKX 거래소에서 API 권한 확인 (읽기/거래 권한)')
    print('2. IP 화이트리스트 설정 확인')
    print('3. API 키가 테스트넷용인지 실거래용인지 확인')
    print('4. Passphrase가 API 생성시 입력한 것과 일치하는지 확인')

if __name__ == "__main__":
    asyncio.run(test_okx_auth())
