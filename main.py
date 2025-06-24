from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
from binance import AsyncClient, BinanceSocketManager
from contextlib import asynccontextmanager
from typing import Dict, List
import os

app = FastAPI()
live_data: Dict[str, dict] = {}  # {timeframe: latest_candle}
historical_data: Dict[str, List[dict]] = {}  # {timeframe: [candles]}

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = await AsyncClient.create()
    bm = BinanceSocketManager(client)
    
    async def handle_socket(msg):
        candle = msg['k']
        tf = candle['i']
        candle_data = {
            "open": float(candle['o']),
            "close": float(candle['c']),
            "volume": float(candle['v']),
            "is_final": candle['x'],
            "timestamp": datetime.utcfromtimestamp(candle['t']/1000)
        }
        
        live_data[tf] = candle_data
        
        if candle['x']:  # Finalized candle
            if tf not in historical_data:
                historical_data[tf] = []
            historical_data[tf].append(candle_data)
            # Keep only today's data
            historical_data[tf] = [
                c for c in historical_data[tf] 
                if c['timestamp'].date() == datetime.utcnow().date()
            ]
    
    # Start WebSockets for all timeframes
    timeframes = ['1m', '5m', '15m']
    sockets = []
    for tf in timeframes:
        ts = bm.kline_socket('SOLUSDT', interval=tf)
        await ts.__aenter__()
        ts._on_message = handle_socket
        sockets.append(ts)
    
    # Load today's historical data
    for tf in timeframes:
        historical_data[tf] = await get_historical_data(client, tf)
    
    yield
    
    # Cleanup
    for ts in sockets:
        await ts.__aexit__(None, None, None)
    await client.close_connection()

async def get_historical_data(client, timeframe: str) -> List[dict]:
    """Fetch today's historical candles"""
    now = datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    candles = await client.get_klines(
        symbol='SOLUSDT',
        interval=timeframe,
        startTime=int(start_of_day.timestamp() * 1000),
        limit=1000
    )
    return [{
        "open": float(c[1]),
        "close": float(c[4]),
        "volume": float(c[5]),
        "is_final": True,
        "timestamp": datetime.utcfromtimestamp(c[0]/1000)
    } for c in candles]

def get_color(candle: dict) -> str:
    """Determine color based on volume and price"""
    if candle['close'] > candle['open']:
        return 'green'
    elif candle['close'] < candle['open']:
        return 'red'
    return 'gray'

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SOLUSDT Volume Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; }
            .controls { display: flex; justify-content: center; margin: 20px 0; gap: 10px; }
            select, button { padding: 8px 15px; font-size: 16px; border-radius: 5px; border: 1px solid #ddd; }
            .chart-container { position: relative; height: 400px; margin: 20px 0; }
            canvas { background: #111; border-radius: 8px; }
            .table-container { margin-top: 30px; overflow-x: auto; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f2f2f2; }
            .green { color: #2ecc71; }
            .red { color: #e74c3c; }
            .gray { color: #95a5a6; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>SOLUSDT Volume Dashboard</h1>
            
            <div class="controls">
                <select id="timeframe">
                    <option value="1m">1 Minute</option>
                    <option value="5m" selected>5 Minutes</option>
                    <option value="15m">15 Minutes</option>
                </select>
                <button onclick="loadData()">Refresh</button>
            </div>
            
            <div class="chart-container">
                <canvas id="volumeChart"></canvas>
            </div>
            
            <div class="table-container">
                <h2>Historical Data</h2>
                <table id="historyTable">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Volume</th>
                            <th>Open</th>
                            <th>Close</th>
                            <th>Signal</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>

        <script>
            const ctx = document.getElementById('volumeChart').getContext('2d');
            let chart = new Chart(ctx, {
                type: 'bar',
                data: { labels: [], datasets: [] },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, title: { display: true, text: 'Volume' } },
                        x: { title: { display: true, text: 'Time' } }
                    }
                }
            });

            async function loadData() {
                const tf = document.getElementById('timeframe').value;
                const response = await axios.get(`/api/history?timeframe=${tf}`);
                const data = response.data;
                
                // Update Chart
                const labels = data.candles.map(c => 
                    new Date(c.timestamp).toLocaleTimeString()
                );
                const volumes = data.candles.map(c => c.volume);
                const colors = data.candles.map(c => 
                    c.close > c.open ? '#2ecc71' : c.close < c.open ? '#e74c3c' : '#95a5a6'
                );
                
                chart.data = {
                    labels: labels,
                    datasets: [{
                        label: `Volume (${tf})`,
                        data: volumes,
                        backgroundColor: colors,
                        borderColor: colors,
                        borderWidth: 1
                    }]
                };
                chart.update();
                
                // Update Table
                const tableBody = document.querySelector('#historyTable tbody');
                tableBody.innerHTML = data.candles.slice().reverse().map(c => `
                    <tr>
                        <td>${new Date(c.timestamp).toLocaleTimeString()}</td>
                        <td>${c.volume.toLocaleString()}</td>
                        <td>${c.open.toFixed(2)}</td>
                        <td>${c.close.toFixed(2)}</td>
                        <td class="${c.close > c.open ? 'green' : c.close < c.open ? 'red' : 'gray'}">
                            ${c.close > c.open ? 'Bullish' : c.close < c.open ? 'Bearish' : 'Neutral'}
                        </td>
                    </tr>
                `).join('');
            }
            
            // Initial load
            loadData();
        </script>
    </body>
    </html>
    """

@app.get("/api/history")
async def api_history(timeframe: str = Query('5m', enum=['1m', '5m', '15m'])):
    return {
        "timeframe": timeframe,
        "candles": historical_data.get(timeframe, [])
    }

@app.get("/")
async def redirect_to_dashboard():
    return HTMLResponse("""
        <script>window.location.href = '/dashboard';</script>
    """)