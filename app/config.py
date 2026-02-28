from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_FRUIT_CONFIG_PATH = Path("fruit.json")
DEFAULT_UI_TEMPLATE_NAME = "index_new.html"
DEFAULT_UI_STAFF_PASSWORD = "1234"

logger = logging.getLogger(__name__)


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
    template_name: str = Field(
        default=DEFAULT_UI_TEMPLATE_NAME,
        description="UI template file name (within templates directory).",
    )
    staff_password: str = Field(
        default=DEFAULT_UI_STAFF_PASSWORD,
        description="Staff mode unlock password.",
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

    @staticmethod
    def _is_valid_template_name(template_name: str) -> bool:
        if not template_name:
            return False
        if "/" in template_name or "\\" in template_name or ".." in template_name:
            return False
        return template_name.lower().endswith(".html")

    def resolve_template_name(self, templates_dir: Path) -> str:
        template_name = (self.template_name or "").strip()
        if not self._is_valid_template_name(template_name):
            logger.warning(
                "Invalid UI template name '%s'; falling back to '%s'.",
                template_name or "<empty>",
                DEFAULT_UI_TEMPLATE_NAME,
            )
            template_name = DEFAULT_UI_TEMPLATE_NAME

        if (templates_dir / template_name).exists():
            return template_name

        logger.error(
            "Configured UI template '%s' is missing; falling back to '%s'.",
            template_name,
            DEFAULT_UI_TEMPLATE_NAME,
        )
        return DEFAULT_UI_TEMPLATE_NAME

    def using_default_staff_password(self) -> bool:
        return "staff_password" not in self.model_fields_set


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


def build_settings(**overrides: Any) -> Settings:
    """Helper for tests to create non-cached settings with overrides."""

    return Settings(**overrides)


