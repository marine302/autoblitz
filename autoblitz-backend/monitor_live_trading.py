# monitor_live_trading.py - 실시간 모니터링 대시보드
import asyncio
import time
import os
from datetime import datetime
from typing import Dict, List
import json

from app.exchanges.okx.live_client import OKXLiveClient
from app.safety.trading_safety import safety_manager

class LiveTradingMonitor:
    """실거래 실시간 모니터링"""
    
    def __init__(self):
        self.okx_client = None
        self.monitoring = False
        self.stats = {
            'start_time': None,
            'total_trades': 0,
            'total_pnl': 0.0,
            'current_positions': {},
            'account_balance': {},
            'price_history': []
        }
    
    async def initialize(self):
        """모니터링 시스템 초기화"""
        try:
            self.okx_client = OKXLiveClient()
            self.stats['start_time'] = datetime.now()
            print("✅ 모니터링 시스템 초기화 완료")
        except Exception as e:
            print(f"❌ 모니터링 초기화 실패: {e}")
            raise
    
    def print_header(self):
        """헤더 출력"""
        os.system('clear' if os.name == 'posix' else 'cls')  # 화면 지우기
        print("="*80)
        print("🚀 오토블리츠 실거래 모니터링 대시보드")
        print("="*80)
        print(f"시작 시간: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"실행 시간: {self.get_runtime()}")
        print("-"*80)
    
    def get_runtime(self) -> str:
        """실행 시간 계산"""
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            hours, remainder = divmod(runtime.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        return "00:00:00"
    
    async def update_account_info(self):
        """계좌 정보 업데이트"""
        try:
            # 잔고 조회
            balances = self.okx_client.get_account_balance()
            self.stats['account_balance'] = balances
            
            # 포지션 조회 (선물 거래시)
            # positions = self.okx_client.get_positions()
            # self.stats['current_positions'] = positions
            
        except Exception as e:
            print(f"❌ 계좌 정보 업데이트 실패: {e}")
    
    async def update_market_data(self):
        """시장 데이터 업데이트"""
        try:
            # BTC 시세 조회
            ticker = self.okx_client.get_ticker('BTC-USDT')
            
            # 가격 히스토리 저장 (최근 20개만)
            price_data = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'price': ticker['last_price'],
                'volume': ticker['volume_24h']
            }
            
            self.stats['price_history'].append(price_data)
            if len(self.stats['price_history']) > 20:
                self.stats['price_history'].pop(0)
            
        except Exception as e:
            print(f"❌ 시장 데이터 업데이트 실패: {e}")
    
    def print_account_summary(self):
        """계좌 요약 출력"""
        print("💰 계좌 현황")
        print("-"*40)
        
        balances = self.stats['account_balance']
        if balances:
            for currency, info in balances.items():
                available = info['available']
                total = info['total']
                print(f"  {currency}: ${available:.2f} (총 ${total:.2f})")
        else:
            print("  데이터 로딩 중...")
        
        print()
    
    def print_market_summary(self):
        """시장 현황 출력"""
        print("📊 시장 현황 (BTC-USDT)")
        print("-"*40)
        
        if self.stats['price_history']:
            latest = self.stats['price_history'][-1]
            print(f"  현재가: ${latest['price']:,.2f}")
            print(f"  시간: {latest['timestamp']}")
            
            # 간단한 가격 추이 (최근 5개)
            if len(self.stats['price_history']) >= 2:
                prev_price = self.stats['price_history'][-2]['price']
                current_price = latest['price']
                change = current_price - prev_price
                change_percent = (change / prev_price) * 100
                
                trend = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                print(f"  변동: {trend} ${change:+.2f} ({change_percent:+.3f}%)")
        else:
            print("  데이터 로딩 중...")
        
        print()
    
    def print_safety_status(self):
        """안전장치 상태 출력"""
        print("🛡️ 안전장치 상태")
        print("-"*40)
        
        try:
            safety_status = safety_manager.get_safety_status()
            
            # 긴급 정지 상태
            emergency = safety_status['emergency_stop']
            status_icon = "🚨" if emergency else "✅"
            status_text = "긴급 정지" if emergency else "정상"
            print(f"  상태: {status_icon} {status_text}")
            
            # 일일 통계
            daily_stats = safety_status['daily_stats']
            print(f"  일일 거래: {daily_stats.get('total_trades', 0)}회")
            print(f"  일일 P&L: ${daily_stats.get('total_profit_loss', 0):.2f}")
            print(f"  활성 봇: {daily_stats.get('active_bots', 0)}개")
            
            # 남은 용량
            remaining = safety_status['remaining_capacity']
            print(f"  손실 여유: ${remaining.get('daily_loss_remaining', 0):.2f}")
            print(f"  봇 여유: {remaining.get('bots_remaining', 0)}개")
            
        except Exception as e:
            print(f"  ❌ 안전장치 상태 조회 실패: {e}")
        
        print()
    
    def print_price_chart(self):
        """간단한 가격 차트 출력"""
        print("📈 가격 추이 (최근 10분)")
        print("-"*40)
        
        if len(self.stats['price_history']) >= 2:
            # 최근 10개 데이터만 표시
            recent_data = self.stats['price_history'][-10:]
            
            for data in recent_data:
                timestamp = data['timestamp']
                price = data['price']
                print(f"  {timestamp}: ${price:,.2f}")
        else:
            print("  데이터 수집 중...")
        
        print()
    
    def print_controls(self):
        """조작 가이드 출력"""
        print("🎮 조작 가이드")
        print("-"*40)
        print("  Ctrl+C: 모니터링 종료")
        print("  대시보드는 10초마다 자동 갱신됩니다")
        print("="*80)
    
    async def run_monitoring(self):
        """모니터링 실행"""
        self.monitoring = True
        
        try:
            while self.monitoring:
                # 헤더 출력
                self.print_header()
                
                # 데이터 업데이트
                await self.update_account_info()
                await self.update_market_data()
                
                # 대시보드 출력
                self.print_account_summary()
                self.print_market_summary()
                self.print_safety_status()
                self.print_price_chart()
                self.print_controls()
                
                # 10초 대기
                await asyncio.sleep(10)
                
        except KeyboardInterrupt:
            print("\n👋 모니터링 종료됨")
            self.monitoring = False
        except Exception as e:
            print(f"\n❌ 모니터링 오류: {e}")
    
    async def start(self):
        """모니터링 시작"""
        await self.initialize()
        await self.run_monitoring()

# 로그 파일 모니터링 함수
def tail_log_file():
    """로그 파일 실시간 출력"""
    log_file = 'live_trading.log'
    
    if not os.path.exists(log_file):
        print(f"로그 파일이 없습니다: {log_file}")
        return
    
    print(f"📝 실거래 로그 모니터링: {log_file}")
    print("-"*50)
    
    try:
        with open(log_file, 'r') as f:
            # 파일 끝으로 이동
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    print(line.strip())
                else:
                    time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n로그 모니터링 종료")

# 메인 실행 함수
async def main():
    """메인 함수"""
    print("모니터링 모드를 선택하세요:")
    print("1. 실시간 대시보드")
    print("2. 로그 파일 추적")
    
    choice = input("선택 (1/2): ")
    
    if choice == "1":
        monitor = LiveTradingMonitor()
        await monitor.start()
    elif choice == "2":
        tail_log_file()
    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    asyncio.run(main())