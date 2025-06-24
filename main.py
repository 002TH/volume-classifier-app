from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime
import requests

app = FastAPI()

# Binance API configuration
BINANCE_API = "https://api.binance.com/api/v3"
TIMEFRAMES = ["1m", "3m", "5m", "15m"]

def get_sol_data(timeframe="5m"):
    try:
        response = requests.get(
            f"{BINANCE_API}/klines",
            params={"symbol": "SOLUSDT", "interval": timeframe, "limit": 2},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return {
            "timeframe": timeframe,
            "current_volume": float(data[-1][5]),
            "prev_volume": float(data[-2][5]),
            "open": float(data[-1][1]),
            "close": float(data[-1][4]),
            "timestamp": datetime.fromtimestamp(data[-1][0]/1000).strftime('%H:%M:%S')
        }
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def get_pressure(data):
    if not data:
        return "No Data", "gray"
    volume_change = data['current_volume'] - data['prev_volume']
    price_change = data['close'] - data['open']
    volume_change_pct = volume_change / data['prev_volume'] if data['prev_volume'] > 0 else 0
    if volume_change <= 0:
        return "Weak Pressure", "#95a5a6"
    if price_change > 0:
        return ("Strong Buying", "#00ff00") if volume_change_pct > 0.5 else ("Buying Pressure", "#2ecc71")
    elif price_change < 0:
        return ("Strong Selling", "#ff0000") if volume_change_pct > 0.5 else ("Selling Pressure", "#e74c3c")
    else:
        return "Neutral Accumulation", "#3498db"

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    data = get_sol_data()
    pressure, color = get_pressure(data) if data else ("No Data", "gray")

    current_volume = f"{data['current_volume']:,.0f}" if data else "N/A"
    prev_volume = f"{data['prev_volume']:,.0f}" if data else "N/A"
    open_price = f"{data['open']:.4f}" if data else "N/A"
    close_price = f"{data['close']:.4f}" if data else "N/A"
    timestamp = data['timestamp'] if data else "N/A"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SOLUSDT Pressure Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; background: #f5f5f5; max-width: 1000px; margin: auto; padding: 20px; }}
            .container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .controls {{ display: flex; gap: 10px; align-items: center; margin-bottom: 15px; }}
            .pressure-indicator {{ font-size: 1.2em; padding: 10px; font-weight: bold; border-radius: 5px; margin: 15px 0; background: #f8f9fa; }}
            .chart-container {{ width: 100%; height: 400px; margin: 20px 0; }}
            .info-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
            .info-card {{ background: #f8f9fa; padding: 10px; border-radius: 5px; }}
            select, button {{ padding: 8px 12px; font-size: 16px; border-radius: 5px; border: 1px solid #ddd; }}
            button {{ background: #3498db; color: white; cursor: pointer; border: none; }}
            .error {{ color: #e74c3c; background: #ffeeee; padding: 10px; border-radius: 5px; display: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="text-align:center;">SOL/USDT Pressure Dashboard</h1>
            <div class="controls">
                <select id="timeframe" onchange="loadData()">
                    <option value="1m">1 Minute</option>
                    <option value="3m">3 Minutes</option>
                    <option value="5m" selected>5 Minutes</option>
                    <option value="15m">15 Minutes</option>
                </select>
                <button onclick="loadData()">Refresh</button>
                <span id="lastUpdate">Last: {timestamp}</span>
            </div>
            <div class="pressure-indicator" style="color: {color};">{pressure}</div>
            <div class="chart-container">
                <canvas id="volumeChart"></canvas>
            </div>
            <div class="info-grid">
                <div class="info-card">
                    <strong>Volume</strong>
                    <div>Current: <span id="currentVolume">{current_volume}</span></div>
                    <div>Previous: <span id="prevVolume">{prev_volume}</span></div>
                </div>
                <div class="info-card">
                    <strong>Price</strong>
                    <div>Open: <span id="openPrice">{open_price}</span></div>
                    <div>Close: <span id="closePrice">{close_price}</span></div>
                </div>
                <div class="info-card">
                    <strong>Change</strong>
                    <div>Volume: <span id="volumeChange">0%</span></div>
                    <div>Price: <span id="priceChange">0%</span></div>
                </div>
            </div>
            <div id="error" class="error"></div>
        </div>
        <script>
            const ctx = document.getElementById('volumeChart').getContext('2d');
            let chart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: ['Volume'],
                    datasets: [{{
                        label: 'SOL Volume',
                        data: [{data['current_volume'] if data else 0}],
                        backgroundColor: '{color}',
                        borderColor: '{color}',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return 'Volume: ' + context.raw.toLocaleString();
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false,
                            ticks: {{
                                callback: function(value) {{
                                    return value.toLocaleString();
                                }}
                            }}
                        }}
                    }}
                }}
            }});

            async function loadData() {{
                const tf = document.getElementById("timeframe").value;
                try {{
                    const res = await fetch(`/data?timeframe=${{tf}}`);
                    const data = await res.json();

                    if (data.error) {{
                        document.getElementById("error").textContent = data.error;
                        document.getElementById("error").style.display = "block";
                        return;
                    }}

                    chart.data.datasets[0].data = [data.current_volume];
                    chart.data.datasets[0].backgroundColor = data.color;
                    chart.data.datasets[0].borderColor = data.color;
                    chart.update();

                    document.getElementById("currentVolume").textContent = data.current_volume.toLocaleString();
                    document.getElementById("prevVolume").textContent = data.prev_volume.toLocaleString();
                    document.getElementById("openPrice").textContent = data.open.toFixed(4);
                    document.getElementById("closePrice").textContent = data.close.toFixed(4);
                    document.getElementById("volumeChange").textContent = `${{((data.current_volume/data.prev_volume-1)*100).toFixed(2)}}%`;
                    document.getElementById("priceChange").textContent = `${{((data.close/data.open-1)*100).toFixed(2)}}%`;
                    document.getElementById("lastUpdate").textContent = "Last: " + data.timestamp;

                    const p = document.querySelector(".pressure-indicator");
                    p.textContent = data.pressure;
                    p.style.color = data.color;
                    document.getElementById("error").style.display = "none";
                }} catch (e) {{
                    document.getElementById("error").textContent = "Fetch failed: " + e.message;
                    document.getElementById("error").style.display = "block";
                }}
            }}

            setInterval(loadData, 3000);
        </script>
    </body>
    </html>
    """

@app.get("/data")
async def get_data(timeframe: str = "5m"):
    data = get_sol_data(timeframe)
    if not data:
        return {"error": "Failed to fetch data"}
    pressure, color = get_pressure(data)
    return {**data, "pressure": pressure, "color": color}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)