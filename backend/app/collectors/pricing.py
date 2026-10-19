# app/collectors/pricing.py
import json, boto3
from datetime import datetime
from ..db import SessionLocal
from ..models.market import PricingSnapshot

LOCATION = {"us-east-1": "US East (N. Virginia)", "eu-north-1": "EU (Stockholm)",
            "ap-south-1": "Asia Pacific (Mumbai)"}   # add the rest

def fetch_on_demand(region: str, instance_type: str) -> float | None:
    client = boto3.client("pricing", region_name="us-east-1")
    resp = client.get_products(ServiceCode="AmazonEC2", Filters=[
        {"Type": "TERM_MATCH", "Field": f, "Value": v} for f, v in [
            ("location", LOCATION[region]), ("instanceType", instance_type),
            ("operatingSystem", "Linux"), ("tenancy", "Shared"),
            ("preInstalledSw", "NA"), ("capacitystatus", "Used")]])
    if not resp["PriceList"]:
        return None
    terms = json.loads(resp["PriceList"][0])["terms"]["OnDemand"]
    dim = next(iter(next(iter(terms.values()))["priceDimensions"].values()))
    return float(dim["pricePerUnit"]["USD"])