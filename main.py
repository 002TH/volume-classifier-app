import asyncio
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from zoneinfo import ZoneInfo
import websockets
from collections import deque

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

SYMBOL = "solusdt"
CANDLE_LIMIT = 50
WS_URL = f"wss://stream.binance.com:9443/ws/{SYMBOL}@kline_5m"

# Shared buffer for last 50 candles
candles = deque(maxlen=CANDLE_LIMIT)

def analyze_candle(kline):
    candle = kline["k"]
    open_time = candle["t"]
    open_price = float(candle["o"])
    close_price = float(candle["c"])
    total_volume = float(candle["v"])
    taker_buy_volume = float(candle["V"])
    taker_sell_volume = total_volume - taker_buy_volume
    delta = taker_buy_volume - taker_sell_volume

    label = "Neutral"
    color = "#95a5a6"
    if len(candles) > 0:
        prev = candles[-1]
        prev_delta = prev["delta"]
        ratio = abs(delta) / (abs(prev_delta) if prev_delta else 1)
        if ratio >= 1.5:
            if delta > 0:
                label = "Strong Buying"
                color = "#00ff00"
            elif delta < 0:
                label = "Strong Selling"
                color = "#ff0000"

    ts = datetime.fromtimestamp(open_time / 1000, ZoneInfo("Africa/Lagos")).strftime('%H:%M:%S')

    return {
        "time": ts,
        "open": open_price,
        "close": close_price,
        "volume": total_volume,
        "delta": delta,
        "label": label,
        "color": color,
        "is_spike": False  # to be updated later
    }

@app.on_event("startup")
async def start_ws_listener():
    async def listen():
        while True:
            try:
                async with websockets.connect(WS_URL, ping_interval=20) as ws:
                    async for message in ws:
                        data = json.loads(message)
                        if data.get("e") == "kline" and data["k"]["x"]:  # Candle closed
                            candle_data = analyze_candle(data)
                            candles.append(candle_data)
                            # Recalculate average and spikes
                            volumes = [c["volume"] for c in candles]
                            avg_volume = sum(volumes) / len(volumes)
                            for c in candles:
                                c["is_spike"] = c["volume"] > avg_volume
            except Exception as e:
                print("WebSocket Error:", e)
                await asyncio.sleep(5)

    asyncio.create_task(listen())

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/realtime")
async def get_realtime(timeframe: str = "5m"):
    if len(candles) < 2:
        return JSONResponse({"error": "Not enough data"}, status_code=500)
    return candles[-1]

@app.get("/historical")
async def get_historical(timeframe: str = "5m"):
    if not candles:
        return JSONResponse({"error": "No historical data"}, status_code=500)

    avg_volume = sum(c["volume"] for c in candles) / len(candles)
    return {
        "candles": list(candles),
        "average_volume": avg_volume
    }