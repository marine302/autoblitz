# okx_real_trade_test.py - OKX 실제 매매 테스트
import asyncio
import aiohttp
import hmac
import hashlib
import base64
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import time

load_dotenv('/workspaces/autoblitz/autoblitz-backend/.env')

class OKXRealTradeTest:
    """OKX 실제 매매 테스트 (소량으로 안전하게)"""
    
    def __init__(self):
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        self.base_url = "https://www.okx.com"
        
        # 테스트 결과 저장
        self.test_results = []
    
    async def make_request(self, method, endpoint, body=''):
        """OKX API 요청"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        message = timestamp + method + endpoint + body
        signature = base64.b64encode(
            hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256).digest()
        ).decode()
        
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            if method == 'GET':
                async with session.get(self.base_url + endpoint, headers=headers) as response:
                    result = {
                        'status': response.status,
                        'data': None,
                        'error': None,
                        'raw_response': None
                    }
                    
                    try:
                        result['raw_response'] = await response.text()
                        if response.status == 200:
                            data = await response.json()
                            result['data'] = data
                        else:
                            result['error'] = result['raw_response']
                    except Exception as e:
                        result['error'] = str(e)
                    
                    return result
            
            elif method == 'POST':
                async with session.post(self.base_url + endpoint, headers=headers, data=body) as response:
                    result = {
                        'status': response.status,
                        'data': None,
                        'error': None,
                        'raw_response': None
                    }
                    
                    try:
                        result['raw_response'] = await response.text()
                        if response.status == 200:
                            data = await response.json()
                            result['data'] = data
                        else:
                            result['error'] = result['raw_response']
                    except Exception as e:
                        result['error'] = str(e)
                    
                    return result
    
    async def get_balance(self):
        """잔고 조회"""
        endpoint = "/api/v5/account/balance"
        result = await self.make_request('GET', endpoint)
        
        if result['data'] and result['data'].get('code') == '0':
            balances = result['data']['data'][0]['details']
            for balance in balances:
                if balance['ccy'] in ['VENOM', 'USDT']:
                    print(f"   {balance['ccy']}: {float(balance['availBal']):.6f}")
            return balances
        else:
            print(f"❌ 잔고 조회 실패: {result['error']}")
            return None
    
    async def place_test_order(self, side, amount, test_name=""):
        """테스트 주문 실행"""
        print(f"\n🧪 테스트: {test_name}")
        print(f"   주문: {side.upper()} {amount} VENOM")
        
        order_data = {
            "instId": "VENOM-USDT",
            "tdMode": "cash",
            "side": side,
            "ordType": "market",
            "sz": str(amount)
        }
        
        print(f"   주문 데이터: {json.dumps(order_data)}")
        
        # 실제 주문 실행
        endpoint = "/api/v5/trade/order"
        body = json.dumps(order_data)
        
        start_time = time.time()
        result = await self.make_request('POST', endpoint, body)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # ms
        
        # 결과 분석
        success = False
        order_id = None
        error_code = None
        error_msg = None
        
        if result['data']:
            if result['data'].get('code') == '0':
                success = True
                order_id = result['data']['data'][0]['ordId']
                print(f"   ✅ 주문 성공! OrderID: {order_id}")
            else:
                error_code = result['data'].get('code')
                error_msg = result['data'].get('msg')
                print(f"   ❌ 주문 실패: [{error_code}] {error_msg}")
        else:
            error_msg = result['error']
            print(f"   ❌ API 오류: {error_msg}")
        
        print(f"   응답 시간: {response_time:.2f}ms")
        
        # 결과 저장
        test_result = {
            'test_name': test_name,
            'side': side,
            'amount': str(amount),
            'success': success,
            'order_id': order_id,
            'error_code': error_code,
            'error_msg': error_msg,
            'response_time': response_time,
            'timestamp': datetime.now().isoformat()
        }
        
        self.test_results.append(test_result)
        
        # 주문 성공 시 상태 확인
        if success and order_id:
            await asyncio.sleep(1)  # 1초 대기
            await self.check_order_status(order_id)
        
        return test_result
    
    async def check_order_status(self, order_id):
        """주문 상태 확인"""
        endpoint = f"/api/v5/trade/order?instId=VENOM-USDT&ordId={order_id}"
        result = await self.make_request('GET', endpoint)
        
        if result['data'] and result['data'].get('code') == '0':
            order = result['data']['data'][0]
            status = order['state']
            filled_sz = float(order['fillSz'])
            avg_px = float(order['avgPx']) if order['avgPx'] else 0
            
            print(f"   📊 주문 상태: {status}")
            print(f"   📊 체결 수량: {filled_sz}")
            if avg_px > 0:
                print(f"   📊 평균 체결가: ${avg_px:.5f}")
        else:
            print(f"   ❌ 주문 상태 조회 실패")
    
    async def safe_test_sequence(self):
        """안전한 테스트 시퀀스"""
        print("🛡️ 안전한 매매 테스트 시작")
        print("=" * 60)
        
        # 현재 잔고 확인
        print("💰 현재 잔고:")
        await self.get_balance()
        
        print("\n⚠️ 주의사항:")
        print("- 최소 수량으로 테스트합니다")
        print("- 각 테스트 간 3초 대기합니다")
        print("- 실패해도 손실은 미미합니다")
        
        # 사용자 확인
        print("\n계속 진행하시겠습니까? (y/n): ", end="")
        
        # 실제 환경에서는 input() 사용, 여기서는 자동 진행
        print("y (자동 진행)")
        
        # 테스트 케이스들
        test_cases = [
            # 1단계: 안전한 최소 수량
            ("sell", 10.000, "최소 수량 (안전)"),
            ("sell", 10.001, "lotSz + 0.001"),
            ("sell", 10.002, "lotSz + 0.002"),
            
            # 2단계: 문제 수량 패턴
            ("sell", 61.796, "정확한 lotSz 배수"),
            ("sell", 61.797, "실패했던 수량 재테스트"),
            
            # 3단계: 다양한 소수점 자리수
            ("sell", 15.1, "소수점 1자리"),
            ("sell", 15.12, "소수점 2자리"),
            ("sell", 15.123, "소수점 3자리"),
            ("sell", 15.12345678, "소수점 8자리"),
        ]
        
        print(f"\n🧪 총 {len(test_cases)}개 테스트 진행")
        print("-" * 60)
        
        for i, (side, amount, test_name) in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}]", end="")
            await self.place_test_order(side, amount, test_name)
            
            # 테스트 간 대기 (Rate Limit 방지)
            if i < len(test_cases):
                print("   ⏱️ 3초 대기...")
                await asyncio.sleep(3)
        
        # 최종 잔고 확인
        print(f"\n💰 테스트 후 잔고:")
        await self.get_balance()
    
    def analyze_results(self):
        """테스트 결과 분석"""
        print("\n" + "=" * 80)
        print("📊 테스트 결과 분석")
        print("=" * 80)
        
        success_count = sum(1 for r in self.test_results if r['success'])
        total_count = len(self.test_results)
        
        print(f"전체 테스트: {total_count}개")
        print(f"성공: {success_count}개")
        print(f"실패: {total_count - success_count}개")
        print(f"성공률: {(success_count/total_count)*100:.1f}%")
        
        print(f"\n📋 상세 결과:")
        print("-" * 80)
        
        for i, result in enumerate(self.test_results, 1):
            status = "✅" if result['success'] else "❌"
            print(f"{i:2d}. {status} {result['test_name']}")
            print(f"    수량: {result['amount']} | 응답시간: {result['response_time']:.0f}ms")
            
            if not result['success']:
                print(f"    오류: [{result['error_code']}] {result['error_msg']}")
        
        # 패턴 분석
        print(f"\n🔍 패턴 분석:")
        print("-" * 40)
        
        # 성공한 수량들의 패턴
        success_amounts = [r['amount'] for r in self.test_results if r['success']]
        failed_amounts = [r['amount'] for r in self.test_results if not r['success']]
        
        if success_amounts:
            print(f"✅ 성공한 수량들:")
            for amount in success_amounts:
                decimal_places = len(amount.split('.')[1]) if '.' in amount else 0
                print(f"   {amount} (소수점 {decimal_places}자리)")
        
        if failed_amounts:
            print(f"\n❌ 실패한 수량들:")
            for amount in failed_amounts:
                decimal_places = len(amount.split('.')[1]) if '.' in amount else 0
                print(f"   {amount} (소수점 {decimal_places}자리)")
        
        # 결론
        print(f"\n🎯 결론:")
        if success_count == total_count:
            print("모든 테스트 성공! 이전 문제는 일시적이었을 수 있습니다.")
        elif success_count == 0:
            print("모든 테스트 실패! 계좌나 API 설정 문제일 수 있습니다.")
        else:
            print(f"부분적 성공! 특정 패턴에서만 실패가 발생합니다.")

async def main():
    tester = OKXRealTradeTest()
    
    print("🔍 OKX 실제 매매 테스트")
    print("목표: 수량 오류의 정확한 원인 파악")
    print()
    
    try:
        # 실제 테스트 실행
        await tester.safe_test_sequence()
        
        # 결과 분석
        tester.analyze_results()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자가 테스트를 중단했습니다.")
        tester.analyze_results()
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        if tester.test_results:
            tester.analyze_results()

if __name__ == "__main__":
    print("⚠️ 경고: 실제 거래가 실행됩니다!")
    print("소량이지만 실제 자금이 사용됩니다.")
    print()
    
    asyncio.run(main())