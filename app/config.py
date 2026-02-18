from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_FRUIT_CONFIG_PATH = Path("fruit.json")


class Settings(BaseSettings):
    """Application-level configuration."""

    model_config = SettingsConfigDict(env_prefix="UI_", extra="ignore")

    camera_service_base_url: AnyHttpUrl = Field(
        default="http://localhost:8200",
        description="Base URL for the Camera service API.",
    )
    fruit_config_path: Path = Field(
        default=DEFAULT_FRUIT_CONFIG_PATH,
        description="Filesystem path to the JSON file containing fruit names and per-kg prices.",
    )
    price_config_path: Path = Field(
        default=DEFAULT_FRUIT_CONFIG_PATH,
        description=(
            "Deprecated alias for UI_PRICE_CONFIG_PATH. "
            "Use UI_FRUIT_CONFIG_PATH instead."
        ),
    )

    def resolve_fruit_path(self) -> Path:
        # Keep backward compatibility with UI_PRICE_CONFIG_PATH while preferring UI_FRUIT_CONFIG_PATH.
        if "fruit_config_path" in self.model_fields_set:
            return self.fruit_config_path.expanduser().resolve()
        if "price_config_path" in self.model_fields_set:
            return self.price_config_path.expanduser().resolve()
        return self.fruit_config_path.expanduser().resolve()

    def resolve_price_path(self) -> Path:
        return self.resolve_fruit_path()


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


def build_settings(**overrides: Any) -> Settings:
    """Helper for tests to create non-cached settings with overrides."""

    return Settings(**overrides)


