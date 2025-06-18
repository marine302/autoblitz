# 🚀 오토블리츠 메인 거래 봇 실행기

"""
main_trading_bot.py

완전한 자동매매 봇을 실행하는 메인 스크립트
- 환경 설정 로드
- 실시간 거래 엔진 시작
- 웹 대시보드 연동
- 로깅 및 모니터링
"""

import asyncio
import logging
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import argparse

# 프로젝트 루트 패스 추가
sys.path.append(str(Path(__file__).parent))

from app.engines.realtime_trading_engine import TradingEngineController, TradingResult
from app.utils.logger import setup_logger
from app.utils.config import load_config, validate_config
from app.utils.notifications import NotificationManager

class AutoBlitzBot:
    """오토블리츠 메인 봇 클래스"""
    
    def __init__(self, config_path: str = None):
        # 설정 로드
        self.config = load_config(config_path or '.env')
        validate_config(self.config)
        
        # 로거 설정
        self.logger = setup_logger('AutoBlitzBot', self.config.get('log_level', 'INFO'))
        
        # 거래 엔진 컨트롤러
        self.engine_controller = TradingEngineController(self.config)
        
        # 알림 매니저
        self.notification_manager = NotificationManager(self.config)
        
        # 통계 데이터
        self.start_time = None
        self.session_stats = {
            'total_trades': 0,
            'profitable_trades': 0,
            'total_profit': 0.0,
            'max_drawdown': 0.0,
            'strategies_count': 0
        }
        
        self.logger.info("🤖 오토블리츠 봇 초기화 완료")
    
    async def initialize_strategies(self) -> List[Dict]:
        """전략 설정 초기화"""
        try:
            strategies_config = []
            
            # 기본 전략들 (설정에서 로드)
            default_strategies = self.config.get('default_strategies', [])
            
            for strategy_config in default_strategies:
                symbol = strategy_config.get('symbol')
                capital = strategy_config.get('capital', 100.0)
                
                # 심볼 유효성 검사
                if not symbol or '-' not in symbol:
                    self.logger.warning(f"잘못된 심볼 설정: {symbol}")
                    continue
                
                # 자본금 검사
                if capital <= 0:
                    self.logger.warning(f"잘못된 자본금 설정: {capital}")
                    continue
                
                strategy_params = {
                    'profit_target': strategy_config.get('profit_target', 1.3),
                    'stop_loss': strategy_config.get('stop_loss', -2.0),
                    'rsi_oversold': strategy_config.get('rsi_oversold', 30),
                    'rsi_overbought': strategy_config.get('rsi_overbought', 70)
                }
                
                strategies_config.append({
                    'symbol': symbol,
                    'capital': capital,
                    'strategy_config': strategy_params
                })
                
                self.logger.info(f"전략 설정 로드: {symbol} (자본금: {capital} USDT)")
            
            if not strategies_config:
                # 기본 전략 추가 (설정이 없는 경우)
                self.logger.info("기본 전략 설정 적용")
                strategies_config = [
                    {
                        'symbol': 'BTC-USDT',
                        'capital': 100.0,
                        'strategy_config': {
                            'profit_target': 1.3,
                            'stop_loss': -2.0
                        }
                    }
                ]
            
            self.session_stats['strategies_count'] = len(strategies_config)
            self.logger.info(f"총 {len(strategies_config)}개 전략 초기화 완료")
            
            return strategies_config
            
        except Exception as e:
            self.logger.error(f"전략 초기화 실패: {e}")
            raise
    
    async def setup_callbacks(self):
        """이벤트 콜백 설정"""
        
        async def on_trade_executed(result: TradingResult):
            """거래 실행 콜백"""
            try:
                self.session_stats['total_trades'] += 1
                
                if result.action == 'sell' and result.profit_rate:
                    if result.profit_rate > 0:
                        self.session_stats['profitable_trades'] += 1
                        profit_amount = (result.profit_rate / 100) * (result.price * result.quantity)
                        self.session_stats['total_profit'] += profit_amount
                    
                    # 드로우다운 계산
                    if result.profit_rate < 0:
                        if abs(result.profit_rate) > self.session_stats['max_drawdown']:
                            self.session_stats['max_drawdown'] = abs(result.profit_rate)
                
                # 거래 로그
                if result.action == 'buy':
                    self.logger.info(f"🟢 매수: {result.symbol} {result.quantity:.6f} @ {result.price:.6f} ({result.reason})")
                elif result.action == 'sell':
                    profit_emoji = "🟢" if (result.profit_rate or 0) > 0 else "🔴"
                    self.logger.info(f"{profit_emoji} 매도: {result.symbol} {result.quantity:.6f} @ {result.price:.6f} "
                                   f"수익률: {result.profit_rate:.2f}% ({result.reason})")
                
                # 중요한 거래는 알림 발송
                if result.action == 'sell' and abs(result.profit_rate or 0) > 1.0:
                    await self.notification_manager.send_trade_alert(result)
                
            except Exception as e:
                self.logger.error(f"거래 콜백 처리 오류: {e}")
        
        async def on_error(error_msg: str):
            """오류 발생 콜백"""
            self.logger.error(f"❌ 엔진 오류: {error_msg}")
            await self.notification_manager.send_error_alert(error_msg)
        
        async def on_status_update(status: Dict):
            """상태 업데이트 콜백"""
            try:
                # 핵심 지표 로그 (5분마다)
                if status.get('total_trades', 0) % 10 == 0 and status.get('total_trades', 0) > 0:
                    self.logger.info(f"📊 현재 상태: 거래 {status['total_trades']}회, "
                                   f"승률 {status['win_rate']}%, "
                                   f"수익 {status['total_profit']:.2f} USDT, "
                                   f"활성 포지션 {status['active_positions']}개")
                
                # 성과가 좋으면 알림
                if status.get('win_rate', 0) > 80 and status.get('total_trades', 0) >= 10:
                    await self.notification_manager.send_performance_alert(status)
                    
            except Exception as e:
                self.logger.error(f"상태 업데이트 콜백 오류: {e}")
        
        # 콜백 등록
        self.engine_controller.engine.on_trade_executed = on_trade_executed
        self.engine_controller.engine.on_error = on_error
        self.engine_controller.engine.on_status_update = on_status_update
        
        self.logger.info("이벤트 콜백 설정 완료")
    
    async def print_startup_banner(self):
        """시작 배너 출력"""
        banner = """
╔══════════════════════════════════════════════════════════╗
║                    🚀 오토블리츠 v1.0                      ║
║                 암호화폐 자동매매 시스템                    ║
║                                                          ║
║  ✅ OKX 거래소 완전 연동                                   ║
║  ✅ 단타로 전략 (RSI + MACD + 볼린저밴드)                  ║
║  ✅ 실시간 거래 엔진                                       ║
║  ✅ 1.3% 목표수익률 / -2% 손절선                          ║
║                                                          ║
║  🎯 목표: 안전하고 꾸준한 수익 창출                        ║
╚══════════════════════════════════════════════════════════╝
        """
        print(banner)
        
        # 현재 설정 정보
        print(f"📅 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 거래소: OKX ({'테스트넷' if self.config.get('sandbox', True) else '실거래'})")
        print(f"📊 전략 수: {self.session_stats['strategies_count']}개")
        print(f"⏰ 최소 신호 간격: {self.config.get('min_signal_interval', 60)}초")
        print(f"🎯 일일 최대 거래: {self.config.get('max_daily_trades', 100)}회")
        print("=" * 60)
    
    async def run(self):
        """메인 실행 함수"""
        try:
            self.start_time = datetime.now()
            
            # 시작 배너 출력
            await self.print_startup_banner()
            
            # 전략 초기화
            strategies_config = await self.initialize_strategies()
            
            # 콜백 설정
            await self.setup_callbacks()
            
            # 알림 시스템 초기화
            await self.notification_manager.send_startup_notification()
            
            # 엔진 시작
            self.logger.info("🚀 거래 엔진 시작 중...")
            await self.engine_controller.run_with_strategies(strategies_config)
            
        except KeyboardInterrupt:
            self.logger.info("👋 사용자에 의한 종료")
        except Exception as e:
            self.logger.error(f"💥 치명적 오류: {e}")
            await self.notification_manager.send_error_alert(f"시스템 치명적 오류: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """정리 작업"""
        try:
            # 세션 통계 출력
            await self.print_session_summary()
            
            # 종료 알림
            await self.notification_manager.send_shutdown_notification(self.session_stats)
            
            self.logger.info("🏁 오토블리츠 봇 종료 완료")
            
        except Exception as e:
            self.logger.error(f"정리 작업 오류: {e}")
    
    async def print_session_summary(self):
        """세션 요약 출력"""
        if not self.start_time:
            return
        
        runtime = datetime.now() - self.start_time
        runtime_hours = runtime.total_seconds() / 3600
        
        print("\n" + "=" * 60)
        print("📊 세션 요약")
        print("=" * 60)
        print(f"⏰ 실행 시간: {runtime_hours:.1f}시간")
        print(f"📈 총 거래 수: {self.session_stats['total_trades']}회")
        print(f"✅ 수익 거래: {self.session_stats['profitable_trades']}회")
        
        if self.session_stats['total_trades'] > 0:
            win_rate = (self.session_stats['profitable_trades'] / self.session_stats['total_trades']) * 100
            print(f"🎯 승률: {win_rate:.1f}%")
        
        print(f"💰 총 수익: {self.session_stats['total_profit']:.2f} USDT")
        print(f"📉 최대 드로우다운: {self.session_stats['max_drawdown']:.2f}%")
        
        if runtime_hours > 0:
            hourly_profit = self.session_stats['total_profit'] / runtime_hours
            print(f"⚡ 시간당 수익: {hourly_profit:.2f} USDT/h")
        
        print("=" * 60)


# 유틸리티 모듈들
class ConfigLoader:
    """설정 로더 클래스"""
    
    @staticmethod
    def load_config(config_path: str = '.env') -> Dict:
        """환경 설정 로드"""
        config = {}
        
        # .env 파일에서 로드
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        config[key] = value
        
        # 환경 변수에서 로드 (우선순위 높음)
        config.update({
            'okx_api_key': os.getenv('OKX_API_KEY', config.get('OKX_API_KEY')),
            'okx_secret_key': os.getenv('OKX_SECRET_KEY', config.get('OKX_SECRET_KEY')),
            'okx_passphrase': os.getenv('OKX_PASSPHRASE', config.get('OKX_PASSPHRASE')),
            'sandbox': os.getenv('SANDBOX', config.get('SANDBOX', 'true')).lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', config.get('LOG_LEVEL', 'INFO')),
            'max_daily_trades': int(os.getenv('MAX_DAILY_TRADES', config.get('MAX_DAILY_TRADES', '100'))),
            'min_signal_interval': int(os.getenv('MIN_SIGNAL_INTERVAL', config.get('MIN_SIGNAL_INTERVAL', '60'))),
            'notification_webhook': os.getenv('NOTIFICATION_WEBHOOK', config.get('NOTIFICATION_WEBHOOK'))
        })
        
        # 기본 전략 설정
        if 'default_strategies' not in config:
            config['default_strategies'] = [
                {
                    'symbol': 'BTC-USDT',
                    'capital': 100.0,
                    'profit_target': 1.3,
                    'stop_loss': -2.0
                },
                {
                    'symbol': 'ETH-USDT',
                    'capital': 50.0,
                    'profit_target': 1.5,
                    'stop_loss': -2.0
                }
            ]
        
        return config
    
    @staticmethod
    def validate_config(config: Dict):
        """설정 유효성 검사"""
        required_keys = ['okx_api_key', 'okx_secret_key', 'okx_passphrase']
        
        for key in required_keys:
            if not config.get(key):
                raise ValueError(f"필수 설정 누락: {key}")
        
        if config.get('max_daily_trades', 0) <= 0:
            raise ValueError("max_daily_trades는 0보다 커야 합니다")
        
        if config.get('min_signal_interval', 0) < 10:
            raise ValueError("min_signal_interval은 10초 이상이어야 합니다")


class SimpleNotificationManager:
    """간단한 알림 매니저"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.webhook_url = config.get('notification_webhook')
        self.logger = logging.getLogger('NotificationManager')
    
    async def send_trade_alert(self, result: TradingResult):
        """거래 알림 발송"""
        if not self.webhook_url:
            return
        
        try:
            message = f"거래 알림: {result.symbol} {result.action} @ {result.price:.6f}"
            if result.profit_rate:
                message += f" (수익률: {result.profit_rate:.2f}%)"
            
            await self._send_webhook(message)
        except Exception as e:
            self.logger.error(f"거래 알림 발송 실패: {e}")
    
    async def send_error_alert(self, error_msg: str):
        """오류 알림 발송"""
        if not self.webhook_url:
            return
        
        try:
            message = f"🚨 오토블리츠 오류: {error_msg}"
            await self._send_webhook(message)
        except Exception as e:
            self.logger.error(f"오류 알림 발송 실패: {e}")
    
    async def send_startup_notification(self):
        """시작 알림"""
        if not self.webhook_url:
            return
        
        try:
            message = "🚀 오토블리츠 봇이 시작되었습니다!"
            await self._send_webhook(message)
        except Exception as e:
            self.logger.error(f"시작 알림 발송 실패: {e}")
    
    async def send_shutdown_notification(self, stats: Dict):
        """종료 알림"""
        if not self.webhook_url:
            return
        
        try:
            message = f"🏁 오토블리츠 봇 종료\n총 거래: {stats['total_trades']}회\n총 수익: {stats['total_profit']:.2f} USDT"
            await self._send_webhook(message)
        except Exception as e:
            self.logger.error(f"종료 알림 발송 실패: {e}")
    
    async def send_performance_alert(self, status: Dict):
        """성과 알림"""
        if not self.webhook_url:
            return
        
        try:
            message = f"📊 성과 알림: 승률 {status['win_rate']}%, 수익 {status['total_profit']:.2f} USDT"
            await self._send_webhook(message)
        except Exception as e:
            self.logger.error(f"성과 알림 발송 실패: {e}")
    
    async def _send_webhook(self, message: str):
        """웹훅 메시지 발송"""
        if not self.webhook_url:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"text": message}
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.debug("웹훅 알림 발송 성공")
                    else:
                        self.logger.warning(f"웹훅 발송 실패: {response.status}")
        except Exception as e:
            self.logger.error(f"웹훅 발송 오류: {e}")


def setup_simple_logger(name: str, level: str = 'INFO') -> logging.Logger:
    """간단한 로거 설정"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    if not logger.handlers:
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # 파일 핸들러
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_dir / f'autoblitz_{datetime.now().strftime("%Y%m%d")}.log'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


# 임시 유틸리티 함수들 (실제 구현에서는 별도 모듈로 분리)
def load_config(config_path: str = '.env') -> Dict:
    return ConfigLoader.load_config(config_path)

def validate_config(config: Dict):
    return ConfigLoader.validate_config(config)

def setup_logger(name: str, level: str = 'INFO') -> logging.Logger:
    return setup_simple_logger(name, level)

class NotificationManager(SimpleNotificationManager):
    pass


# CLI 인터페이스
def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(description='오토블리츠 암호화폐 자동매매 봇')
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='.env',
        help='설정 파일 경로 (기본값: .env)'
    )
    
    parser.add_argument(
        '--sandbox',
        action='store_true',
        help='테스트넷 모드로 실행'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 거래 없이 시뮬레이션만 실행'
    )
    
    parser.add_argument(
        '--strategies',
        type=str,
        help='사용할 전략 목록 (JSON 형식)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='로그 레벨 설정'
    )
    
    return parser.parse_args()


# 메인 실행 함수
async def main():
    """메인 실행 함수"""
    try:
        # 명령행 인수 파싱
        args = parse_arguments()
        
        # 기본 로거 설정
        setup_simple_logger('AutoBlitz', args.log_level)
        logger = logging.getLogger('AutoBlitz')
        
        logger.info("🚀 오토블리츠 봇 시작")
        
        # 설정 로드
        config = load_config(args.config)
        
        # 명령행 옵션 반영
        if args.sandbox:
            config['sandbox'] = True
        if args.dry_run:
            config['dry_run'] = True
        if args.log_level:
            config['log_level'] = args.log_level
        
        # 사용자 정의 전략
        if args.strategies:
            try:
                custom_strategies = json.loads(args.strategies)
                config['default_strategies'] = custom_strategies
                logger.info(f"사용자 정의 전략 {len(custom_strategies)}개 로드")
            except json.JSONDecodeError:
                logger.error("잘못된 전략 JSON 형식")
                return
        
        # 봇 생성 및 실행
        bot = AutoBlitzBot()
        bot.config.update(config)
        
        await bot.run()
        
    except KeyboardInterrupt:
        print("\n👋 안전하게 종료됩니다...")
    except Exception as e:
        print(f"💥 오류 발생: {e}")
        logging.getLogger('AutoBlitz').error(f"메인 실행 오류: {e}")
        sys.exit(1)


# 빠른 시작 함수
async def quick_start():
    """빠른 시작 (기본 설정)"""
    print("🚀 오토블리츠 빠른 시작")
    print("기본 설정으로 테스트넷에서 BTC-USDT 거래를 시작합니다.")
    print()
    
    # 기본 설정 생성
    config = {
        'okx_api_key': 'demo_api_key',
        'okx_secret_key': 'demo_secret_key',
        'okx_passphrase': 'demo_passphrase',
        'sandbox': True,
        'log_level': 'INFO',
        'max_daily_trades': 20,
        'min_signal_interval': 30,
        'default_strategies': [
            {
                'symbol': 'BTC-USDT',
                'capital': 100.0,
                'profit_target': 1.3,
                'stop_loss': -2.0
            }
        ]
    }
    
    # 봇 실행
    bot = AutoBlitzBot()
    bot.config = config
    await bot.run()


if __name__ == "__main__":
    # 실제 실행 시
    asyncio.run(main())
    
    # 빠른 테스트 실행 시 (주석 해제)
    # asyncio.run(quick_start())