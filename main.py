from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import requests

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

BINANCE_API = "https://api.binance.com/api/v3"
SYMBOL = "SOLUSDT"

# Supported timeframes including 1m and 3m
SUPPORTED_TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]

def get_klines(interval="5m", limit=1000):
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

def analyze_volume(interval="5m"):
    candles = get_klines(interval, 1000)
    if not candles or len(candles) < 2:
        return []
    
    results = []
    for i in range(1, len(candles)):
        prev_candle = candles[i-1]
        candle = candles[i]
        
        curr_delta = calculate_delta(candle)
        prev_delta = calculate_delta(prev_candle)
        
        # Calculate ratio (absolute values)
        abs_curr = abs(curr_delta)
        abs_prev = abs(prev_delta) if abs(prev_delta) > 0 else 1  # Avoid division by zero
        
        ratio = abs_curr / abs_prev
        
        # Determine color based on ratio and direction
        if ratio >= 1.5:  # Strong signal threshold
            if curr_delta > 0:
                color = "#00ff00"  # Green (strong buy)
            elif curr_delta < 0:
                color = "#ff0000"  # Red (strong sell)
            else:
                color = "#95a5a6"  # Gray (neutral)
        else:
            color = "#95a5a6"  # Gray (neutral)
        
        # Format time
        ts = datetime.fromtimestamp(candle[0]/1000).strftime('%H:%M')
        
        results.append({
            "time": ts,
            "volume": float(candle[5]),
            "delta": curr_delta,
            "color": color
        })
    
    return results

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/volume-data")
async def get_volume_data(timeframe: str = "5m"):
    data = analyze_volume(timeframe)
    if not data:
        return JSONResponse({"error": "Data fetch failed"}, status_code=500)
    return data