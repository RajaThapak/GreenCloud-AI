# app/main.py
from fastapi import FastAPI
from .api.routes import api

app = FastAPI(title="GreenCloud AI")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(api)