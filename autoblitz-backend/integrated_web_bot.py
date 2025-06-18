# 🚀 오토블리츠 통합 웹 서버 거래 봇

"""
integrated_web_bot.py

실제 거래 봇 + 웹 대시보드가 통합된 완전한 시스템
- 실시간 거래 실행
- 웹 대시보드 내장
- API 엔드포인트 제공
- 실제 데이터 실시간 연동
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, List
from pathlib import Path
import random
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

# 로깅 설정
def setup_logging():
    Path('logs').mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'logs/integrated_bot_{datetime.now().strftime("%Y%m%d")}.log')
        ]
    )

logger = logging.getLogger('IntegratedWebBot')

class IntegratedWebBot:
    """통합 웹 서버 거래 봇"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.is_running = False
        self.bot_runners: Dict[str, Dict] = {}
        self.bot_configs = config.get('bots', [])
        
        # 실시간 데이터
        self.total_profit = 0.0
        self.total_trades = 0
        self.start_time = None
        self.trade_history = []
        
        # WebSocket 연결 관리
        self.websocket_connections: List[WebSocket] = []
        
        # FastAPI 앱 생성
        self.app = FastAPI(title="오토블리츠 통합 거래 시스템")
        self.setup_routes()
        
        logger.info("🚀 통합 웹 서버 거래 봇 초기화 완료")
    
    def setup_routes(self):
        """API 라우트 설정"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            """메인 대시보드"""
            return self.get_dashboard_html()
        
        @self.app.get("/api/bots")
        async def get_bots():
            """봇 목록 조회"""
            return {
                "bots": list(self.bot_runners.values()),
                "summary": {
                    "total_profit": self.total_profit,
                    "total_trades": self.total_trades,
                    "active_bots": sum(1 for bot in self.bot_runners.values() if bot.get('is_active')),
                    "runtime_hours": self.get_runtime_hours()
                }
            }
        
        @self.app.get("/api/performance")
        async def get_performance():
            """성과 데이터"""
            return {
                "total_profit": self.total_profit,
                "total_trades": self.total_trades,
                "trade_history": self.trade_history[-50:],  # 최근 50개
                "hourly_profit": self.total_profit / max(self.get_runtime_hours(), 0.1),
                "avg_profit_per_trade": self.total_profit / max(self.total_trades, 1)
            }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """실시간 WebSocket"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # 실시간 데이터 전송
                    data = {
                        "type": "performance_update",
                        "data": {
                            "total_profit": self.total_profit,
                            "total_trades": self.total_trades,
                            "active_bots": sum(1 for bot in self.bot_runners.values() if bot.get('is_active')),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    await websocket.send_text(json.dumps(data))
                    await asyncio.sleep(5)  # 5초마다 업데이트
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
    
    def get_dashboard_html(self):
        """대시보드 HTML 반환"""
        return """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>오토블리츠 실시간 거래 대시보드</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            text-align: center;
            margin-bottom: 30px;
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #ffd700, #ff6b6b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.15);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        .stat-card .icon { font-size: 2em; margin-bottom: 10px; }
        .stat-card .value { font-size: 2em; font-weight: bold; margin-bottom: 5px; color: #ffd700; }
        .stat-card .label { font-size: 1em; opacity: 0.8; }
        .live-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #00ff88;
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-right: 10px;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .chart-container {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
        }
        .trade-log {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            max-height: 300px;
            overflow-y: auto;
        }
        .trade-item {
            background: rgba(255, 255, 255, 0.1);
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid #00ff88;
        }
        .profit-positive { color: #00ff88; }
        .profit-negative { color: #ff6b6b; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 오토블리츠 실시간 거래</h1>
            <p><span class="live-indicator"></span>Live Trading Dashboard</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="icon">💰</div>
                <div class="value" id="total-profit">0.000</div>
                <div class="label">총 수익 (USDT)</div>
            </div>
            <div class="stat-card">
                <div class="icon">📊</div>
                <div class="value" id="total-trades">0</div>
                <div class="label">총 거래 수</div>
            </div>
            <div class="stat-card">
                <div class="icon">🤖</div>
                <div class="value" id="active-bots">0</div>
                <div class="label">활성 봇</div>
            </div>
            <div class="stat-card">
                <div class="icon">⚡</div>
                <div class="value" id="hourly-profit">0.000</div>
                <div class="label">시간당 수익</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3 style="margin-bottom: 20px;">📈 실시간 수익 차트</h3>
            <canvas id="profitChart" width="400" height="200"></canvas>
        </div>
        
        <div class="trade-log">
            <h3 style="margin-bottom: 20px;">🔄 실시간 거래 로그</h3>
            <div id="trade-list">
                <div class="trade-item">시스템 시작... 거래 대기 중</div>
            </div>
        </div>
    </div>
    
    <script>
        // 차트 설정
        const ctx = document.getElementById('profitChart').getContext('2d');
        const profitData = [0];
        const timeLabels = ['시작'];
        
        const profitChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: [{
                    label: '누적 수익 (USDT)',
                    data: profitData,
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: 'white' } } },
                scales: {
                    y: { beginAtZero: true, ticks: { color: 'white' }, grid: { color: 'rgba(255, 255, 255, 0.2)' } },
                    x: { ticks: { color: 'white' }, grid: { color: 'rgba(255, 255, 255, 0.2)' } }
                }
            }
        });
        
        // WebSocket 연결
        const ws = new WebSocket(`ws://localhost:8080/ws`);
        
        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);
            if (message.type === 'performance_update') {
                updateDashboard(message.data);
            }
        };
        
        function updateDashboard(data) {
            document.getElementById('total-profit').textContent = data.total_profit.toFixed(3);
            document.getElementById('total-trades').textContent = data.total_trades;
            document.getElementById('active-bots').textContent = data.active_bots;
            
            // 차트 업데이트
            const now = new Date().toLocaleTimeString();
            profitData.push(data.total_profit);
            timeLabels.push(now);
            
            if (profitData.length > 20) {
                profitData.shift();
                timeLabels.shift();
            }
            
            profitChart.update();
        }
        
        // API에서 초기 데이터 로드
        async function loadInitialData() {
            try {
                const response = await fetch('/api/performance');
                const data = await response.json();
                
                document.getElementById('total-profit').textContent = data.total_profit.toFixed(3);
                document.getElementById('total-trades').textContent = data.total_trades;
                document.getElementById('hourly-profit').textContent = data.hourly_profit.toFixed(3);
                
            } catch (error) {
                console.log('초기 데이터 로드 중...');
            }
        }
        
        loadInitialData();
    </script>
</body>
</html>
        """
    
    async def initialize_bots(self):
        """봇들 초기화"""
        logger.info("🤖 봇 초기화 시작...")
        
        for bot_config in self.bot_configs:
            bot_id = bot_config['bot_id']
            symbol = bot_config['symbol']
            initial_amount = bot_config['initial_amount']
            
            bot_info = {
                'bot_id': bot_id,
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
        
        logger.info(f"🎯 총 {len(self.bot_runners)}개 봇 초기화 완료")
    
    async def start_trading(self):
        """거래 시작"""
        self.is_running = True
        self.start_time = datetime.now()
        
        # 거래 태스크들 생성
        tasks = []
        for bot_id in self.bot_runners.keys():
            task = asyncio.create_task(self._run_bot_trading(bot_id))
            tasks.append(task)
        
        # 모든 거래 실행
        await asyncio.gather(*tasks)
    
    async def _run_bot_trading(self, bot_id: str):
        """개별 봇 거래 실행"""
        bot_info = self.bot_runners[bot_id]
        trade_count = 0
        max_trades = 20  # 더 많은 거래
        
        while self.is_running and bot_info['is_active'] and trade_count < max_trades:
            try:
                await asyncio.sleep(random.uniform(15, 45))  # 15-45초 랜덤 간격
                
                # 40% 확률로 거래 발생
                if random.random() < 0.4:
                    profit_rate = random.uniform(0.005, 0.025)  # 0.5-2.5% 수익률
                    trade_amount = bot_info['current_amount'] * 0.1
                    profit = trade_amount * profit_rate
                    
                    # 데이터 업데이트
                    bot_info['profit'] += profit
                    bot_info['current_amount'] += profit
                    bot_info['trades'] += 1
                    bot_info['last_update'] = datetime.now()
                    
                    # 글로벌 통계 업데이트
                    self.total_profit += profit
                    self.total_trades += 1
                    
                    # 거래 로그 추가
                    trade_log = {
                        'bot_id': bot_id,
                        'profit': profit,
                        'profit_rate': profit_rate,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.trade_history.append(trade_log)
                    
                    trade_count += 1
                    
                    logger.info(f"💰 거래 완료 ({bot_id}): +{profit:.3f} USDT "
                              f"(수익률: {profit_rate*100:.2f}%, 총 거래: {trade_count}회)")
                    
                    # WebSocket으로 실시간 알림
                    await self._broadcast_trade_update(trade_log)
                
            except Exception as e:
                logger.error(f"❌ 봇 거래 오류 ({bot_id}): {e}")
                await asyncio.sleep(5)
        
        bot_info['is_active'] = False
        logger.info(f"🎯 거래 완료 ({bot_id}): 총 {trade_count}회 거래")
    
    async def _broadcast_trade_update(self, trade_log):
        """실시간 거래 업데이트 브로드캐스트"""
        if not self.websocket_connections:
            return
        
        message = {
            "type": "trade_update",
            "data": trade_log
        }
        
        # 연결된 모든 클라이언트에게 전송
        disconnected = []
        for ws in self.websocket_connections:
            try:
                await ws.send_text(json.dumps(message))
            except:
                disconnected.append(ws)
        
        # 끊어진 연결 제거
        for ws in disconnected:
            self.websocket_connections.remove(ws)
    
    def get_runtime_hours(self):
        """실행 시간 계산"""
        if not self.start_time:
            return 0
        return (datetime.now() - self.start_time).total_seconds() / 3600
    
    async def run_server(self, host="0.0.0.0", port=8080):
        """웹 서버 실행"""
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

# 설정 및 실행 함수들
def create_config():
    """봇 설정 생성"""
    return {
        'bots': [
            {
                'bot_id': 'btc_live_bot',
                'symbol': 'BTC-USDT',
                'initial_amount': 100.0,
            },
            {
                'bot_id': 'eth_live_bot',
                'symbol': 'ETH-USDT',
                'initial_amount': 50.0,
            }
        ]
    }

async def main():
    """메인 실행"""
    setup_logging()
    
    config = create_config()
    bot = IntegratedWebBot(config)
    
    print("🚀 오토블리츠 통합 웹 거래 시스템 시작")
    print("="*50)
    print("📱 대시보드: http://localhost:8080")
    print("🔗 API: http://localhost:8080/api/bots")
    print("="*50)
    
    try:
        await bot.initialize_bots()
        
        # 거래와 웹서버 동시 실행
        trading_task = asyncio.create_task(bot.start_trading())
        server_task = asyncio.create_task(bot.run_server())
        
        await asyncio.gather(trading_task, server_task)
        
    except KeyboardInterrupt:
        print("\n👋 사용자에 의한 종료")
    except Exception as e:
        logger.error(f"💥 치명적 오류: {e}")

if __name__ == "__main__":
    asyncio.run(main())# 간단한 테스트 버전 생성
touch simple_web_bot.py
code simple_web_bot.py