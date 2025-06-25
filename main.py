from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import requests

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

BINANCE_API = "https://api.binance.com/api/v3"
SYMBOL = "SOLUSDT"

def get_klines(interval="5m", limit=50):
    try:
        response = requests.get(f"{BINANCE_API}/klines", params={
            "symbol": SYMBOL,
            "interval": interval,
            "limit": limit
        }, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def calculate_delta(candle):
    """Calculate buy/sell volume delta using tick rule"""
    close = float(candle[4])
    open_ = float(candle[1])
    volume = float(candle[5])
    
    if close > open_:  # Bullish candle - all volume counted as buy
        return volume
    elif close < open_:  # Bearish candle - all volume counted as sell
        return -volume
    else:  # Neutral candle - split volume
        return 0

def analyze_volume(candle, prev_candle):
    curr_delta = calculate_delta(candle)
    prev_delta = calculate_delta(prev_candle)
    open_ = float(candle[1])
    close = float(candle[4])
    ts = datetime.fromtimestamp(candle[0]/1000).strftime('%H:%M:%S')

    # Neutral case
    if curr_delta == 0:
        return {
            "label": "Neutral",
            "color": "#3498db",
            "volume": float(candle[5]),
            "delta": 0,
            "open": open_,
            "close": close,
            "time": ts
        }

    # Determine strength based on delta change
    delta_ratio = abs(curr_delta) / abs(prev_delta) if prev_delta != 0 else 1

    if curr_delta > 0:  # Buying pressure
        if delta_ratio > 1.5:
            return {
                "label": "Strong Buying",
                "color": "#00ff00",
                "volume": float(candle[5]),
                "delta": curr_delta,
                "open": open_,
                "close": close,
                "time": ts
            }
        else:
            return {
                "label": "Buying Pressure",
                "color": "#2ecc71",
                "volume": float(candle[5]),
                "delta": curr_delta,
                "open": open_,
                "close": close,
                "time": ts
            }
    else:  # Selling pressure
        if delta_ratio > 1.5:
            return {
                "label": "Strong Selling",
                "color": "#ff0000",
                "volume": float(candle[5]),
                "delta": curr_delta,
                "open": open_,
                "close": close,
                "time": ts
            }
        else:
            return {
                "label": "Selling Pressure",
                "color": "#e74c3c",
                "volume": float(candle[5]),
                "delta": curr_delta,
                "open": open_,
                "close": close,
                "time": ts
            }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/realtime")
async def get_realtime(timeframe: str = "1m"):
    data = get_klines(interval=timeframe, limit=2)
    if not data or len(data) < 2:
        return JSONResponse({"error": "Data fetch failed"}, status_code=500)
    return analyze_volume(data[-1], data[-2])

@app.get("/historical")
async def get_historical(timeframe: str = "1m"):
    data = get_klines(interval=timeframe, limit=50)
    if not data:
        return JSONResponse({"error": "Data fetch failed"}, status_code=500)
    return [analyze_volume(data[i], data[i-1]) for i in range(1, len(data))]