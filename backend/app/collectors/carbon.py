# app/collectors/carbon.py
import httpx
from datetime import datetime
from ..config import settings

ZONE = {"eu-north-1": "SE", "eu-west-1": "IE", "ca-central-1": "CA-ON",
        "us-east-1": "US-MIDA-PJM", "ap-south-1": "IN-WE"}   # verify zone codes in the provider docs

STATIC = {}  # region -> gCO2/kWh yearly average; fill from a published dataset

def fetch_carbon(region: str) -> tuple[float, str]:
    if settings.electricitymaps_token and region in ZONE:
        try:
            r = httpx.get("https://api.electricitymap.org/v3/carbon-intensity/latest",
                          params={"zone": ZONE[region]},
                          headers={"auth-token": settings.electricitymaps_token}, timeout=10)
            r.raise_for_status()
            return float(r.json()["carbonIntensity"]), "electricitymaps"
        except httpx.HTTPError:
            pass
    return STATIC[region], "static"