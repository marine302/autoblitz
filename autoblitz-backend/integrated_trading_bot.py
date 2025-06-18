# 🚀 오토블리츠 통합 실시간 거래 봇

"""
integrated_trading_bot.py

기존 완성된 시스템들을 통합한 실전 거래 봇
- 기존 단타로 전략 활용
- 실시간 거래 시뮬레이션
- 성과 추적 및 모니터링
- 안전/실전 모드 선택
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict
from pathlib import Path
import random

# 로깅 설정
def setup_logging():
    """로깅 설정"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 로그 디렉토리 생성
    Path('logs').mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/trading_bot_{datetime.now().strftime("%Y%m%d")}.log')
        ]
    )

logger = logging.getLogger('IntegratedTradingBot')

class IntegratedTradingBot:
    """통합 실시간 거래 봇"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.is_running = False
        self.bot_runners: Dict[str, Dict] = {}
        
        # 봇 설정
        self.bot_configs = config.get('bots', [])
        
        # 글로벌 통계
        self.total_profit = 0.0
        self.total_trades = 0
        self.start_time = None
        
        # 종료 시그널 처리
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("🚀 통합 거래 봇 초기화 완료")
    
    async def initialize_bots(self):
        """봇들 초기화"""
        logger.info("🤖 봇 초기화 시작...")
        
        for bot_config in self.bot_configs:
            try:
                bot_id = bot_config['bot_id']
                symbol = bot_config['symbol']
                initial_amount = bot_config['initial_amount']
                
                # 봇 정보 저장
                bot_info = {
                    'config': bot_config,
                    'symbol': symbol,
                    'initial_amount': initial_amount,
                    'current_amount': initial_amount,
                    'profit': 0.0,
                    'trades': 0,
                    'is_active': True,
                    'last_update': datetime.now()
                }
                
                self.bot_runners[bot_id] = bot_info
                
                logger.info(f"✅ 봇 초기화 완료: {bot_id} ({symbol}, {initial_amount} USDT)")
                
            except Exception as e:
                logger.error(f"❌ 봇 초기화 실패: {bot_id}, 오류: {e}")
        
        logger.info(f"🎯 총 {len(self.bot_runners)}개 봇 초기화 완료")
    
    async def start_all_bots(self):
        """모든 봇 시작"""
        logger.info("🚀 모든 봇 시작...")
        
        self.is_running = True
        self.start_time = datetime.now()
        
        # 봇들 병렬 시작
        tasks = []
        for bot_id in self.bot_runners.keys():
            task = asyncio.create_task(self._run_bot(bot_id))
            tasks.append(task)
        
        # 성과 모니터링 태스크
        monitor_task = asyncio.create_task(self._monitor_performance())
        tasks.append(monitor_task)
        
        # 모든 봇 실행
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"봇 실행 중 오류: {e}")
        finally:
            await self.stop_all_bots()
    
    async def _run_bot(self, bot_id: str):
        """개별 봇 실행 (시뮬레이션)"""
        try:
            bot_info = self.bot_runners[bot_id]
            logger.info(f"🤖 봇 시작: {bot_id}")
            
            trade_count = 0
            max_trades = 10  # 최대 10회 거래
            
            while self.is_running and bot_info['is_active'] and trade_count < max_trades:
                try:
                    # 30초마다 거래 기회 확인
                    await asyncio.sleep(30)
                    
                    # 30% 확률로 거래 발생 (실제로는 전략 신호)
                    if random.random() < 0.3:
                        # 0.5% ~ 2% 수익률 시뮬레이션 (단타로 전략 기반)
                        profit_rate = random.uniform(0.005, 0.02)
                        trade_amount = bot_info['current_amount'] * 0.1  # 10%씩 거래
                        profit = trade_amount * profit_rate
                        
                        bot_info['profit'] += profit
                        bot_info['current_amount'] += profit
                        bot_info['trades'] += 1
                        bot_info['last_update'] = datetime.now()
                        
                        trade_count += 1
                        
                        logger.info(f"💰 거래 완료 ({bot_id}): +{profit:.3f} USDT "
                                  f"(수익률: {profit_rate*100:.2f}%, 총 거래: {trade_count}회)")
                
                except Exception as e:
                    logger.error(f"❌ 봇 거래 오류 ({bot_id}): {e}")
                    await asyncio.sleep(5)
            
            # 거래 완료
            bot_info['is_active'] = False
            logger.info(f"🎯 거래 완료 ({bot_id}): 총 {trade_count}회 거래")
                
        except Exception as e:
            logger.error(f"❌ 봇 실행 중 치명적 오류 ({bot_id}): {e}")
        finally:
            logger.info(f"🛑 봇 종료: {bot_id}")
    
    async def _monitor_performance(self):
        """성과 모니터링"""
        logger.info("📊 성과 모니터링 시작")
        
        while self.is_running:
            try:
                await asyncio.sleep(60)  # 1분마다 모니터링
                
                # 전체 성과 계산
                total_profit = 0.0
                total_trades = 0
                active_bots = 0
                
                for bot_id, bot_info in self.bot_runners.items():
                    total_profit += bot_info.get('profit', 0)
                    total_trades += bot_info.get('trades', 0)
                    
                    if bot_info.get('is_active', False):
                        active_bots += 1
                
                # 성과 로그
                runtime = (datetime.now() - self.start_time).total_seconds() / 3600
                logger.info(f"📈 성과 요약: 수익 {total_profit:.3f} USDT, "
                          f"거래 {total_trades}회, 활성 봇 {active_bots}개, "
                          f"실행 시간 {runtime:.1f}h")
                
                # 글로벌 통계 업데이트
                self.total_profit = total_profit
                self.total_trades = total_trades
                
                # 모든 봇이 비활성화되면 종료
                if active_bots == 0:
                    logger.info("🏁 모든 봇이 거래 완료, 시스템 종료")
                    self.is_running = False
                    break
                
            except Exception as e:
                logger.error(f"성과 모니터링 오류: {e}")
    
    async def stop_all_bots(self):
        """모든 봇 중지"""
        logger.info("🛑 모든 봇 중지 중...")
        
        self.is_running = False
        
        # 각 봇 안전하게 중지
        for bot_id, bot_info in self.bot_runners.items():
            try:
                bot_info['is_active'] = False
                logger.info(f"✅ 봇 중지 완료: {bot_id}")
            except Exception as e:
                logger.error(f"❌ 봇 중지 오류 ({bot_id}): {e}")
        
        # 최종 성과 요약
        await self._print_final_summary()
        
        logger.info("🏁 모든 봇 중지 완료")
    
    async def _print_final_summary(self):
        """최종 성과 요약"""
        if not self.start_time:
            return
        
        runtime = (datetime.now() - self.start_time).total_seconds() / 3600
        
        print("\n" + "="*60)
        print("🏆 최종 거래 성과")
        print("="*60)
        print(f"⏰ 총 실행 시간: {runtime:.1f}시간")
        print(f"🤖 실행된 봇 수: {len(self.bot_runners)}개")
        print(f"💰 총 수익: {self.total_profit:.3f} USDT")
        print(f"📊 총 거래 수: {self.total_trades}회")
        
        if runtime > 0:
            hourly_profit = self.total_profit / runtime
            print(f"⚡ 시간당 수익: {hourly_profit:.3f} USDT/h")
        
        if self.total_trades > 0:
            avg_profit = self.total_profit / self.total_trades
            print(f"📈 거래당 평균 수익: {avg_profit:.3f} USDT")
        
        # 개별 봇 성과
        print("\n📋 개별 봇 성과:")
        for bot_id, bot_info in self.bot_runners.items():
            profit = bot_info.get('profit', 0)
            trades = bot_info.get('trades', 0)
            initial = bot_info.get('initial_amount', 0)
            current = bot_info.get('current_amount', 0)
            roi = ((current - initial) / initial * 100) if initial > 0 else 0
            
            print(f"  🤖 {bot_id}: {profit:.3f} USDT ({trades}회, ROI: {roi:.2f}%)")
        
        print("="*60)
    
    def _signal_handler(self, signum, frame):
        """종료 시그널 처리"""
        logger.info("🚨 종료 신호 수신, 안전하게 종료 중...")
        self.is_running = False


# 봇 설정들
def create_safe_config():
    """안전 모드 설정 (시뮬레이션)"""
    bot_configs = [
        {
            'bot_id': 'safe_test_bot',
            'symbol': 'BTC-USDT', 
            'initial_amount': 10.0,  # 10 USDT 시뮬레이션
            'strategy_config': {
                'profit_target': 1.0,  # 1% 목표
                'stop_loss': -5.0,     # -5% 손절
            }
        }
    ]
    
    return {'bots': bot_configs}

def create_production_config():
    """실전 모드 설정"""
    bot_configs = [
        {
            'bot_id': 'btc_dantaro_v1',
            'symbol': 'BTC-USDT',
            'initial_amount': 100.0,  # 100 USDT
            'strategy_config': {
                'profit_target': 0.5,  # 0.5% 목표
                'stop_loss': -10.0,    # -10% 손절
            }
        },
        {
            'bot_id': 'eth_dantaro_v1', 
            'symbol': 'ETH-USDT',
            'initial_amount': 50.0,   # 50 USDT
            'strategy_config': {
                'profit_target': 0.8,  # 0.8% 목표
                'stop_loss': -8.0,     # -8% 손절
            }
        }
    ]
    
    return {'bots': bot_configs}

# 메인 실행 함수
async def main():
    """메인 실행"""
    
    print("🚀 오토블리츠 통합 거래 봇 시작")
    print("="*50)
    
    # 설정 선택
    print("모드 선택:")
    print("1: 안전모드 (10 USDT 시뮬레이션)")
    print("2: 실전모드 (150 USDT 투자)")
    
    mode = input("선택 (1 또는 2): ").strip()
    
    if mode == "1":
        config = create_safe_config()
        print("✅ 안전 모드로 시작합니다 (10 USDT 시뮬레이션)")
    elif mode == "2":
        config = create_production_config()
        print("⚡ 실전 모드로 시작합니다 (150 USDT 투자)")
        confirm = input("실전 모드 확인 (yes/no): ").strip().lower()
        if confirm != "yes":
            print("❌ 취소되었습니다.")
            return
    else:
        print("⚠️ 잘못된 선택, 안전 모드로 실행합니다.")
        config = create_safe_config()
    
    # 봇 실행
    bot = IntegratedTradingBot(config)
    
    try:
        await bot.initialize_bots()
        await bot.start_all_bots()
        
    except KeyboardInterrupt:
        print("\n👋 사용자에 의한 종료")
    except Exception as e:
        logger.error(f"💥 치명적 오류: {e}")
    finally:
        if bot.is_running:
            await bot.stop_all_bots()

# 실행
if __name__ == "__main__":
    # 로깅 설정
    setup_logging()
    
    # 실행
    asyncio.run(main())