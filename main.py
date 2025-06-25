from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import requests

app = FastAPI()

BINANCE_API = "https://api.binance.com/api/v3"

def get_klines(timeframe="5m", limit=20):
    try:
        response = requests.get(
            f"{BINANCE_API}/klines",
            params={"symbol": "SOLUSDT", "interval": timeframe, "limit": limit},
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching klines: {e}")
        return []

def classify_candle(open_, close, volume, prev_volume):
    if volume <= prev_volume:
        return "gray", "Weak Pressure"
    elif close > open_:
        if volume > prev_volume * 1.5:
            return "#00ff00", "Strong Buying"
        return "#2ecc71", "Buying Pressure"
    elif close < open_:
        if volume > prev_volume * 1.5:
            return "#ff0000", "Strong Selling"
        return "#e74c3c", "Selling Pressure"
    else:
        return "#3498db", "Neutral"

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SOL Volume History</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 960px;
                margin: 20px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            canvas { background: #fff; border-radius: 10px; }
        </style>
    </head>
    <body>
        <h2>SOL/USDT Volume Pressure</h2>
        <select id="tf" onchange="loadChart()">
            <option value="1m">1m</option>
            <option value="3m">3m</option>
            <option value="5m" selected>5m</option>
            <option value="15m">15m</option>
        </select>
        <canvas id="volChart" height="300"></canvas>
        <script>
            async function loadChart() {
                const tf = document.getElementById("tf").value;
                const res = await fetch(`/history?timeframe=${tf}`);
                const data = await res.json();

                const ctx = document.getElementById("volChart").getContext("2d");
                if (window.chart) window.chart.destroy();

                window.chart = new Chart(ctx, {
                    type: "bar",
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: "Volume",
                            data: data.volumes,
                            backgroundColor: data.colors
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            x: { ticks: { maxRotation: 90, minRotation: 45 }},
                            y: { beginAtZero: false }
                        }
                    }
                });
            }

            loadChart();
            setInterval(loadChart, 3000);
        </script>
    </body>
    </html>
    """)

@app.get("/history")
async def get_history(timeframe: str = "5m"):
    klines = get_klines(timeframe)
    if not klines or len(klines) < 2:
        return JSONResponse(content={"error": "Not enough data"}, status_code=400)

    labels = []
    volumes = []
    colors = []

    for i in range(1, len(klines)):
        prev = klines[i-1]
        curr = klines[i]

        open_ = float(curr[1])
        close = float(curr[4])
        volume = float(curr[5])
        prev_volume = float(prev[5])
        ts = datetime.fromtimestamp(curr[0] / 1000).strftime("%H:%M")

        color, _ = classify_candle(open_, close, volume, prev_volume)

        labels.append(ts)
        volumes.append(volume)
        colors.append(color)

    return {
        "labels": labels,
        "volumes": volumes,
        "colors": colors
    }