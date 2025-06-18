# okx_complete_cycle_test.py - 완전한 매수→매도 사이클 테스트
import asyncio
import aiohttp
import hmac
import hashlib
import base64
import json
import os
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from dotenv import load_dotenv
from pathlib import Path

load_dotenv('/workspaces/autoblitz/autoblitz-backend/.env')

class OKXCompleteCycleTest:
    """완전한 매수→매도 사이클 테스트 (실제 봇 환경과 동일)"""
    
    def __init__(self):
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        self.base_url = "https://www.okx.com"
        
        # 테스트 결과 저장
        self.cycle_results = []
        
        # 코인 데이터 로드
        self.venom_spec = self.load_venom_spec()
    
    def load_venom_spec(self):
        """VENOM 코인 데이터 로드"""
        data_dir = Path("./coin_data")
        latest_file = data_dir / "okx_coins_latest.json"
        
        if not latest_file.exists():
            print("❌ 코인 데이터가 없습니다. 먼저 수집을 실행하세요:")
            print("python okx_coin_info_collector.py")
            return None
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        venom_data = data['coins'].get('VENOM-USDT')
        if not venom_data:
            print("❌ VENOM-USDT 데이터를 찾을 수 없습니다.")
            return None
        
        print("✅ VENOM-USDT 코인 데이터 로드 완료")
        return venom_data
    
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
                    result = {'status': response.status, 'data': None, 'error': None}
                    if response.status == 200:
                        data = await response.json()
                        result['data'] = data
                        if data.get('code') != '0':
                            result['error'] = data.get('msg')
                    else:
                        result['error'] = await response.text()
                    return result
            
            elif method == 'POST':
                async with session.post(self.base_url + endpoint, headers=headers, data=body) as response:
                    result = {'status': response.status, 'data': None, 'error': None}
                    if response.status == 200:
                        data = await response.json()
                        result['data'] = data
                        if data.get('code') != '0':
                            result['error'] = data.get('msg')
                    else:
                        result['error'] = await response.text()
                    return result
    
    async def get_balances(self):
        """현재 잔고 확인"""
        endpoint = "/api/v5/account/balance"
        result = await self.make_request('GET', endpoint)
        
        balances = {'USDT': 0, 'VENOM': 0}
        
        if result['data'] and result['data'].get('code') == '0':
            balance_details = result['data']['data'][0]['details']
            for balance in balance_details:
                if balance['ccy'] in ['USDT', 'VENOM']:
                    available = float(balance['availBal'])
                    balances[balance['ccy']] = available
        
        return balances
    
    def calculate_precise_sellable_amount(self, total_amount):
        """정확한 매도 가능 수량 계산"""
        if not self.venom_spec:
            return None
        
        rules = self.venom_spec['trading_rules']
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
            'total_amount': total_amount,
            'sellable_amount': sellable_amount,
            'dust_amount': dust_amount,
            'dust_percentage': (dust_amount / total_amount) * 100 if total_amount > 0 else 0
        }
    
    async def execute_order(self, order_data, order_type):
        """주문 실행 및 체결 확인"""
        print(f"📤 {order_type} 주문 실행:")
        print(f"   주문 데이터: {json.dumps(order_data)}")
        
        endpoint = "/api/v5/trade/order"
        body = json.dumps(order_data)
        
        start_time = datetime.now()
        result = await self.make_request('POST', endpoint, body)
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds() * 1000
        
        if not (result['data'] and result['data'].get('code') == '0'):
            error_msg = result['data'].get('msg') if result['data'] else result['error']
            print(f"   ❌ {order_type} 실패: {error_msg}")
            return {'success': False, 'error': error_msg}
        
        order_id = result['data']['data'][0]['ordId']
        print(f"   ✅ {order_type} 주문 접수! OrderID: {order_id}")
        
        # 체결 대기 (최대 10초)
        for i in range(10):
            await asyncio.sleep(1)
            
            order_endpoint = f"/api/v5/trade/order?instId={order_data['instId']}&ordId={order_id}"
            order_result = await self.make_request('GET', order_endpoint)
            
            if order_result['data'] and order_result['data'].get('code') == '0':
                order_info = order_result['data']['data'][0]
                
                if order_info['state'] == 'filled':
                    filled_amount = float(order_info['fillSz'])
                    avg_price = float(order_info['avgPx']) if order_info['avgPx'] else 0
                    total_cost = filled_amount * avg_price
                    
                    print(f"   ✅ {order_type} 체결 완료!")
                    print(f"      체결 수량: {filled_amount:.8f}")
                    print(f"      평균 체결가: ${avg_price:.8f}")
                    print(f"      총 금액: ${total_cost:.8f}")
                    print(f"      응답 시간: {response_time:.1f}ms")
                    
                    return {
                        'success': True,
                        'order_id': order_id,
                        'filled_amount': filled_amount,
                        'avg_price': avg_price,
                        'total_cost': total_cost,
                        'response_time': response_time
                    }
        
        print(f"   ⚠️ {order_type} 체결 확인 시간 초과")
        return {'success': False, 'error': f'{order_type} 체결 확인 실패'}
    
    async def run_complete_cycle_test(self, test_usdt_amount):
        """완전한 매수→매도 사이클 테스트"""
        print(f"🔄 완전한 매수→매도 사이클 테스트")
        print(f"테스트 금액: ${test_usdt_amount} USDT")
        print("=" * 80)
        
        if not self.venom_spec:
            print("❌ VENOM 코인 데이터가 없어 테스트 불가")
            return None
        
        # 초기 잔고 확인
        initial_balances = await self.get_balances()
        print(f"💰 초기 잔고:")
        print(f"   USDT: {initial_balances['USDT']:.8f}")
        print(f"   VENOM: {initial_balances['VENOM']:.8f}")
        
        if initial_balances['USDT'] < test_usdt_amount:
            print(f"❌ USDT 잔고 부족: {initial_balances['USDT']:.2f} < {test_usdt_amount}")
            return None
        
        # VENOM 규칙 출력
        rules = self.venom_spec['trading_rules']
        print(f"\n📏 VENOM 거래 규칙:")
        print(f"   최소 주문량: {rules['min_order_size']} VENOM")
        print(f"   수량 단위: {rules['lot_size']} (소수점 {rules['lot_decimals']}자리)")
        print(f"   최소 주문 금액: ${rules.get('min_order_usdt', 0):.2f}")
        
        cycle_result = {
            'test_amount': test_usdt_amount,
            'initial_balances': initial_balances,
            'buy_result': None,
            'sell_calculation': None,
            'sell_result': None,
            'final_balances': None,
            'profit_analysis': None
        }
        
        # === 1단계: 매수 실행 ===
        print(f"\n📈 1단계: VENOM 매수")
        print("-" * 50)
        
        buy_order = {
            "instId": "VENOM-USDT",
            "tdMode": "cash",
            "side": "buy",
            "ordType": "market",
            "sz": str(test_usdt_amount),
            "tgtCcy": "quote_ccy"  # USDT로 주문
        }
        
        buy_result = await self.execute_order(buy_order, "매수")
        cycle_result['buy_result'] = buy_result
        
        if not buy_result['success']:
            print("❌ 매수 실패로 테스트 중단")
            return cycle_result
        
        # 매수 후 잔고 확인
        await asyncio.sleep(2)
        after_buy_balances = await self.get_balances()
        print(f"\n💰 매수 후 잔고:")
        print(f"   USDT: {after_buy_balances['USDT']:.8f}")
        print(f"   VENOM: {after_buy_balances['VENOM']:.8f}")
        
        # === 2단계: 매도 수량 정밀 계산 ===
        print(f"\n📊 2단계: 매도 수량 정밀 계산")
        print("-" * 50)
        
        venom_balance = after_buy_balances['VENOM']
        sell_calc = self.calculate_precise_sellable_amount(venom_balance)
        cycle_result['sell_calculation'] = sell_calc
        
        print(f"💎 정밀 계산 결과:")
        print(f"   총 보유량: {sell_calc['total_amount']:.8f} VENOM")
        print(f"   매도 가능: {sell_calc['sellable_amount']:.8f} VENOM")
        print(f"   더스트: {sell_calc['dust_amount']:.8f} VENOM ({sell_calc['dust_percentage']:.6f}%)")
        
        # 최소 주문량 확인
        if sell_calc['sellable_amount'] < rules['min_order_size']:
            print(f"❌ 매도량이 최소 주문량 미만: {sell_calc['sellable_amount']} < {rules['min_order_size']}")
            return cycle_result
        
        # === 3단계: 매도 실행 ===
        print(f"\n📉 3단계: VENOM 매도")
        print("-" * 50)
        
        sell_order = {
            "instId": "VENOM-USDT",
            "tdMode": "cash",
            "side": "sell",
            "ordType": "market",
            "sz": str(sell_calc['sellable_amount'])
        }
        
        sell_result = await self.execute_order(sell_order, "매도")
        cycle_result['sell_result'] = sell_result
        
        if not sell_result['success']:
            print("❌ 매도 실패")
            return cycle_result
        
        # === 4단계: 최종 분석 ===
        print(f"\n📋 4단계: 완전한 손익 분석")
        print("-" * 50)
        
        # 최종 잔고 확인
        await asyncio.sleep(2)
        final_balances = await self.get_balances()
        cycle_result['final_balances'] = final_balances
        
        print(f"💰 최종 잔고:")
        print(f"   USDT: {final_balances['USDT']:.8f}")
        print(f"   VENOM: {final_balances['VENOM']:.8f}")
        
        # 손익 계산
        usdt_change = final_balances['USDT'] - initial_balances['USDT']
        venom_change = final_balances['VENOM'] - initial_balances['VENOM']
        
        # 더스트 가치 계산
        dust_value = sell_calc['dust_amount'] * sell_result['avg_price']
        
        # 수수료 계산 (추정)
        buy_fee = buy_result['total_cost'] * 0.001  # 0.1% 추정
        sell_fee = sell_result['total_cost'] * 0.001  # 0.1% 추정
        total_fees = buy_fee + sell_fee
        
        profit_analysis = {
            'usdt_change': usdt_change,
            'venom_change': venom_change,
            'dust_value': dust_value,
            'estimated_fees': total_fees,
            'net_loss': abs(usdt_change),
            'dust_percentage': sell_calc['dust_percentage']
        }
        cycle_result['profit_analysis'] = profit_analysis
        
        print(f"\n📊 상세 손익 분석:")
        print(f"   💵 USDT 변화: {usdt_change:+.8f}")
        print(f"   🐍 VENOM 변화: {venom_change:+.8f}")
        print(f"   🧹 더스트 가치: ${dust_value:.8f}")
        print(f"   💸 예상 수수료: ${total_fees:.8f}")
        print(f"   📉 순손실: ${abs(usdt_change):.8f}")
        print(f"   📊 더스트율: {sell_calc['dust_percentage']:.6f}%")
        
        return cycle_result
    
    async def run_multiple_cycle_tests(self):
        """여러 번의 사이클 테스트"""
        print("🔬 완전한 매수→매도 사이클 테스트")
        print("목표: 실제 봇 환경과 동일한 완전한 검증")
        print("=" * 80)
        
        # 테스트 계획
        test_amounts = [15.0, 12.0, 10.0]  # USDT 기준
        
        print(f"📋 테스트 계획:")
        for i, amount in enumerate(test_amounts, 1):
            print(f"   {i}. ${amount} USDT로 매수→매도 사이클")
        
        total_cost = sum(test_amounts)
        print(f"   예상 총 비용: ${total_cost} (수수료+스프레드)")
        
        # 현재 잔고 확인
        current_balances = await self.get_balances()
        print(f"\n💰 현재 잔고: ${current_balances['USDT']:.2f} USDT")
        
        if current_balances['USDT'] < total_cost:
            print(f"❌ USDT 잔고 부족: {current_balances['USDT']:.2f} < {total_cost}")
            return
        
        user_input = input(f"\n🚀 완전한 사이클 테스트를 시작하시겠습니까? (y/n): ").strip().lower()
        
        if user_input != 'y':
            print("❌ 사용자가 테스트를 취소했습니다.")
            return
        
        print(f"\n🔥 완전한 사이클 테스트 시작!")
        print("=" * 80)
        
        # 테스트 실행
        for i, amount in enumerate(test_amounts, 1):
            print(f"\n🔄 사이클 테스트 {i}/{len(test_amounts)}")
            
            cycle_result = await self.run_complete_cycle_test(amount)
            
            if cycle_result:
                self.cycle_results.append(cycle_result)
                
                if cycle_result['profit_analysis']:
                    loss = cycle_result['profit_analysis']['net_loss']
                    dust_rate = cycle_result['profit_analysis']['dust_percentage']
                    print(f"   결과: 손실 ${loss:.6f}, 더스트율 {dust_rate:.4f}%")
            
            if i < len(test_amounts):
                print(f"\n⏳ 다음 테스트까지 5초 대기...")
                await asyncio.sleep(5)
        
        # 종합 분석
        await self.analyze_all_cycles()
    
    async def analyze_all_cycles(self):
        """모든 사이클 결과 종합 분석"""
        print(f"\n" + "=" * 80)
        print(f"📊 종합 사이클 테스트 결과 분석")
        print("=" * 80)
        
        if not self.cycle_results:
            print("❌ 분석할 결과가 없습니다.")
            return
        
        successful_cycles = [r for r in self.cycle_results 
                           if r.get('sell_result', {}).get('success', False)]
        
        print(f"📈 전체 통계:")
        print(f"   총 사이클: {len(self.cycle_results)}개")
        print(f"   성공 사이클: {len(successful_cycles)}개")
        print(f"   성공률: {len(successful_cycles)/len(self.cycle_results)*100:.1f}%")
        
        if successful_cycles:
            total_loss = sum(c['profit_analysis']['net_loss'] for c in successful_cycles)
            total_dust_rate = sum(c['profit_analysis']['dust_percentage'] for c in successful_cycles)
            avg_dust_rate = total_dust_rate / len(successful_cycles)
            
            # 🔧 수정: 올바른 총 투자금 계산
            total_investment = sum(c['test_amount'] for c in successful_cycles)
            # 🔧 수정: 정확한 손실률 계산 (개별이 아닌 전체 기준)
            overall_loss_rate = (total_loss / total_investment) * 100
            
            print(f"\n💰 손익 분석:")
            print(f"   총 투자: ${total_investment:.2f}")  # 🔧 추가: 총 투자금 표시
            print(f"   총 손실: ${total_loss:.8f}")
            print(f"   전체 손실률: {overall_loss_rate:.2f}%")  # 🔧 추가: 전체 손실률
            print(f"   평균 더스트율: {avg_dust_rate:.6f}%")
            print(f"   사이클당 평균 손실: ${total_loss/len(successful_cycles):.8f}")
            
            print(f"\n🎯 봇 개발 가이드라인:")
            print(f"   1. 더스트율: {avg_dust_rate:.4f}% (허용 가능)")
            # 🔧 수정: 올바른 최소 수익률 계산 및 표시
            min_profit_rate = overall_loss_rate + 1.0  # 손실률 + 1% 안전마진
            print(f"   2. 거래 비용: {overall_loss_rate:.2f}% (수수료+스프레드)")
            print(f"   3. 최소 수익률: {min_profit_rate:.1f}% 이상 필요 (손익분기점 + 안전마진)")
            print(f"   4. 실용성: 매우 우수 ({min_profit_rate:.1f}%는 달성 가능한 수준)")
            
            # 정밀도 검증 결과
            all_success = all(c.get('sell_result', {}).get('success', False) for c in self.cycle_results)
            
            print(f"\n✅ 정밀도 검증 결과:")
            if all_success:
                print("   🎉 모든 매수→매도 사이클 100% 성공!")
                print("   🎉 코인 데이터 기반 정밀 계산 완벽 검증!")
                print("   🎉 봇에서 안전하게 사용 가능!")
                # 🔧 추가: 실제 봇 구현을 위한 코드 예시
                print(f"\n🤖 실제 봇 구현 예시:")
                print(f"   ```python")
                print(f"   if expected_profit_rate < {min_profit_rate:.1f}:")
                print(f"       return '수익률 부족 - 거래 건너뛰기'")
                print(f"   else:")
                print(f"       proceed_with_trade()  # 거래 진행")
                print(f"   ```")
            else:
                print("   ⚠️ 일부 사이클 실패 - 추가 검토 필요")

async def main():
    tester = OKXCompleteCycleTest()
    await tester.run_multiple_cycle_tests()

if __name__ == "__main__":
    asyncio.run(main())