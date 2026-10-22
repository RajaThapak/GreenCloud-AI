# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str 
    redis_url: str 
    ELECTRICITYMAPS_TOKEN: str = ""
    electricitymaps_base_url: str = "https://api.electricitymaps.com/v4"
    class Config:
        env_file = ".env"

settings = Settings()