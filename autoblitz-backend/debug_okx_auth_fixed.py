import os
import asyncio
import aiohttp
import time
import hmac
import base64
import hashlib
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

async def test_okx_auth_fixed():
    """OKX API 인증 테스트 (타임스탬프 수정)"""
    api_key = os.getenv('OKX_API_KEY')
    secret_key = os.getenv('OKX_SECRET_KEY')
    passphrase = os.getenv('OKX_PASSPHRASE')
    
    print('🔐 OKX API 인증 디버깅 (수정판)')
    print('=' * 50)
    
    # ISO 8601 형식의 타임스탬프 (OKX 요구사항)
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
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
    print(f'Timestamp: {timestamp} (ISO 8601 형식)')
    print(f'Message: {message[:50]}...')
    print(f'Signature: {signature[:20]}...')
    print()
    
    # API 요청
    async with aiohttp.ClientSession() as session:
        url = f'https://www.okx.com{request_path}'
        
        try:
            async with session.get(url, headers=headers) as response:
                print(f'📊 응답 상태: {response.status}')
                text = await response.text()
                data = json.loads(text)
                
                print(f'응답 코드: {data.get("code", "N/A")}')
                print(f'응답 메시지: {data.get("msg", "N/A")}')
                
                if response.status == 200 and data.get('code') == '0':
                    print('\n✅ API 인증 성공! 🎉')
                    if 'data' in data and data['data']:
                        print('\n💰 계좌 잔고:')
                        for item in data['data']:
                            for detail in item.get('details', []):
                                ccy = detail.get('ccy', 'N/A')
                                avail = detail.get('availBal', '0')
                                if float(avail) > 0:
                                    print(f'  {ccy}: {avail}')
                else:
                    print('\n❌ API 인증 실패')
                    if data.get('code') == '50111':
                        print('원인: API Key가 잘못되었습니다.')
                    elif data.get('code') == '50112':
                        print('원인: 타임스탬프 형식이 잘못되었습니다.')
                    elif data.get('code') == '50113':
                        print('원인: Passphrase가 일치하지 않습니다.')
                    elif data.get('code') == '50114':
                        print('원인: IP 화이트리스트에 등록되지 않았습니다.')
                    
        except Exception as e:
            print(f'❌ 요청 실패: {e}')

if __name__ == "__main__":
    asyncio.run(test_okx_auth_fixed())
EOF
