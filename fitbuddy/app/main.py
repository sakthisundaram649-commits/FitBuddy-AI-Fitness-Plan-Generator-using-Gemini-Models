"""
main.py
FastAPI entry point for FitBuddy - AI Fitness Plan Generator.
Run with: uvicorn app.main:app --reload
Then visit http://127.0.0.1:8000
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import router

app = FastAPI(title="FitBuddy - AI Fitness Plan Generator")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(router)
