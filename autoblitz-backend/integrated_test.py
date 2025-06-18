#!/usr/bin/env python3
"""
오토블리츠 통합 실행 테스트
파일 경로: /workspaces/autoblitz/autoblitz-backend/integrated_test.py
"""

import asyncio
import json
from datetime import datetime
from app.bot_engine.core.bot_runner import BotRunner
from app.exchanges.okx.client import create_okx_client
from app.strategies.dantaro.okx_spot_v1 import DantaroOKXSpotV1

class IntegratedBotTest:
    def __init__(self):
        self.bot = None
        self.client = None
        self.trades = []
        self.logs = []
        
    def log(self, message, level="INFO"):
        """로그 기록"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        self.logs.append(log_entry)
    
    async def test_components(self):
        """개별 컴포넌트 테스트"""
        self.log("🔧 컴포넌트 테스트 시작", "INFO")
        
        # 1. 거래소 클라이언트 테스트
        try:
            self.client = await create_okx_client(sandbox=False)
            self.log("✅ OKX 클라이언트 생성 성공", "SUCCESS")
            
            # 시세 조회
            ticker = await self.client.get_ticker('BTC-USDT')
            self.log(f"💎 BTC 가격: ${ticker['last']:,.2f}", "INFO")
            
            # 잔고 조회
            balance = await self.client.get_balance()
            for currency, data in balance.items():
                if data.get('available', 0) > 0:
                    self.log(f"💰 {currency}: {data['available']}", "INFO")
                    
        except Exception as e:
            self.log(f"❌ 거래소 연결 실패: {e}", "ERROR")
        
        # 2. 전략 테스트
        try:
            strategy_config = {
                'symbol': 'BTC-USDT',
                'capital': 20.0,
                'grid_count': 3,
                'grid_gap': 0.1,
                'multiplier': 1.5,
                'profit_target': 0.3,
                'stop_loss': -5.0
            }
            
            strategy = DantaroOKXSpotV1(strategy_config)
            self.log("✅ 전략 생성 성공", "SUCCESS")
            
            # 전략 정보
            info = strategy.get_strategy_info()
            self.log(f"📊 전략 정보: 그리드 {info['grid_count']}개, 간격 {info['grid_gap']}%", "INFO")
            
            # 시뮬레이션 시그널 생성
            market_data = {
                'price': ticker['last'] if 'ticker' in locals() else 50000,
                'volume': 100,
                'timestamp': datetime.now()
            }
            
            signal = await strategy.analyze(market_data)
            self.log(f"📈 시그널: {signal['action']} at ${signal['price']}", "INFO")
            
        except Exception as e:
            self.log(f"❌ 전략 테스트 실패: {e}", "ERROR")
    
    async def run_integrated_bot(self):
        """통합 봇 실행"""
        self.log("\n🤖 통합 봇 실행 테스트", "INFO")
        self.log("=" * 50, "INFO")
        
        # 봇 설정
        config = {
            'symbol': 'BTC-USDT',
            'capital': 20.0,
            'strategy': 'dantaro_okx_spot_v1',
            'exchange': 'okx',
            'grid_count': 3,
            'grid_gap': 0.1,
            'multiplier': 1.5,
            'profit_target': 0.3,
            'stop_loss': -5.0
        }
        
        try:
            # 컴포넌트 테스트
            await self.test_components()
            
            # 봇 생성 및 초기화
            self.log("\n🚀 봇 초기화 중...", "INFO")
            self.bot = BotRunner(1, 1, config)
            await self.bot.initialize()
            
            self.log(f"✅ 봇 ID: {self.bot.bot_id}", "SUCCESS")
            self.log(f"✅ 상태: {self.bot.state}", "SUCCESS")
            self.log(f"✅ 심볼: {self.bot.symbol}", "SUCCESS")
            self.log(f"✅ 자본금: ${self.bot.capital}", "SUCCESS")
            
            # 봇 실행 (60초)
            self.log("\n⏰ 60초간 봇 실행...", "INFO")
            self.log("💡 진행 상황을 모니터링합니다.", "INFO")
            self.log("-" * 50, "INFO")
            
            # 봇 실행 태스크
            bot_task = asyncio.create_task(self.bot.run())
            
            # 모니터링 (60초)
            for i in range(12):  # 5초마다, 총 60초
                await asyncio.sleep(5)
                elapsed = (i + 1) * 5
                
                # 상태 체크
                status = f"[{elapsed:03d}초] 봇 실행 중... "
                status += f"상태: {self.bot.state}"
                
                # 추가 정보 수집
                if hasattr(self.bot, 'total_trades'):
                    status += f", 거래: {self.bot.total_trades}건"
                if hasattr(self.bot, 'total_profit'):
                    status += f", 수익: ${self.bot.total_profit:.2f}"
                
                self.log(status, "INFO")
            
            # 봇 중지
            self.log("\n⏹️ 봇 중지 중...", "INFO")
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass
            
            # 최종 통계
            self.log("\n📊 최종 통계", "INFO")
            self.log("=" * 50, "INFO")
            self.log(f"실행 시간: 60초", "INFO")
            self.log(f"봇 상태: {self.bot.state}", "INFO")
            
            # 거래 기록이 있다면 출력
            if self.trades:
                self.log(f"총 거래: {len(self.trades)}건", "INFO")
                for trade in self.trades[-5:]:  # 최근 5건만
                    self.log(f"  - {trade}", "INFO")
            
            self.log("\n🎉 통합 테스트 완료!", "SUCCESS")
            
        except Exception as e:
            self.log(f"\n❌ 오류 발생: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            
        finally:
            # 정리
            if self.client:
                await self.client.close()
            
            # 로그 저장
            self.save_logs()
    
    def save_logs(self):
        """로그 파일 저장"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"logs/integrated_test_{timestamp}.log"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.logs))
            print(f"\n📝 로그 저장됨: {filename}")
        except Exception as e:
            print(f"❌ 로그 저장 실패: {e}")

async def main():
    """메인 함수"""
    print("🚀 오토블리츠 통합 테스트 시작")
    print(f"⏰ 시작 시간: {datetime.now()}")
    print("=" * 70)
    
    test = IntegratedBotTest()
    await test.run_integrated_bot()
    
    print("=" * 70)
    print(f"⏰ 종료 시간: {datetime.now()}")
    print("✅ 테스트 완료")

if __name__ == "__main__":
    asyncio.run(main())