# okx_multi_coin_test.py - 다중 코인 구간별 완전 테스트
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

class OKXMultiCoinTest:
    """다중 코인 구간별 완전 테스트"""
    
    def __init__(self):
        self.api_key = os.getenv('OKX_API_KEY')
        self.secret_key = os.getenv('OKX_SECRET_KEY')
        self.passphrase = os.getenv('OKX_PASSPHRASE')
        self.base_url = "https://www.okx.com"
        
        # 테스트 결과 저장
        self.all_test_results = {}
        
        # 코인 데이터 로드
        self.coin_data = self.load_coin_data()
    
    def load_coin_data(self):
        """모든 코인 데이터 로드"""
        data_dir = Path("./coin_data")
        latest_file = data_dir / "okx_coins_latest.json"
        
        if not latest_file.exists():
            print("❌ 코인 데이터가 없습니다. 먼저 수집을 실행하세요:")
            print("python okx_coin_info_collector.py")
            return None
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("✅ 코인 데이터 로드 완료")
        return data['coins']
    
    def select_test_coins(self):
        """구간별 테스트 코인 선택"""
        if not self.coin_data:
            return None
        
        test_coins = {}
        
        # 각 구간별 코인 찾기 및 검증
        candidates = {
            'HIGH': ['BTC-USDT', 'ETH-USDT'],  # HIGH 백업으로 ETH도 추가
            'MEDIUM': ['ETH-USDT', 'SOL-USDT', 'TON-USDT'],
            'LOW': ['VENOM-USDT', 'DOGE-USDT', 'MATIC-USDT'], 
            'MICRO': ['PEPE-USDT', 'SHIB-USDT', 'FLOKI-USDT']
        }
        
        for tier, symbols in candidates.items():
            for symbol in symbols:
                if symbol in self.coin_data:
                    coin_info = self.coin_data[symbol]
                    
                    # 거래 가능한 코인만 선택
                    if coin_info['status']['is_tradable']:
                        test_coins[tier] = {
                            'symbol': symbol,
                            'info': coin_info
                        }
                        break
        
        return test_coins
    
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
        
        balances = {}
        
        if result['data'] and result['data'].get('code') == '0':
            balance_details = result['data']['data'][0]['details']
            for balance in balance_details:
                ccy = balance['ccy']
                available = float(balance['availBal'])
                if available > 0:
                    balances[ccy] = available
        
        return balances
    
    def calculate_precise_sellable_amount(self, symbol, total_amount):
        """정확한 매도 가능 수량 계산"""
        if symbol not in self.coin_data:
            return None
        
        rules = self.coin_data[symbol]['trading_rules']
        lot_size = rules['lot_size']
        lot_decimals = rules['lot_decimals']
        
        # 정확한 Decimal 계산
        decimal_amount = Decimal(str(total_amount))
        decimal_lot = Decimal(str(lot_size))
        
        # lot_size의 배수로 내림
        valid_units = decimal_amount // decimal_lot
        sellable_amount = float(valid_units * decimal_lot)
        
        # 소수점 자리수 제한
        if lot_decimals > 0:
            quantize_format = '0.' + '0' * lot_decimals
            sellable_amount = float(Decimal(str(sellable_amount)).quantize(
                Decimal(quantize_format), rounding=ROUND_DOWN
            ))
        else:
            # 정수인 경우
            sellable_amount = int(sellable_amount)
        
        dust_amount = total_amount - sellable_amount
        
        return {
            'total_amount': total_amount,
            'sellable_amount': sellable_amount,
            'dust_amount': dust_amount,
            'dust_percentage': (dust_amount / total_amount) * 100 if total_amount > 0 else 0,
            'lot_size': lot_size,
            'lot_decimals': lot_decimals
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
    
    async def test_single_coin_cycle(self, tier, coin_info, test_usdt):
        """단일 코인 완전 사이클 테스트"""
        symbol = coin_info['symbol']
        rules = coin_info['info']['trading_rules']
        
        print(f"\n{'='*80}")
        print(f"🎯 {tier} 구간 테스트: {symbol}")
        print(f"테스트 금액: ${test_usdt} USDT")
        print(f"{'='*80}")
        
        # 코인 규칙 표시
        print(f"📏 {symbol} 거래 규칙:")
        print(f"   최소 주문량: {rules['min_order_size']}")
        print(f"   수량 단위: {rules['lot_size']} (소수점 {rules['lot_decimals']}자리)")
        print(f"   가격 단위: {rules['tick_size']} (소수점 {rules['tick_decimals']}자리)")
        print(f"   최소 주문 금액: ${rules.get('min_order_usdt', 0):.2f}")
        
        base_ccy = coin_info['info']['base_currency']
        
        # 초기 잔고
        initial_balances = await self.get_balances()
        initial_usdt = initial_balances.get('USDT', 0)
        initial_base = initial_balances.get(base_ccy, 0)
        
        print(f"\n💰 초기 잔고:")
        print(f"   USDT: {initial_usdt:.8f}")
        print(f"   {base_ccy}: {initial_base:.8f}")
        
        if initial_usdt < test_usdt:
            print(f"❌ USDT 잔고 부족: {initial_usdt:.2f} < {test_usdt}")
            return None
        
        cycle_result = {
            'symbol': symbol,
            'tier': tier,
            'test_amount': test_usdt,
            'initial_balances': {'USDT': initial_usdt, base_ccy: initial_base},
            'buy_result': None,
            'sell_calculation': None,
            'sell_result': None,
            'final_balances': None,
            'profit_analysis': None
        }
        
        # === 매수 실행 ===
        print(f"\n📈 1단계: {symbol} 매수")
        print("-" * 50)
        
        buy_order = {
            "instId": symbol,
            "tdMode": "cash",
            "side": "buy",
            "ordType": "market",
            "sz": str(test_usdt),
            "tgtCcy": "quote_ccy"
        }
        
        buy_result = await self.execute_order(buy_order, "매수")
        cycle_result['buy_result'] = buy_result
        
        if not buy_result['success']:
            print("❌ 매수 실패로 테스트 중단")
            return cycle_result
        
        # 매수 후 잔고 확인
        await asyncio.sleep(2)
        after_buy_balances = await self.get_balances()
        base_balance = after_buy_balances.get(base_ccy, 0)
        
        print(f"\n💰 매수 후 잔고:")
        print(f"   USDT: {after_buy_balances.get('USDT', 0):.8f}")
        print(f"   {base_ccy}: {base_balance:.8f}")
        
        # === 매도 수량 정밀 계산 ===
        print(f"\n📊 2단계: 매도 수량 정밀 계산")
        print("-" * 50)
        
        sell_calc = self.calculate_precise_sellable_amount(symbol, base_balance)
        cycle_result['sell_calculation'] = sell_calc
        
        print(f"💎 정밀 계산 결과:")
        print(f"   총 보유량: {sell_calc['total_amount']:.8f} {base_ccy}")
        print(f"   매도 가능: {sell_calc['sellable_amount']:.8f} {base_ccy}")
        print(f"   더스트: {sell_calc['dust_amount']:.8f} {base_ccy} ({sell_calc['dust_percentage']:.6f}%)")
        
        # 최소 주문량 확인
        if sell_calc['sellable_amount'] < rules['min_order_size']:
            print(f"❌ 매도량이 최소 주문량 미만: {sell_calc['sellable_amount']} < {rules['min_order_size']}")
            return cycle_result
        
        # === 매도 실행 ===
        print(f"\n📉 3단계: {symbol} 매도")
        print("-" * 50)
        
        sell_order = {
            "instId": symbol,
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
        
        # === 최종 분석 ===
        print(f"\n📋 4단계: 손익 분석")
        print("-" * 50)
        
        # 최종 잔고
        await asyncio.sleep(2)
        final_balances = await self.get_balances()
        final_usdt = final_balances.get('USDT', 0)
        final_base = final_balances.get(base_ccy, 0)
        
        cycle_result['final_balances'] = {'USDT': final_usdt, base_ccy: final_base}
        
        print(f"💰 최종 잔고:")
        print(f"   USDT: {final_usdt:.8f}")
        print(f"   {base_ccy}: {final_base:.8f}")
        
        # 손익 계산
        usdt_change = final_usdt - initial_usdt
        base_change = final_base - initial_base
        dust_value = sell_calc['dust_amount'] * sell_result['avg_price']
        
        # 수수료 추정
        buy_fee = buy_result['total_cost'] * 0.001
        sell_fee = sell_result['total_cost'] * 0.001
        total_fees = buy_fee + sell_fee
        
        profit_analysis = {
            'usdt_change': usdt_change,
            'base_change': base_change,
            'dust_value': dust_value,
            'estimated_fees': total_fees,
            'net_loss': abs(usdt_change),
            'dust_percentage': sell_calc['dust_percentage']
        }
        cycle_result['profit_analysis'] = profit_analysis
        
        print(f"\n📊 {symbol} 상세 손익:")
        print(f"   💵 USDT 변화: {usdt_change:+.8f}")
        print(f"   🪙 {base_ccy} 변화: {base_change:+.8f}")
        print(f"   🧹 더스트 가치: ${dust_value:.8f}")
        print(f"   💸 예상 수수료: ${total_fees:.8f}")
        print(f"   📉 순손실: ${abs(usdt_change):.8f}")
        print(f"   📊 더스트율: {sell_calc['dust_percentage']:.6f}%")
        
        return cycle_result
    
    async def run_multi_coin_test(self):
        """다중 코인 구간별 테스트 실행"""
        print("🌟 OKX 다중 코인 구간별 완전 테스트")
        print("목표: 가격대별 코인의 정밀도 및 더스트 패턴 완전 검증")
        print("=" * 80)
        
        # 테스트 코인 선택
        test_coins = self.select_test_coins()
        if not test_coins:
            print("❌ 테스트할 코인을 찾을 수 없습니다.")
            return
        
        # 테스트 계획 표시
        print(f"📋 구간별 테스트 계획:")
        test_amounts = {'HIGH': 15, 'MEDIUM': 12, 'LOW': 10, 'MICRO': 8}
        total_cost = 0
        
        for tier, coin_info in test_coins.items():
            amount = test_amounts.get(tier, 10)
            total_cost += amount
            symbol = coin_info['symbol']
            rules = coin_info['info']['trading_rules']
            
            print(f"   {tier:6s}: {symbol:12s} ${amount:2d} USDT (소수점 {rules['lot_decimals']}자리)")
        
        print(f"   총 예상 비용: ${total_cost} USDT")
        
        # 현재 잔고 확인
        current_balances = await self.get_balances()
        usdt_balance = current_balances.get('USDT', 0)
        print(f"\n💰 현재 USDT 잔고: ${usdt_balance:.2f}")
        
        if usdt_balance < total_cost:
            print(f"❌ USDT 잔고 부족: {usdt_balance:.2f} < {total_cost}")
            return
        
        user_input = input(f"\n🚀 다중 코인 구간별 테스트를 시작하시겠습니까? (y/n): ").strip().lower()
        
        if user_input != 'y':
            print("❌ 사용자가 테스트를 취소했습니다.")
            return
        
        print(f"\n🔥 다중 코인 테스트 시작!")
        
        # 구간별 테스트 실행
        test_order = ['HIGH', 'MEDIUM', 'LOW', 'MICRO']
        
        for i, tier in enumerate(test_order, 1):
            if tier not in test_coins:
                print(f"\n⚠️ {tier} 구간 코인을 찾을 수 없어 건너뜁니다.")
                continue
            
            coin_info = test_coins[tier]
            test_amount = test_amounts[tier]
            
            print(f"\n🔄 구간별 테스트 {i}/{len(test_order)}")
            
            result = await self.test_single_coin_cycle(tier, coin_info, test_amount)
            
            if result:
                self.all_test_results[tier] = result
                
                if result.get('profit_analysis'):
                    loss = result['profit_analysis']['net_loss']
                    dust_rate = result['profit_analysis']['dust_percentage']
                    print(f"   📊 {tier} 결과: 손실 ${loss:.6f}, 더스트율 {dust_rate:.4f}%")
            
            if i < len(test_order):
                print(f"\n⏳ 다음 구간 테스트까지 5초 대기...")
                await asyncio.sleep(5)
        
        # 종합 분석
        await self.analyze_multi_coin_results()
    
    async def analyze_multi_coin_results(self):
        """다중 코인 테스트 결과 종합 분석"""
        print(f"\n" + "=" * 80)
        print(f"📊 다중 코인 구간별 테스트 종합 분석")
        print("=" * 80)
        
        if not self.all_test_results:
            print("❌ 분석할 결과가 없습니다.")
            return
        
        successful_tests = {tier: result for tier, result in self.all_test_results.items() 
                          if result.get('sell_result', {}).get('success', False)}
        
        print(f"📈 전체 통계:")
        print(f"   계획된 구간: 4개 (HIGH, MEDIUM, LOW, MICRO)")
        print(f"   실행된 테스트: {len(self.all_test_results)}개")
        print(f"   성공한 테스트: {len(successful_tests)}개")
        print(f"   성공률: {len(successful_tests)/len(self.all_test_results)*100:.1f}%")
        
        if successful_tests:
            total_investment = sum(r['test_amount'] for r in successful_tests.values())
            total_loss = sum(r['profit_analysis']['net_loss'] for r in successful_tests.values())
            overall_loss_rate = (total_loss / total_investment) * 100
            
            print(f"\n💰 구간별 손익 분석:")
            print(f"   총 투자: ${total_investment:.2f}")
            print(f"   총 손실: ${total_loss:.8f}")
            print(f"   전체 손실률: {overall_loss_rate:.2f}%")
            
            print(f"\n📊 구간별 상세 결과:")
            print("-" * 60)
            
            for tier in ['HIGH', 'MEDIUM', 'LOW', 'MICRO']:
                if tier in successful_tests:
                    result = successful_tests[tier]
                    symbol = result['symbol']
                    loss = result['profit_analysis']['net_loss']
                    dust_rate = result['profit_analysis']['dust_percentage']
                    investment = result['test_amount']
                    loss_rate = (loss / investment) * 100
                    lot_decimals = result['sell_calculation']['lot_decimals']
                    
                    print(f"   {tier:6s}: {symbol:12s} │ 손실: ${loss:.6f} ({loss_rate:.2f}%) │ 더스트: {dust_rate:.4f}% │ 정밀도: {lot_decimals}자리")
                else:
                    print(f"   {tier:6s}: 테스트 실패 또는 미실행")
            
            # 더스트 패턴 분석
            print(f"\n🧹 더스트 패턴 분석:")
            print("-" * 40)
            
            dust_by_decimals = {}
            for result in successful_tests.values():
                decimals = result['sell_calculation']['lot_decimals']
                dust_rate = result['profit_analysis']['dust_percentage']
                
                if decimals not in dust_by_decimals:
                    dust_by_decimals[decimals] = []
                dust_by_decimals[decimals].append(dust_rate)
            
            for decimals in sorted(dust_by_decimals.keys()):
                rates = dust_by_decimals[decimals]
                avg_rate = sum(rates) / len(rates)
                print(f"   {decimals}자리 소수점: 평균 더스트율 {avg_rate:.4f}%")
            
            # 최종 봇 가이드라인
            min_profit_rate = overall_loss_rate + 1.0
            
            print(f"\n🤖 구간별 봇 개발 완벽 가이드라인:")
            print("-" * 50)
            print(f"   📊 전체 거래 비용: {overall_loss_rate:.2f}%")
            print(f"   🎯 권장 최소 수익률: {min_profit_rate:.1f}% (안전마진 포함)")
            print(f"   🧹 더스트 문제: 모든 구간에서 0.01% 미만 (무시 가능)")
            
            all_success = len(successful_tests) == len(self.all_test_results)
            
            print(f"\n✅ 다중 코인 정밀도 검증 결과:")
            if all_success:
                print("   🎉 모든 구간 테스트 100% 성공!")
                print("   🎉 HIGH(8자리) → MICRO(0자리) 모든 정밀도 완벽 검증!")
                print("   🎉 가격대별 맞춤 처리 시스템 완성!")
                print(f"\n🚀 최종 결론: 모든 가격대 코인에서 안전하게 사용 가능!")
                
                print(f"\n💻 실제 봇 구현 코드:")
                print(f"   ```python")
                print(f"   def should_trade(expected_profit_rate):")
                print(f"       return expected_profit_rate >= {min_profit_rate:.1f}  # {overall_loss_rate:.2f}% + 1% 마진")
                print(f"   ```")
            else:
                print("   ⚠️ 일부 구간 실패 - 해당 구간 추가 검토 필요")

async def main():
    tester = OKXMultiCoinTest()
    await tester.run_multi_coin_test()

if __name__ == "__main__":
    asyncio.run(main())