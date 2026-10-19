# app/main.py
from fastapi import FastAPI
app = FastAPI(title="GreenCloud AI")

@app.get("/health")
def health():
    return {"status": "ok"}