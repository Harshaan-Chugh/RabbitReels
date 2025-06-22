#!/usr/bin/env python3

import os
import sys

# Add the repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Test static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
print(f"Static directory: {static_dir}")
print(f"Static directory exists: {os.path.exists(static_dir)}")
if os.path.exists(static_dir):
    print(f"Files in static directory: {os.listdir(static_dir)}")

try:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    print("✅ Static files mounted successfully")
except Exception as e:
    print(f"❌ Failed to mount static files: {e}")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/login.html")

@app.get("/test")
async def test():
    return {"message": "Test endpoint works!"}

@app.get("/debug")
async def debug():
    return {
        "static_dir": static_dir,
        "static_exists": os.path.exists(static_dir),
        "routes": [{"path": route.path, "methods": list(route.methods) if hasattr(route, 'methods') else "mount"} for route in app.routes]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
