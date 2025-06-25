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

def analyze_volume(candle, prev_candle):
    curr_vol = float(candle[5])
    prev_vol = float(prev_candle[5])
    open_ = float(candle[1])
    close = float(candle[4])
    ts = datetime.fromtimestamp(candle[0]/1000).strftime('%H:%M:%S')

    if curr_vol <= prev_vol:
        return {"label": "Weak Pressure", "color": "#95a5a6", "volume": curr_vol, "open": open_, "close": close, "time": ts}

    if close > open_:
        return {"label": "Strong Buying" if curr_vol > prev_vol * 1.5 else "Buying Pressure",
                "color": "#ff008000" if curr_vol > prev_vol * 1.5 else "#2ecc71",
                "volume": curr_vol, "open": open_, "close": close, "time": ts}
    elif close < open_:
        return {"label": "Strong Selling" if curr_vol > prev_vol * 1.5 else "Selling Pressure",
                "color": "#ff0000" if curr_vol > prev_vol * 1.5 else "#ffc0504d",
                "volume": curr_vol, "open": open_, "close": close, "time": ts}
    else:
        return {"label": "Neutral", "color": "#3498db", "volume": curr_vol, "open": open_, "close": close, "time": ts}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/realtime")
async def get_realtime(timeframe: str = "1m"):
    data = get_klines(interval=timeframe, limit=2)
    if not data:
        return JSONResponse({"error": "Data fetch failed"}, status_code=500)
    result = analyze_volume(data[-1], data[-2])
    return result

@app.get("/historical")
async def get_historical(timeframe: str = "1m"):
    data = get_klines(interval=timeframe, limit=50)
    if not data:
        return JSONResponse({"error": "Data fetch failed"}, status_code=500)
    candles = []
    for i in range(1, len(data)):
        result = analyze_volume(data[i], data[i-1])
        candles.append(result)
    return candles