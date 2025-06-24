from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
from datetime import datetime

app = FastAPI()

BINANCE_API = "https://api.binance.com/api/v3"

def get_sol_data():
    response = requests.get(f"{BINANCE_API}/klines?symbol=SOLUSDT&interval=5m&limit=2")
    data = response.json()
    return {
        "current_volume": float(data[-1][5]),
        "prev_volume": float(data[-2][5]),
        "open": float(data[-1][1]),
        "close": float(data[-1][4])
    }

def get_color(data):
    if data["current_volume"] <= data["prev_volume"]:
        return "gray"
    elif data["close"] > data["open"]:
        return "darkgreen"
    elif data["close"] < data["open"]:
        return "darkred"
    else:
        return "green"

@app.get("/")
async def dashboard():
    data = get_sol_data()
    color = get_color(data)
    
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SOL Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: Arial; padding: 20px; }}
            #chart {{ width: 100%; max-width: 800px; height: 400px; margin: 0 auto; }}
            h1 {{ text-align: center; }}
        </style>
    </head>
    <body>
        <h1>SOL/USDT Volume</h1>
        <div id="chart">
            <canvas id="volumeChart"></canvas>
        </div>
        <script>
            const ctx = document.getElementById('volumeChart');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: ['Current Volume'],
                    datasets: [{{
                        label: 'SOL Volume',
                        data: [{data["current_volume"]}],
                        backgroundColor: '{color}'
                    }}]
                }},
                options: {{
                    scales: {{
                        y: {{ beginAtZero: false }}
                    }}
                }}
            }});
        </script>
        <p style="text-align: center;">
            Open: ${data["open"]} | Close: ${data["close"]} | Volume: {data["current_volume"]:,.0f}
        </p>
    </body>
    </html>
    """)