# 🚀 오토블리츠 실시간 성과 추적기

"""
performance_tracker.py

실행 중인 봇들의 성과를 실시간으로 추적하고 분석
- API를 통한 실시간 데이터 수집
- 성과 분석 및 리포팅
- 자동 알림 시스템
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import time

class PerformanceTracker:
    """실시간 성과 추적기"""
    
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.is_running = False
        self.performance_history = []
        
    async def start_monitoring(self):
        """모니터링 시작"""
        self.is_running = True
        print("🚀 실시간 성과 추적 시작")
        print("="*50)
        
        while self.is_running:
            try:
                await self._collect_data()
                await self._display_performance()
                await asyncio.sleep(30)  # 30초마다 업데이트
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ 모니터링 오류: {e}")
                await asyncio.sleep(5)
        
        print("🛑 성과 추적 종료")
    
    async def _collect_data(self):
        """API에서 데이터 수집"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/api/v1/bots/") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 성과 데이터 저장
                        timestamp = datetime.now()
                        performance_data = {
                            'timestamp': timestamp,
                            'data': data,
                            'summary': self._calculate_summary(data)
                        }
                        
                        self.performance_history.append(performance_data)
                        
                        # 최근 100개만 유지
                        if len(self.performance_history) > 100:
                            self.performance_history.pop(0)
                            
        except Exception as e:
            print(f"⚠️ API 연결 실패: {e}")
    
    def _calculate_summary(self, data):
        """성과 요약 계산"""
        try:
            if 'bots' in data:
                bots = data['bots']
                
                total_profit = sum(bot.get('total_profit', 0) for bot in bots)
                total_trades = sum(bot.get('total_trades', 0) for bot in bots)
                active_bots = sum(1 for bot in bots if bot.get('status') == 'running')
                
                return {
                    'total_profit': total_profit,
                    'total_trades': total_trades,
                    'active_bots': active_bots,
                    'total_bots': len(bots)
                }
        except Exception:
            pass
        
        return {
            'total_profit': 0,
            'total_trades': 0, 
            'active_bots': 0,
            'total_bots': 0
        }
    
    async def _display_performance(self):
        """성과 표시"""
        if not self.performance_history:
            print("📊 데이터 수집 중...")
            return
        
        latest = self.performance_history[-1]
        summary = latest['summary']
        timestamp = latest['timestamp']
        
        # 화면 클리어 (선택적)
        print("\n" + "="*60)
        print(f"📊 실시간 성과 현황 ({timestamp.strftime('%H:%M:%S')})")
        print("="*60)
        
        # 기본 통계
        print(f"🤖 활성 봇: {summary['active_bots']}/{summary['total_bots']}개")
        print(f"💰 총 수익: {summary['total_profit']:.3f} USDT")
        print(f"📈 총 거래: {summary['total_trades']}회")
        
        if summary['total_trades'] > 0:
            avg_profit = summary['total_profit'] / summary['total_trades']
            print(f"📊 거래당 평균: {avg_profit:.3f} USDT")
        
        # 추세 분석
        if len(self.performance_history) >= 2:
            self._show_trend()
        
        print("="*60)
    
    def _show_trend(self):
        """추세 분석 표시"""
        try:
            current = self.performance_history[-1]['summary']
            previous = self.performance_history[-2]['summary']
            
            profit_change = current['total_profit'] - previous['total_profit']
            trades_change = current['total_trades'] - previous['total_trades']
            
            if profit_change > 0:
                print(f"📈 수익 증가: +{profit_change:.3f} USDT")
            elif profit_change < 0:
                print(f"📉 수익 감소: {profit_change:.3f} USDT")
            
            if trades_change > 0:
                print(f"🔄 신규 거래: +{trades_change}회")
                
        except Exception as e:
            print(f"추세 분석 오류: {e}")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_running = False

# 실행 함수
async def main():
    """메인 실행"""
    tracker = PerformanceTracker()
    
    try:
        await tracker.start_monitoring()
    except KeyboardInterrupt:
        print("\n👋 사용자에 의한 종료")
    finally:
        tracker.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())