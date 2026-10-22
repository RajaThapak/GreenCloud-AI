# app/celery_app.py
from celery import Celery
from celery.schedules import crontab
from .config import settings

celery = Celery("greencloud", broker=settings.redis_url, include=["app.collectors.tasks"])
celery.conf.beat_schedule = {
    "spot":    {"task": "app.collectors.tasks.collect_spot_all",    "schedule": 300.0},
    "carbon":  {"task": "app.collectors.tasks.collect_carbon_all",  "schedule": 1800.0},
    "pricing": {"task": "app.collectors.tasks.collect_pricing_all", "schedule": crontab(hour=3, minute=0)},
}