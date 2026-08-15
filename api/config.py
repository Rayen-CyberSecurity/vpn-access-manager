"""Configuration, read once from the environment at import time."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # postgresql://user:password@host:port/dbname
    database_url: str
    # shared secret required on every write endpoint
    api_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
