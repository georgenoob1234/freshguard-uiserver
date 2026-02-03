from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PriceCatalog:
    """Loads and provides per-fruit prices from a JSON file."""

    def __init__(self, price_file: Path) -> None:
        self._price_file = price_file
        self._prices: Dict[str, float] = {}
        self._load_prices()

    def _load_prices(self) -> None:
        if not self._price_file.exists():
            logger.warning(
                "Price config file %s does not exist; all prices default to 0",
                self._price_file,
            )
            self._prices = {}
            return

        try:
            content = self._price_file.read_text(encoding="utf-8")
            raw = json.loads(content)
            if not isinstance(raw, dict):
                raise ValueError("Price config must be a JSON object")
            self._prices = {
                key: float(value)
                for key, value in raw.items()
                if isinstance(value, (int, float))
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to load price config: %s", exc)
            self._prices = {}

    def get_price(self, fruit_class: Optional[str]) -> Optional[float]:
        if fruit_class is None:
            return None
        return self._prices.get(fruit_class)

    @property
    def prices(self) -> Dict[str, float]:
        return dict(self._prices)


