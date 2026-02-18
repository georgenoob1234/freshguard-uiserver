from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)
UNKNOWN_FRUIT_NAME = "Неизвестно"


class PriceCatalog:
    """Loads and provides fruit names and per-fruit prices from a JSON file."""

    def __init__(self, fruit_file: Path) -> None:
        self._fruit_file = fruit_file
        self._prices: Dict[str, float] = {}
        self._pretty_names: Dict[str, str] = {}
        self._load_catalog()

    def _load_catalog(self) -> None:
        if not self._fruit_file.exists():
            logger.warning(
                "Fruit config file %s does not exist; fruit names default to '%s' and prices to 0",
                self._fruit_file,
                UNKNOWN_FRUIT_NAME,
            )
            self._prices = {}
            self._pretty_names = {}
            return

        try:
            content = self._fruit_file.read_text(encoding="utf-8")
            raw = json.loads(content)
            if not isinstance(raw, dict):
                raise ValueError("Fruit config must be a JSON object")

            prices: Dict[str, float] = {}
            pretty_names: Dict[str, str] = {}

            for key, value in raw.items():
                if not isinstance(key, str):
                    logger.warning(
                        "Skipping non-string fruit class key %r in %s",
                        key,
                        self._fruit_file,
                    )
                    continue

                pretty_name = UNKNOWN_FRUIT_NAME
                price = 0.0

                if isinstance(value, dict):
                    raw_name = value.get("name")
                    if isinstance(raw_name, str) and raw_name.strip():
                        pretty_name = raw_name
                    elif raw_name is not None:
                        logger.warning(
                            "Invalid name for fruit '%s' in %s; using '%s'",
                            key,
                            self._fruit_file,
                            UNKNOWN_FRUIT_NAME,
                        )

                    raw_price = value.get("price_per_kg")
                    if isinstance(raw_price, (int, float)):
                        price = float(raw_price)
                    elif raw_price is not None:
                        logger.warning(
                            "Invalid price_per_kg for fruit '%s' in %s; using 0.0",
                            key,
                            self._fruit_file,
                        )
                elif isinstance(value, (int, float)):
                    # Legacy compatibility: old format was { "<fruit_class>": <price> }.
                    logger.warning(
                        "Legacy fruit config format detected for '%s' in %s; "
                        "please migrate to {\"name\": ..., \"price_per_kg\": ...}",
                        key,
                        self._fruit_file,
                    )
                    price = float(value)
                else:
                    logger.warning(
                        "Invalid config entry for fruit '%s' in %s; using defaults",
                        key,
                        self._fruit_file,
                    )

                pretty_names[key] = pretty_name
                prices[key] = price

            self._pretty_names = pretty_names
            self._prices = prices
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to load fruit config: %s", exc)
            self._prices = {}
            self._pretty_names = {}

    def get_price(self, fruit_class: Optional[str]) -> Optional[float]:
        if fruit_class is None:
            return None
        return self._prices.get(fruit_class, 0.0)

    def get_pretty_name(self, fruit_class: Optional[str]) -> str:
        if fruit_class is None:
            return UNKNOWN_FRUIT_NAME
        return self._pretty_names.get(fruit_class, UNKNOWN_FRUIT_NAME)

    @property
    def prices(self) -> Dict[str, float]:
        return dict(self._prices)

    @property
    def pretty_names(self) -> Dict[str, str]:
        return dict(self._pretty_names)


