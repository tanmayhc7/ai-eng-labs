from functools import lru_cache
from pydantic import Field, SecretStr

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
        )

    anthropic_api_key: SecretStr
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = Field(default=512, ge=1, le=8192)
    temperature: float = Field(default=1.0, ge=0.0, le=1.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()