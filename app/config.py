from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-level configuration."""

    model_config = SettingsConfigDict(env_prefix="UI_", extra="ignore")

    camera_service_base_url: AnyHttpUrl = Field(
        default="http://localhost:8200",
        description="Base URL for the Camera service API.",
    )
    price_config_path: Path = Field(
        default=Path("prices.json"),
        description="Filesystem path to the JSON file containing per-fruit prices.",
    )

    def resolve_price_path(self) -> Path:
        return self.price_config_path.expanduser().resolve()


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


def build_settings(**overrides: Any) -> Settings:
    """Helper for tests to create non-cached settings with overrides."""

    return Settings(**overrides)


