from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import requests

app = FastAPI()
BINANCE_API = "https://api.binance.com/api/v3"

def get_sol_data(timeframe="1m", limit=2):
    try:
        response = requests.get(
            f"{BINANCE_API}/klines",
            params={"symbol": "SOLUSDT", "interval": timeframe, "limit": limit},
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching Binance data: {e}")
        return None

def classify_pressure(kline):
    open_price = float(kline[1])
    close_price = float(kline[4])
    volume = float(kline[5])
    timestamp = datetime.fromtimestamp(kline[0] / 1000).strftime('%H:%M:%S')

    return {
        "open": open_price,
        "close": close_price,
        "volume": volume,
        "timestamp": timestamp,
        "color": get_color(open_price, close_price, volume)
    }

def get_color(open_price, close_price, volume_diff):
    if volume_diff <= 0:
        return "gray"
    if close_price > open_price:
        return "#006400" if volume_diff > 0 else "#2ecc71"
    elif close_price < open_price:
        return "#8B0000" if volume_diff > 0 else "#e74c3c"
    return "#3498db"

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SOLUSDT Volume Classifier</title>
        <style>
            body { font-family: Arial; background: #f4f4f4; padding: 20px; }
            .panel { background: white; padding: 15px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .live { font-size: 18px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 8px; text-align: center; }
            th { background: #333; color: white; }
        </style>
    </head>
    <body>
        <div class="panel live" id="livePanel">
            Loading live data...
        </div>
        <div class="panel">
            <label for="tf">Select timeframe:</label>
            <select id="tf" onchange="loadHistory()">
                <option value="1m">1m</option>
                <option value="3m" selected>3m</option>
                <option value="5m">5m</option>
                <option value="15m">15m</option>
            </select>
            <div id="historyPanel">Loading history...</div>
        </div>

        <script>
            async function loadLive() {
                try {
                    const res = await fetch("/live");
                    const data = await res.json();
                    document.getElementById("livePanel").innerHTML = `
                        <strong>Live (${data.timestamp}):</strong><br>
                        Open: ${data.open} | Close: ${data.close} | Volume: ${data.volume}<br>
                        <span style="color:${data.color}; font-weight:bold;">${data.pressure}</span>
                    `;
                } catch {
                    document.getElementById("livePanel").innerText = "Error loading live data.";
                }
            }

            async function loadHistory() {
                const tf = document.getElementById("tf").value;
                const res = await fetch(`/history?timeframe=${tf}`);
                const history = await res.json();
                let html = "<table><tr><th>Time</th><th>Open</th><th>Close</th><th>Volume</th><th>Pressure</th></tr>";
                for (let row of history) {
                    html += `<tr style="color:${row.color};">
                        <td>${row.timestamp}</td>
                        <td>${row.open}</td>
                        <td>${row.close}</td>
                        <td>${row.volume}</td>
                        <td>${row.pressure}</td>
                    </tr>`;
                }
                html += "</table>";
                document.getElementById("historyPanel").innerHTML = html;
            }

            loadLive();
            loadHistory();
            setInterval(loadLive, 3000);
        </script>
    </body>
    </html>
    """

@app.get("/live")
async def live_data():
    klines = get_sol_data("1m", 2)
    if not klines or len(klines) < 2:
        return JSONResponse({"error": "No data"}, status_code=500)

    prev_vol = float(klines[-2][5])
    curr = classify_pressure(klines[-1])
    volume_diff = curr["volume"] - prev_vol

    curr["pressure"] = (
        "Strong Buying" if volume_diff > 0 and curr["close"] > curr["open"] else
        "Strong Selling" if volume_diff > 0 and curr["close"] < curr["open"] else
        "Neutral" if volume_diff > 0 else "Weak"
    )
    return curr

@app.get("/history")
async def historical_data(timeframe: str = "3m"):
    klines = get_sol_data(timeframe, 20)
    if not klines:
        return []

    history = []
    for i in range(1, len(klines)):
        prev = float(klines[i - 1][5])
        curr = classify_pressure(klines[i])
        diff = curr["volume"] - prev
        pressure = (
            "Strong Buying" if diff > 0 and curr["close"] > curr["open"] else
            "Strong Selling" if diff > 0 and curr["close"] < curr["open"] else
            "Neutral" if diff > 0 else "Weak"
        )
        curr["pressure"] = pressure
        history.append(curr)
    return history

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)