from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

BINANCE_API = "https://api.binance.com/api/v3"
SYMBOL = "SOLUSDT"
SUPPORTED_TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h"]

def get_klines(interval="5m", limit=50):
    try:
        if interval not in SUPPORTED_TIMEFRAMES:
            interval = "5m"
        
        response = requests.get(f"{BINANCE_API}/klines", params={
            "symbol": SYMBOL,
            "interval": interval,
            "limit": limit
        }, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def calculate_delta(candle):
    total_volume = float(candle[5])
    taker_buy_volume = float(candle[9])
    taker_sell_volume = total_volume - taker_buy_volume
    return taker_buy_volume - taker_sell_volume, total_volume

def analyze_candle(candle, prev_candle):
    curr_delta, total_volume = calculate_delta(candle)
    prev_delta, _ = calculate_delta(prev_candle)

    abs_curr = abs(curr_delta)
    abs_prev = abs(prev_delta) if abs(prev_delta) > 0 else 1
    ratio = abs_curr / abs_prev

    if ratio >= 1.5:
        if curr_delta > 0:
            label = "Strong Buying"
            color = "#00ff00"
        elif curr_delta < 0:
            label = "Strong Selling"
            color = "#ff0000"
        else:
            label = "Neutral"
            color = "#95a5a6"
    else:
        label = "Neutral"
        color = "#95a5a6"

    ts = datetime.fromtimestamp(candle[0] / 1000, ZoneInfo("Africa/Lagos")).strftime('%H:%M:%S')

    return {
        "time": ts,
        "open": float(candle[1]),
        "close": float(candle[4]),
        "volume": total_volume,
        "delta": curr_delta,
        "label": label,
        "color": color
    }

def get_realtime_data(interval="5m"):
    data = get_klines(interval, 2)
    if not data or len(data) < 2:
        return None
    return analyze_candle(data[-1], data[-2])

def get_historical_data(interval="5m"):
    data = get_klines(interval, 50)
    if not data:
        return None

    volumes = [float(candle[5]) for candle in data]
    average_volume = sum(volumes) / len(volumes) if volumes else 0

    results = []
    for i in range(1, len(data)):
        candle_data = analyze_candle(data[i], data[i - 1])
        candle_data["is_spike"] = candle_data["volume"] > average_volume
        results.append(candle_data)

    return {
        "candles": results,
        "average_volume": average_volume
    }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/realtime")
async def get_realtime(timeframe: str = "5m"):
    data = get_realtime_data(timeframe)
    if not data:
        return JSONResponse({"error": "Data fetch failed"}, status_code=500)
    return data

@app.get("/historical")
async def get_historical(timeframe: str = "5m"):
    data = get_historical_data(timeframe)
    if not data:
        return JSONResponse({"error": "Data fetch failed"}, status_code=500)
    return data