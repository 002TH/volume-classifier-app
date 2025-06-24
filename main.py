from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import requests
import os

app = FastAPI()

BINANCE_API = "https://api.binance.com/api/v3"
TIMEFRAMES = ["1m", "2m", "3m", "5m", "15m"]

def get_sol_data(timeframe):
    response = requests.get(f"{BINANCE_API}/klines?symbol=SOLUSDT&interval={timeframe}&limit=2")
    data = response.json()
    return {
        "timeframe": timeframe,
        "current_volume": float(data[-1][5]),
        "prev_volume": float(data[-2][5]),
        "open": float(data[-1][1]),
        "close": float(data[-1][4]),
        "timestamp": datetime.fromtimestamp(data[-1][0]/1000).strftime('%H:%M:%S')
    }

def get_color(data):
    if data["current_volume"] <= data["prev_volume"]:
        return "gray"
    elif data["close"] > data["open"]:
        return "darkgreen"
    elif data["close"] < data["open"]:
        return "darkred"
    return "green"

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SOL Multi-Timeframe Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
        <style>
            body { font-family: Arial; padding: 20px; max-width: 1200px; margin: 0 auto; }
            .chart-container { display: flex; flex-wrap: wrap; gap: 20px; }
            .chart-box { width: 45%; min-width: 400px; height: 300px; }
            .controls { margin: 20px 0; text-align: center; }
            select { padding: 8px; font-size: 16px; }
            .timestamp { font-size: 12px; color: #666; text-align: right; }
        </style>
    </head>
    <body>
        <h1 style="text-align: center;">SOL/USDT Volume Dashboard</h1>
        
        <div class="controls">
            <select id="timeframe" onchange="loadData()">
                <option value="1m">1 Minute</option>
                <option value="2m">2 Minutes</option>
                <option value="3m">3 Minutes</option>
                <option value="5m" selected>5 Minutes</option>
                <option value="15m">15 Minutes</option>
            </select>
        </div>

        <div class="chart-container">
            <div class="chart-box">
                <canvas id="volumeChart"></canvas>
                <div class="timestamp" id="timestamp"></div>
            </div>
            <div class="chart-box">
                <canvas id="priceChart"></canvas>
                <div class="timestamp" id="priceTimestamp"></div>
            </div>
        </div>

        <script>
            let volumeChart, priceChart;
            let refreshInterval = 3000; // 3 seconds
            
            function initCharts() {
                const volumeCtx = document.getElementById('volumeChart');
                const priceCtx = document.getElementById('priceChart');
                
                volumeChart = new Chart(volumeCtx, {
                    type: 'bar',
                    data: { datasets: [] },
                    options: { responsive: true, maintainAspectRatio: false }
                });
                
                priceChart = new Chart(priceCtx, {
                    type: 'line',
                    data: { datasets: [] },
                    options: { responsive: true, maintainAspectRatio: false }
                });
                
                loadData();
                setInterval(loadData, refreshInterval);
            }
            
            async function loadData() {
                const timeframe = document.getElementById('timeframe').value;
                try {
                    const response = await axios.get(`/data?timeframe=${timeframe}`);
                    updateCharts(response.data);
                } catch (error) {
                    console.error("Error loading data:", error);
                }
            }
            
            function updateCharts(data) {
                // Volume Chart
                volumeChart.data = {
                    labels: ['Current', 'Previous'],
                    datasets: [{
                        label: `Volume (${data.timeframe})`,
                        data: [data.current_volume, data.prev_volume],
                        backgroundColor: [get_color(data), 'lightgray']
                    }]
                };
                volumeChart.update();
                document.getElementById('timestamp').textContent = `Last update: ${data.timestamp}`;
                
                // Price Chart
                priceChart.data = {
                    labels: ['Open', 'Close'],
                    datasets: [{
                        label: `Price (${data.timeframe})`,
                        data: [data.open, data.close],
                        borderColor: data.close > data.open ? 'green' : 'red',
                        backgroundColor: data.close > data.open ? 'rgba(0,255,0,0.1)' : 'rgba(255,0,0,0.1)',
                        borderWidth: 2
                    }]
                };
                priceChart.update();
                document.getElementById('priceTimestamp').textContent = `Last update: ${data.timestamp}`;
            }
            
            function get_color(data) {
                if (data.current_volume <= data.prev_volume) return 'gray';
                return data.close > data.open ? 'darkgreen' : 
                       data.close < data.open ? 'darkred' : 'green';
            }
            
            window.onload = initCharts;
        </script>
    </body>
    </html>
    """

@app.get("/data")
async def get_data(timeframe: str):
    data = get_sol_data(timeframe)
    return {
        **data,
        "color": get_color(data)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)