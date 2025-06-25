from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import requests
import numpy as np

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

BINANCE_API = "https://api.binance.com/api/v3"
SYMBOL = "SOLUSDT"

# Supported timeframes
SUPPORTED_TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]

def get_klines(interval="5m", limit=50):
    try:
        # Validate timeframe
        if interval not in SUPPORTED_TIMEFRAMES:
            interval = "5m"  # Default to 5m if invalid
        
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
    """Calculate buy/sell volume delta using tick rule"""
    close = float(candle[4])
    open_ = float(candle[1])
    volume = float(candle[5])
    
    if close > open_:  # Bullish candle
        return volume
    elif close < open_:  # Bearish candle
        return -volume
    else:  # Neutral candle
        return 0

def analyze_candle(candle, prev_candle):
    """Analyze a single candle with previous candle context"""
    curr_delta = calculate_delta(candle)
    prev_delta = calculate_delta(prev_candle)
    
    # Calculate ratio (absolute values)
    abs_curr = abs(curr_delta)
    abs_prev = abs(prev_delta) if abs(prev_delta) > 0 else 1  # Avoid division by zero
    
    ratio = abs_curr / abs_prev
    
    # Determine color based on ratio and direction
    if ratio >= 1.5:  # Strong signal threshold
        if curr_delta > 0:
            label = "Strong Buying"
            color = "#00ff00"  # Green (strong buy)
        elif curr_delta < 0:
            label = "Strong Selling"
            color = "#ff0000"  # Red (strong sell)
        else:
            label = "Neutral"
            color = "#95a5a6"  # Gray (neutral)
    else:
        label = "Neutral"
        color = "#95a5a6"  # Gray (neutral)
    
    # Format time
    ts = datetime.fromtimestamp(candle[0]/1000).strftime('%H:%M:%S')
    
    return {
        "time": ts,
        "open": float(candle[1]),
        "close": float(candle[4]),
        "volume": float(candle[5]),
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
    
    # Calculate average volume
    volumes = [float(candle[5]) for candle in data]
    average_volume = sum(volumes) / len(volumes) if volumes else 0
    
    results = []
    for i in range(1, len(data)):
        candle_data = analyze_candle(data[i], data[i-1])
        # Add spike indicator
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