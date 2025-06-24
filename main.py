from fastapi import FastAPI
from datetime import datetime
import requests
from typing import Optional

app = FastAPI()

BINANCE_API = "https://api.binance.com/api/v3"

def get_candle_data(timeframe: str) -> Optional[dict]:
    """Fetch candle data from Binance"""
    try:
        response = requests.get(
            f"{BINANCE_API}/klines",
            params={
                "symbol": "SOLUSDT",
                "interval": timeframe,
                "limit": 2
            }
        )
        response.raise_for_status()
        candles = response.json()
        return {
            "current": {
                "open": float(candles[-1][1]),
                "close": float(candles[-1][4]),
                "volume": float(candles[-1][5])
            },
            "previous": {
                "volume": float(candles[-2][5])
            }
        }
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def determine_color(data: dict) -> str:
    """Determine color based on volume and price rules"""
    if data["current"]["volume"] <= data["previous"]["volume"]:
        return "gray"
    else:
        if data["current"]["close"] > data["current"]["open"]:
            return "darkgreen"
        elif data["current"]["close"] < data["current"]["open"]:
            return "darkred"
        else:
            return "green"

@app.get("/indicator")
async def get_indicator(timeframe: str = "5m"):
    """Endpoint to get the indicator color"""
    valid_timeframes = ["1m", "2m", "3m", "5m", "15m"]
    if timeframe not in valid_timeframes:
        return {"error": "Invalid timeframe. Use 1m, 2m, 3m, 5m, or 15m"}
    
    data = get_candle_data(timeframe)
    if not data:
        return {"error": "Could not fetch data from Binance"}
    
    color = determine_color(data)
    return {
        "symbol": "SOLUSDT",
        "timeframe": timeframe,
        "current_volume": data["current"]["volume"],
        "previous_volume": data["previous"]["volume"],
        "open": data["current"]["open"],
        "close": data["current"]["close"],
        "color": color,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def health_check():
    return {"status": "healthy", "service": "SOLUSDT Volume Indicator"}