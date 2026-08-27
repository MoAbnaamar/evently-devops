from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# Application settings loaded from environment variables at startup
class Settings(BaseSettings):

    # Read environment variables prefixed with EVENTLY_
    model_config = SettingsConfigDict(env_prefix="EVENTLY_")

    # Default application settings
    app_version: str = "dev"
    environment: str = "local"


# Retrieve and cache settings to avoid reading environment variables on every request
@lru_cache
def get_settings() -> Settings:
    return Settings()