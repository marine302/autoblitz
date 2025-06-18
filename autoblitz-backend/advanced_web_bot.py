# 🚀 고급 웹 거래 봇

"""
advanced_web_bot.py

간단한 버전에서 확장된 고급 기능
- 다중 봇 지원
- 실시간 차트
- 거래 히스토리
- 설정 변경
- 성과 분석
"""

import asyncio
import time
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn
import signal
import sys

class AdvancedWebBot:
    def __init__(self):
        self.app = FastAPI(title="오토블리츠 고급 거래 시스템")
        
        # 봇 상태
        self.bots = {
            'btc_bot': {
                'name': 'BTC 거래봇',
                'symbol': 'BTC-USDT',
                'is_running': False,
                'profit': 0.0,
                'trades': 0,
                'capital': 100.0,
                'last_trade': None
            },
            'eth_bot': {
                'name': 'ETH 거래봇', 
                'symbol': 'ETH-USDT',
                'is_running': False,
                'profit': 0.0,
                'trades': 0,
                'capital': 50.0,
                'last_trade': None
            }
        }
        
        # 전체 통계
        self.start_time = None
        self.trade_history = []
        self.profit_history = []
        
        # WebSocket 연결
        self.websocket_connections = []
        
        # 종료 신호 처리
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            return """
<!DOCTYPE html>
<html>
<head>
    <title>오토블리츠 고급 대시보드</title>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; margin: 0; padding: 20px; min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            text-align: center; margin-bottom: 30px;
            background: rgba(255, 255, 255, 0.1); padding: 20px;
            border-radius: 15px; backdrop-filter: blur(10px);
        }
        .header h1 {
            font-size: 2.5em; margin-bottom: 10px;
            background: linear-gradient(45deg, #ffd700, #ff6b6b);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card {
            background: rgba(255, 255, 255, 0.15); padding: 20px; margin: 20px 0;
            border-radius: 15px; backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat {
            text-align: center; padding: 20px; background: rgba(255, 255, 255, 0.1);
            border-radius: 10px; transition: transform 0.3s ease;
        }
        .stat:hover { transform: translateY(-5px); }
        .stat .value { font-size: 1.8em; color: #4CAF50; font-weight: bold; }
        .stat .label { font-size: 0.9em; opacity: 0.8; margin-top: 5px; }
        
        .bot-card {
            background: rgba(255, 255, 255, 0.1); padding: 15px; margin: 10px 0;
            border-radius: 10px; border-left: 4px solid #4CAF50;
        }
        .bot-header { display: flex; justify-content: space-between; align-items: center; }
        .bot-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0; }
        .bot-stat { text-align: center; padding: 10px; background: rgba(255, 255, 255, 0.1); border-radius: 5px; }
        
        button {
            background: linear-gradient(45deg, #4CAF50, #45a049); color: white;
            border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer;
            margin: 5px; font-weight: bold; transition: all 0.3s ease;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(76, 175, 80, 0.4); }
        .stop-btn { background: linear-gradient(45deg, #f44336, #da190b); }
        .stop-btn:hover { box-shadow: 0 5px 15px rgba(244, 67, 54, 0.4); }
        
        .status-running { color: #4CAF50; font-weight: bold; }
        .status-stopped { color: #f44336; font-weight: bold; }
        
        .trade-log {
            max-height: 200px; overflow-y: auto; background: rgba(0, 0, 0, 0.2);
            padding: 15px; border-radius: 8px; font-family: monospace; font-size: 0.9em;
        }
        .trade-item {
            padding: 5px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            display: flex; justify-content: space-between;
        }
        .profit-positive { color: #4CAF50; }
        .profit-negative { color: #f44336; }
        
        .live-indicator {
            display: inline-block; width: 10px; height: 10px; background: #4CAF50;
            border-radius: 50%; animation: pulse 2s infinite; margin-right: 10px;
        }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 오토블리츠 고급 대시보드</h1>
            <p><span class="live-indicator"></span>Advanced Trading System</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat">
                <div class="value" id="total-profit">0.00</div>
                <div class="label">총 수익 (USDT)</div>
            </div>
            <div class="stat">
                <div class="value" id="total-trades">0</div>
                <div class="label">총 거래</div>
            </div>
            <div class="stat">
                <div class="value" id="active-bots">0</div>
                <div class="label">활성 봇</div>
            </div>
            <div class="stat">
                <div class="value" id="hourly-profit">0.00</div>
                <div class="label">시간당 수익</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>📈 실시간 수익 차트</h3>
                <canvas id="profitChart" width="400" height="200"></canvas>
            </div>
            
            <div class="card">
                <h3>🔄 최근 거래 로그</h3>
                <div class="trade-log" id="trade-log">
                    <div class="trade-item">시스템 대기 중...</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>🤖 봇 관리</h3>
            <div class="grid" id="bot-list">
                <!-- 봇 카드들이 여기에 동적으로 추가됩니다 -->
            </div>
        </div>
        
        <div class="card">
            <h3>🎮 전체 제어</h3>
            <button onclick="startAllBots()">모든 봇 시작</button>
            <button onclick="stopAllBots()" class="stop-btn">모든 봇 중지</button>
            <button onclick="refreshData()">새로고침</button>
            <button onclick="exportData()">데이터 내보내기</button>
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
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
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
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
        
        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);
            if (message.type === 'update') {
                updateDashboard(message.data);
            }
        };
        
        ws.onerror = function(error) {
            console.log('WebSocket 연결 중...');
        };
        
        function updateDashboard(data) {
            // 전체 통계 업데이트
            document.getElementById('total-profit').textContent = data.total_profit.toFixed(2);
            document.getElementById('total-trades').textContent = data.total_trades;
            document.getElementById('active-bots').textContent = data.active_bots;
            document.getElementById('hourly-profit').textContent = data.hourly_profit.toFixed(2);
            
            // 차트 업데이트
            const now = new Date().toLocaleTimeString();
            profitData.push(data.total_profit);
            timeLabels.push(now);
            
            if (profitData.length > 20) {
                profitData.shift();
                timeLabels.shift();
            }
            profitChart.update();
            
            // 봇 목록 업데이트
            updateBotList(data.bots);
            
            // 거래 로그 업데이트
            if (data.recent_trades && data.recent_trades.length > 0) {
                updateTradeLog(data.recent_trades);
            }
        }
        
        function updateBotList(bots) {
            const botList = document.getElementById('bot-list');
            botList.innerHTML = '';
            
            for (const [botId, bot] of Object.entries(bots)) {
                const botCard = `
                    <div class="bot-card">
                        <div class="bot-header">
                            <h4>${bot.name}</h4>
                            <span class="${bot.is_running ? 'status-running' : 'status-stopped'}">
                                ${bot.is_running ? '실행 중' : '중지됨'}
                            </span>
                        </div>
                        <div class="bot-stats">
                            <div class="bot-stat">
                                <div class="profit-positive">+${bot.profit.toFixed(2)}</div>
                                <div>수익</div>
                            </div>
                            <div class="bot-stat">
                                <div>${bot.trades}</div>
                                <div>거래</div>
                            </div>
                            <div class="bot-stat">
                                <div>${bot.capital.toFixed(0)}</div>
                                <div>자본금</div>
                            </div>
                        </div>
                        <div>
                            <button onclick="toggleBot('${botId}')" ${bot.is_running ? 'class="stop-btn"' : ''}>
                                ${bot.is_running ? '중지' : '시작'}
                            </button>
                        </div>
                    </div>
                `;
                botList.innerHTML += botCard;
            }
        }
        
        function updateTradeLog(trades) {
            const tradeLog = document.getElementById('trade-log');
            tradeLog.innerHTML = '';
            
            trades.slice(-10).forEach(trade => {
                const tradeItem = `
                    <div class="trade-item">
                        <span>${trade.bot_id}: ${trade.symbol}</span>
                        <span class="profit-positive">+${trade.profit.toFixed(3)} USDT</span>
                    </div>
                `;
                tradeLog.innerHTML += tradeItem;
            });
        }
        
        // 제어 함수들
        function toggleBot(botId) {
            fetch(`/api/bot/${botId}/toggle`, {method: 'POST'})
                .then(response => response.json())
                .then(data => console.log(data.message));
        }
        
        function startAllBots() {
            fetch('/api/bots/start-all', {method: 'POST'})
                .then(response => response.json())
                .then(data => alert(data.message));
        }
        
        function stopAllBots() {
            fetch('/api/bots/stop-all', {method: 'POST'})
                .then(response => response.json())
                .then(data => alert(data.message));
        }
        
        function refreshData() {
            location.reload();
        }
        
        function exportData() {
            fetch('/api/export')
                .then(response => response.blob())
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `autoblitz_data_${new Date().getTime()}.json`;
                    a.click();
                });
        }
        
        // 초기 데이터 로드
        fetch('/api/status')
            .then(response => response.json())
            .then(data => updateDashboard(data));
    </script>
</body>
</html>
            """
        
        @self.app.get("/api/status")
        async def get_status():
            total_profit = sum(bot['profit'] for bot in self.bots.values())
            total_trades = sum(bot['trades'] for bot in self.bots.values())
            active_bots = sum(1 for bot in self.bots.values() if bot['is_running'])
            
            runtime_hours = 0
            if self.start_time:
                runtime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
            
            hourly_profit = total_profit / max(runtime_hours, 0.1)
            
            return {
                "total_profit": total_profit,
                "total_trades": total_trades,
                "active_bots": active_bots,
                "hourly_profit": hourly_profit,
                "bots": self.bots,
                "recent_trades": self.trade_history[-10:]
            }
        
        @self.app.post("/api/bot/{bot_id}/toggle")
        async def toggle_bot(bot_id: str):
            if bot_id in self.bots:
                bot = self.bots[bot_id]
                if bot['is_running']:
                    bot['is_running'] = False
                    return {"message": f"{bot['name']} 중지됨"}
                else:
                    bot['is_running'] = True
                    if not self.start_time:
                        self.start_time = datetime.now()
                    asyncio.create_task(self.trading_loop(bot_id))
                    return {"message": f"{bot['name']} 시작됨"}
            return {"message": "봇을 찾을 수 없습니다"}
        
        @self.app.post("/api/bots/start-all")
        async def start_all_bots():
            count = 0
            for bot_id, bot in self.bots.items():
                if not bot['is_running']:
                    bot['is_running'] = True
                    if not self.start_time:
                        self.start_time = datetime.now()
                    asyncio.create_task(self.trading_loop(bot_id))
                    count += 1
            return {"message": f"{count}개 봇이 시작되었습니다"}
        
        @self.app.post("/api/bots/stop-all")
        async def stop_all_bots():
            count = 0
            for bot in self.bots.values():
                if bot['is_running']:
                    bot['is_running'] = False
                    count += 1
            return {"message": f"{count}개 봇이 중지되었습니다"}
        
        @self.app.get("/api/export")
        async def export_data():
            from fastapi.responses import Response
            
            # datetime 객체를 문자열로 변환
            safe_bots = {}
            for bot_id, bot in self.bots.items():
                safe_bot = bot.copy()
                if isinstance(safe_bot.get('last_trade'), str):
                    # 이미 문자열이면 그대로 유지
                    pass
                elif safe_bot.get('last_trade'):
                    # datetime 객체면 문자열로 변환
                    safe_bot['last_trade'] = safe_bot['last_trade'].isoformat()
                safe_bots[bot_id] = safe_bot
            
            export_data = {
                "bots": safe_bots,
                "trade_history": self.trade_history,
                "profit_history": self.profit_history,
                "export_time": datetime.now().isoformat()
            }
            
            return Response(
                content=json.dumps(export_data, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=autoblitz_data.json"}
            )
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    await asyncio.sleep(5)
                    status = await self.get_status_data()
                    await websocket.send_text(json.dumps({
                        "type": "update",
                        "data": status
                    }))
            except:
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
    
    async def get_status_data(self):
        """현재 상태 데이터 반환"""
        total_profit = sum(bot['profit'] for bot in self.bots.values())
        total_trades = sum(bot['trades'] for bot in self.bots.values())
        active_bots = sum(1 for bot in self.bots.values() if bot['is_running'])
        
        runtime_hours = 0
        if self.start_time:
            runtime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        
        hourly_profit = total_profit / max(runtime_hours, 0.1)
        
        return {
            "total_profit": total_profit,
            "total_trades": total_trades,
            "active_bots": active_bots,
            "hourly_profit": hourly_profit,
            "bots": self.bots,
            "recent_trades": self.trade_history[-10:]
        }
    
    async def trading_loop(self, bot_id: str):
        """개별 봇 거래 루프"""
        bot = self.bots[bot_id]
        trade_count = 0
        
        print(f"🤖 {bot['name']} 거래 시작!")
        
        while bot['is_running'] and trade_count < 15:  # 봇당 최대 15회 거래
            try:
                await asyncio.sleep(random.uniform(8, 20))  # 8-20초 랜덤
                
                # 60% 확률로 거래 발생
                if random.random() < 0.6:
                    # 수익률 계산 (0.5% ~ 2.5%)
                    profit_rate = random.uniform(0.005, 0.025)
                    trade_amount = bot['capital'] * 0.1  # 자본금의 10%
                    profit = trade_amount * profit_rate
                    
                    # 봇 데이터 업데이트
                    bot['profit'] += profit
                    bot['trades'] += 1
                    bot['last_trade'] = datetime.now().isoformat()  # ISO 문자열로 변환
                    
                    # 거래 히스토리 추가
                    trade_record = {
                        'bot_id': bot_id,
                        'symbol': bot['symbol'],
                        'profit': profit,
                        'profit_rate': profit_rate,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.trade_history.append(trade_record)
                    
                    trade_count += 1
                    
                    print(f"💰 {bot['name']} 거래: +{profit:.3f} USDT ({profit_rate*100:.1f}%)")
                    
                    # WebSocket으로 실시간 업데이트
                    await self.broadcast_update()
                
            except Exception as e:
                print(f"거래 오류 ({bot_id}): {e}")
                await asyncio.sleep(5)
        
        bot['is_running'] = False
        print(f"🏁 {bot['name']} 거래 완료 (총 {trade_count}회)")
    
    async def broadcast_update(self):
        """WebSocket으로 실시간 업데이트 브로드캐스트"""
        if not self.websocket_connections:
            return
        
        status = await self.get_status_data()
        message = json.dumps({
            "type": "update",
            "data": status
        })
        
        disconnected = []
        for ws in self.websocket_connections:
            try:
                await ws.send_text(message)
            except:
                disconnected.append(ws)
        
        # 끊어진 연결 제거
        for ws in disconnected:
            self.websocket_connections.remove(ws)
    
    def signal_handler(self, signum, frame):
        print("\n🛑 종료 신호 수신")
        for bot in self.bots.values():
            bot['is_running'] = False
        sys.exit(0)

# 실행 함수
async def main():
    bot = AdvancedWebBot()
    
    print("🚀 오토블리츠 고급 웹 거래 시스템 시작")
    print("="*50)
    print("📱 대시보드: http://localhost:8080")
    print("🔗 API: http://localhost:8080/api/status")
    print("🛑 종료: Ctrl+C")
    print("="*50)
    
    config = uvicorn.Config(bot.app, host="0.0.0.0", port=8080, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())