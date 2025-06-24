from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime
import requests

app = FastAPI()

# Binance API configuration
BINANCE_API = "https://api.binance.com/api/v3"
TIMEFRAMES = ["1m", "3m", "5m", "15m"]

def get_sol_data(timeframe="5m"):
    """Fetch SOL/USDT data from Binance"""
    try:
        response = requests.get(
            f"{BINANCE_API}/klines",
            params={
                "symbol": "SOLUSDT",
                "interval": timeframe,
                "limit": 2
            },
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

def get_color(data):
    """Determine bar color based on your rules"""
    if not data:
        return "gray"
    if data["current_volume"] <= data["prev_volume"]:
        return "gray"
    elif data["close"] > data["open"]:
        return "#2ecc71"  # green
    elif data["close"] < data["open"]:
        return "#e74c3c"  # red
    return "#3498db"  # blue

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    data = get_sol_data()
    color = get_color(data)
    
    # Safely format the numbers
    current_volume = f"{data['current_volume']:,.0f}" if data else "N/A"
    prev_volume = f"{data['prev_volume']:,.0f}" if data else "N/A"
    open_price = f"{data['open']:.4f}" if data else "N/A"
    close_price = f"{data['close']:.4f}" if data else "N/A"
    timestamp = data['timestamp'] if data else "N/A"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SOLUSDT Volume Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}
            .chart-container {{
                width: 100%;
                height: 400px;
            }}
            .controls {{
                display: flex;
                gap: 10px;
                align-items: center;
            }}
            select {{
                padding: 8px;
                font-size: 16px;
            }}
            .info {{
                display: flex;
                justify-content: space-between;
                background: #f8f9fa;
                padding: 10px;
                border-radius: 5px;
            }}
            .error {{
                color: red;
                padding: 10px;
                background: #ffeeee;
                border-radius: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>SOL/USDT Volume Dashboard</h1>
            
            <div class="controls">
                <select id="timeframe" onchange="loadData()">
                    <option value="1m">1 Minute</option>
                    <option value="3m">3 Minutes</option>
                    <option value="5m" selected>5 Minutes</option>
                    <option value="15m">15 Minutes</option>
                </select>
                <button onclick="loadData()">Refresh</button>
                <span id="lastUpdate">{timestamp}</span>
            </div>
            
            <div class="chart-container">
                <canvas id="volumeChart"></canvas>
            </div>
            
            <div class="info">
                <div>
                    <strong>Current Volume:</strong> 
                    <span id="currentVolume">{current_volume}</span>
                </div>
                <div>
                    <strong>Previous Volume:</strong> 
                    <span id="prevVolume">{prev_volume}</span>
                </div>
                <div>
                    <strong>Price:</strong> 
                    <span id="price">{open_price} → {close_price}</span>
                </div>
            </div>
            
            <div id="error" class="error" style="display: none;"></div>
        </div>

        <script>
            // Initialize chart
            const ctx = document.getElementById('volumeChart').getContext('2d');
            let chart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: ['Current Volume'],
                    datasets: [{{
                        label: 'SOL Volume',
                        data: [{data['current_volume'] if data else 0}],
                        backgroundColor: '{color}'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{
                            beginAtZero: false
                        }}
                    }}
                }}
            }});
            
            // Auto-refresh every 3 seconds
            setInterval(loadData, 3000);
            
            async function loadData() {{
                const timeframe = document.getElementById('timeframe').value;
                try {{
                    const response = await fetch(`/data?timeframe=${{timeframe}}`);
                    const data = await response.json();
                    
                    if (data.error) {{
                        showError(data.error);
                        return;
                    }}
                    
                    // Update chart
                    chart.data.datasets[0].data = [data.current_volume];
                    chart.data.datasets[0].backgroundColor = data.color;
                    chart.update();
                    
                    // Update info
                    document.getElementById('currentVolume').textContent = data.current_volume.toLocaleString();
                    document.getElementById('prevVolume').textContent = data.prev_volume.toLocaleString();
                    document.getElementById('price').textContent = `${{data.open.toFixed(4)}} → ${{data.close.toFixed(4)}}`;
                    document.getElementById('lastUpdate').textContent = `Last update: ${{data.timestamp}}`;
                    document.getElementById('error').style.display = 'none';
                }} catch (e) {{
                    showError("Failed to load data: " + e.message);
                }}
            }}
            
            function showError(message) {{
                const errorEl = document.getElementById('error');
                errorEl.textContent = message;
                errorEl.style.display = 'block';
            }}
        </script>
    </body>
    </html>
    """

@app.get("/data")
async def get_data(timeframe: str = "5m"):
    """Endpoint for AJAX data requests"""
    data = get_sol_data(timeframe)
    if not data:
        return {"error": "Failed to fetch data from Binance"}
    return {
        **data,
        "color": get_color(data)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)