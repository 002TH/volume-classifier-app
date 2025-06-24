from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

templates = Jinja2Templates(directory="templates")

class Candle(BaseModel):
    open: float
    close: float
    volume: float

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/classify")
def classify_candles(candles: List[Candle]):
    if len(candles) < 2:
        return {"error": "Need at least two candles"}

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