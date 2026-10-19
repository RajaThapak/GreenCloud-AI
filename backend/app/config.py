# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str 
    redis_url: str 
    electricitymaps_token: str = ""
    class Config:
        env_file = ".env"

settings = Settings()