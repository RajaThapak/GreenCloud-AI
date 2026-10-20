# app/collectors/tasks.py
from ..celery_app import celery
from .config import REGIONS
from .spot import collect_spot
from .carbon import collect_carbon
from .pricing import collect_pricing

@celery.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def collect_spot_all():
    return {r: collect_spot(r) for r in REGIONS}
# write collect_carbon_all and collect_pricing_all the same way

@celery.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def collect_carbon_all():
    return {r: collect_carbon(r) for r in REGIONS}

@celery.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def collect_pricing_all():
    return {r: collect_pricing(r) for r in REGIONS}