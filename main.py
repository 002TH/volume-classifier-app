from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List

app = FastAPI()

# CORS for frontend to backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

class Candle(BaseModel):
    open: float
    close: float
    volume: float

@app.post("/classify")
async def classify(candles: List[Candle]):
    classified = []
    for i in range(len(candles)):
        color = "gray"
        if i > 0:
            prev = candles[i - 1]
            curr = candles[i]
            if curr.volume > prev.volume:
                if curr.close > curr.open:
                    color = "darkgreen"
                elif curr.close < curr.open:
                    color = "darkred"
                else:
                    color = "green"
        classified.append({
            "index": i,
            "open": curr.open,
            "close": curr.close,
            "volume": curr.volume,
            "color": color
        })
    return {"classified": classified}