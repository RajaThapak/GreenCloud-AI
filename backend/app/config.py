# app/config.py
from pydantic import model_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str 
    redis_url: str 
    ELECTRICITYMAPS_TOKEN: str = ""
    electricitymaps_base_url: str = "https://api.electricitymaps.com/v4"
    auth_secret: str = ""
    auth_token_ttl_minutes: int = 60
    class Config:
        env_file = ".env"

    @model_validator(mode="after")
    def validate_auth_configuration(self):
        if (
            not self.auth_secret
            or self.auth_secret == "change-this-auth-secret-in-production"
            or len(self.auth_secret) < 32
        ):
            raise ValueError(
                "AUTH_SECRET must be configured with at least 32 non-placeholder characters."
            )
        if self.auth_token_ttl_minutes <= 0:
            raise ValueError("AUTH_TOKEN_TTL_MINUTES must be greater than zero.")
        return self

settings = Settings()