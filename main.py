from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/test")
async def test_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <body>
        <h1 style="color: red;">If you see this, it works!</h1>
    </body>
    </html>
    """)

@app.get("/dashboard")
async def dashboard():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard</title>
    </head>
    <body>
        <h1>Basic Dashboard</h1>
    </body>
    </html>
    """)