from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

# Create folder for web files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def dashboard():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SOL Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial; padding: 20px; }
            #chart { width: 800px; height: 400px; }
        </style>
    </head>
    <body>
        <h1>SOL Volume Dashboard</h1>
        <div id="chart">
            <canvas id="volumeChart"></canvas>
        </div>
        <script>
            // Simple chart
            const ctx = document.getElementById('volumeChart');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['SOL Volume'],
                    datasets: [{
                        label: 'Volume',
                        data: [10000],
                        backgroundColor: 'green'
                    }]
                }
            });
        </script>
    </body>
    </html>
    """)