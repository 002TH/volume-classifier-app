from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import requests

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

BINANCE_API = "https://api.binance.com/api/v3"

def fetch_candle_data(symbol="SOLUSDT", interval="1m", limit=100):
    try:
        url = f"{BINANCE_API}/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()
        data = res.json()

        candles = []
        for d in data:
            candles.append({
                "time": d[0],
                "open": float(d[1]),
                "high": float(d[2]),
                "low": float(d[3]),
                "close": float(d[4]),
                "volume": float(d[5])
            })

        return candles
    except Exception as e:
        print(f"Fetch error: {e}")
        return []

def classify_volume(candle, prev_candle):
    if not candle or not prev_candle:
        return "No Data", "gray"

    curr_vol = candle["volume"]
    prev_vol = prev_candle["volume"]
    price_diff = candle["close"] - candle["open"]
    vol_change = curr_vol - prev_vol
    vol_change_pct = vol_change / prev_vol if prev_vol else 0

    if curr_vol <= prev_vol:
        return "Weak Volume", "#7f8c8d"  # Gray

    if price_diff > 0:
        if vol_change_pct > 0.5:
            return "Strong Buying", "#00ff00"
        return "Buying Pressure", "#2ecc71"
    elif price_diff < 0:
        if vol_change_pct > 0.5:
            return "Strong Selling", "#ff0000"
        return "Selling Pressure", "#e74c3c"
    else:
        return "Neutral", "#3498db"

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SOLUSDT Volume Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-chart-financial"></script>
        <style>
            body { font-family: Arial; padding: 20px; background: #f4f4f4; }
            h1 { text-align: center; }
            .panel { margin-bottom: 40px; }
            canvas { background: white; border-radius: 10px; }
            #metrics { font-weight: bold; text-align: center; margin: 10px; }
        </style>
    </head>
    <body>
        <h1>SOLUSDT Volume Dashboard</h1>

        <div class="panel">
            <h3>🔴 Current Candle (Updates every 3 seconds)</h3>
            <div id="metrics">Loading...</div>
            <canvas id="liveChart" height="300"></canvas>
        </div>

        <div class="panel">
            <h3>📊 Historical Candles</h3>
            <select id="intervalSelect" onchange="loadHistory()">
                <option value="1m">1m</option>
                <option value="3m">3m</option>
                <option value="5m" selected>5m</option>
                <option value="15m">15m</option>
            </select>
            <canvas id="historyChart" height="300"></canvas>
        </div>

        <script>
            const liveChart = new Chart(document.getElementById("liveChart").getContext("2d"), {
                type: 'candlestick',
                data: { datasets: [{ label: "Live", data: [] }] },
                options: {
                    scales: {
                        x: { type: 'time', time: { unit: 'minute' } },
                        y: { beginAtZero: false }
                    }
                }
            });

            const historyChart = new Chart(document.getElementById("historyChart").getContext("2d"), {
                type: 'candlestick',
                data: { datasets: [{ label: "History", data: [] }] },
                options: {
                    scales: {
                        x: { type: 'time', time: { unit: 'minute' } },
                        y: { beginAtZero: false }
                    }
                }
            });

            async function updateLive() {
                const res = await fetch('/live');
                const data = await res.json();

                liveChart.data.datasets[0].data = [data.candle];
                liveChart.update();

                document.getElementById("metrics").innerHTML = `
                    Time: ${data.timestamp}<br>
                    Open: ${data.candle.o} | High: ${data.candle.h}<br>
                    Low: ${data.candle.l} | Close: ${data.candle.c}<br>
                    Volume: ${data.volume.toLocaleString()}<br>
                    Signal: <span style="color:${data.color}">${data.signal}</span>
                `;
            }

            async function loadHistory() {
                const interval = document.getElementById("intervalSelect").value;
                const res = await fetch(`/history?interval=${interval}`);
                const data = await res.json();

                historyChart.data.datasets[0].data = data;
                historyChart.update();
            }

            setInterval(updateLive, 3000);
            updateLive();
            loadHistory();
        </script>
    </body>
    </html>
    """)

@app.get("/live")
async def live_data():
    candles = fetch_candle_data(interval="1m", limit=2)
    if len(candles) < 2:
        return JSONResponse({"error": "Insufficient data"}, status_code=500)

    current = candles[-1]
    previous = candles[-2]
    signal, color = classify_volume(current, previous)

    return {
        "timestamp": datetime.fromtimestamp(current["time"] / 1000).strftime("%H:%M:%S"),
        "candle": {
            "x": current["time"],
            "o": current["open"],
            "h": current["high"],
            "l": current["low"],
            "c": current["close"]
        },
        "volume": current["volume"],
        "signal": signal,
        "color": color
    }

@app.get("/history")
async def history_data(interval: str = "5m"):
    candles = fetch_candle_data(interval=interval, limit=100)
    formatted = [{
        "x": c["time"],
        "o": c["open"],
        "h": c["high"],
        "l": c["low"],
        "c": c["close"]
    } for c in candles]
    return formatted