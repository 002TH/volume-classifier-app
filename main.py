from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Candle(BaseModel):
    open: float
    close: float
    volume: float

@app.post("/classify")
def classify(candles: List[Candle]):
    results = []
    for i in range(1, len(candles)):
        curr = candles[i]
        prev = candles[i - 1]
        if curr.volume < prev.volume:
            color = "gray"
        else:
            if (curr.close > curr.open and prev.close < prev.open) or (curr.close < curr.open and prev.close > prev.open):
                color = "lightgreen"
            elif curr.close > curr.open:
                color = "green"
            elif curr.close < curr.open:
                color = "red"
            else:
                color = "gray"
        results.append({
            "index": i,
            "open": curr.open,
            "close": curr.close,
            "volume": curr.volume,
            "color": color
        })
    return {"classified": results}
