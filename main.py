from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timedelta
import pytz

app = FastAPI()

# Config
SYMBOL = "SOLUSDT"
BINANCE_API = "https://api.binance.com/api/v3"
SUPPORTED_TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h"]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")


# Helper to fetch Binance klines
def get_klines(interval="5m", limit=50):
    try:
        if interval not in SUPPORTED_TIMEFRAMES:
            interval = "5m"

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; VolumeDashboard/1.0)"
        }

        response = requests.get(
            f"{BINANCE_API}/klines",
            params={
                "symbol": SYMBOL,
                "interval": interval,
                "limit": limit
            },
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        print(f"[❌ Klines Error] {e}")
        return None


# Helper to convert UTC to local time (Nigeria)
def utc_to_local(utc_ts):
    utc_time = datetime.utcfromtimestamp(utc_ts / 1000)
    lagos = pytz.timezone("Africa/Lagos")
    return utc_time.replace(tzinfo=pytz.utc).astimezone(lagos).strftime("%H:%M:%S")


@app.get("/realtime")
def get_realtime(timeframe: str = "5m"):
    print(f"🔁 [Realtime] Endpoint hit | Timeframe: {timeframe}")

    klines = get_klines(interval=timeframe, limit=2)
    if not klines or len(klines) < 2:
        return JSONResponse(content={"error": "Kline data unavailable"}, status_code=500)

    previous, latest = klines[-2], klines[-1]

    prev_volume = float(previous[5])
    latest_volume = float(latest[5])
    delta = latest_volume - prev_volume

    color = "#95a5a6"
    label = "Neutral"

    if delta > 0:
        color = "#00ff00"
        label = "Strong Buy"
    elif delta < 0:
        color = "#ff0000"
        label = "Strong Sell"

    response = {
        "time": utc_to_local(latest[0]),
        "volume": latest_volume,
        "delta": delta,
        "color": color,
        "label": label
    }
    return response


@app.get("/historical")
def get_historical(timeframe: str = "5m"):
    print(f"📚 [Historical] Endpoint hit | Timeframe: {timeframe}")

    data = get_klines(interval=timeframe, limit=50)
    if not data:
        return JSONResponse(content={"error": "Historical data unavailable"}, status_code=500)

    candles = []
    volumes = []

    for i in range(1, len(data)):
        curr = float(data[i][5])
        prev = float(data[i - 1][5])
        delta = curr - prev

        is_spike = False
        volumes.append(curr)
        local_time = utc_to_local(data[i][0])

        color = "#95a5a6"
        if delta > 0:
            color = "#00ff00"
        elif delta < 0:
            color = "#ff0000"

        candles.append({
            "time": local_time,
            "volume": curr,
            "delta": delta,
            "color": color,
            "is_spike": False
        })

    average_volume = sum(volumes) / len(volumes)

    for c in candles:
        if c["volume"] > average_volume * 1.5:
            c["is_spike"] = True

    response = {
        "average_volume": average_volume,
        "candles": candles
    }
    print(f"📊 [Historical] Data keys: {list(response.keys())}")
    return response

@app.get("/")
def root():
    return {"message": "App is working!"}