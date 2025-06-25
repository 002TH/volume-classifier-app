from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import requests
import math
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static", html=True), name="static")

BINANCE_API = "https://api.binance.com/api/v3"
SYMBOL = "SOLUSDT"

def convert_candle(candle):
    """Convert all numeric fields in Binance candle to floats"""
    return [
        float(candle[0]),  # open time
        float(candle[1]),  # open
        float(candle[2]),  # high
        float(candle[3]),  # low
        float(candle[4]),  # close
        float(candle[5]),  # volume
        float(candle[6]),  # close time
        float(candle[7]),  # quote asset volume
        int(candle[8]),    # number of trades
        float(candle[9]),  # taker buy base asset volume
        float(candle[10]), # taker buy quote asset volume
        candle[11]         # ignore
    ]

def get_klines(interval="5m", limit=50):
    try:
        response = requests.get(f"{BINANCE_API}/klines", params={
            "symbol": SYMBOL,
            "interval": interval,
            "limit": limit
        }, timeout=5)
        response.raise_for_status()
        return [convert_candle(item) for item in response.json()]
    except Exception as e:
        print(f"Error: {e}")
        return None

def calculate_delta(candle):
    """Calculate buy/sell volume delta using tick rule"""
    close = candle[4]
    open_ = candle[1]
    volume = candle[5]
    
    if close > open_:
        return {"buy_volume": volume, "sell_volume": 0, "delta": volume}
    elif close < open_:
        return {"buy_volume": 0, "sell_volume": volume, "delta": -volume}
    else:
        return {"buy_volume": volume/2, "sell_volume": volume/2, "delta": 0}

def tanh(x):
    """Hyperbolic tangent replacement without numpy"""
    return (math.exp(x) - math.exp(-x)) / (math.exp(x) + math.exp(-x))

def analyze_candle(candle, prev_candle):
    delta_data = calculate_delta(candle)
    prev_delta = calculate_delta(prev_candle)
    
    open_ = candle[1]
    close = candle[4]
    volume = candle[5]
    ts = datetime.fromtimestamp(candle[0]/1000).strftime('%H:%M:%S')
    
    # Calculate volume ratios
    prev_volume = prev_candle[5] if prev_candle[5] > 0 else 1
    volume_ratio = volume / prev_volume
    delta_ratio = delta_data['delta'] / abs(prev_delta['delta']) if prev_delta['delta'] != 0 else 0
    
    # Determine candle type
    candle_type = "bullish" if close > open_ else "bearish" if close < open_ else "neutral"
    
    # Calculate combined strength score (-100 to 100)
    strength_score = min(100, max(-100, 
        (30 * (1 if candle_type == "bullish" else -1 if candle_type == "bearish" else 0)) +
        (40 * math.log(1 + volume_ratio) * (1 if delta_data['delta'] > 0 else -1)) +
        (30 * tanh(delta_ratio))
    ))
    
    return {
        "time": ts,
        "open": open_,
        "close": close,
        "volume": volume,
        "delta": delta_data['delta'],
        "buy_volume": delta_data['buy_volume'],
        "sell_volume": delta_data['sell_volume'],
        "candle_type": candle_type,
        "strength_score": strength_score,
        "volume_ratio": volume_ratio,
        "delta_ratio": delta_ratio
    }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return HTMLResponse(content=open("static/index.html").read(), status_code=200)

@app.get("/realtime")
async def get_realtime(timeframe: str = "1m"):
    data = get_klines(interval=timeframe, limit=2)
    if not data or len(data) < 2:
        return JSONResponse({"error": "Data fetch failed"}, status_code=500)
    return analyze_candle(data[-1], data[-2])

@app.get("/historical")
async def get_historical(timeframe: str = "1m"):
    data = get_klines(interval=timeframe, limit=50)
    if not data:
        return JSONResponse({"error": "Data fetch failed"}, status_code=500)
    return [analyze_candle(data[i], data[i-1]) for i in range(1, len(data))]