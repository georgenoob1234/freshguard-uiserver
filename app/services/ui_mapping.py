from __future__ import annotations

from typing import Any, Dict, Optional

from ..models import FruitSummary, ScanResult
from ..pricing import PriceCatalog

FRUIT_NAME_MAP: Dict[str, str] = {}


def get_pretty_name(fruit_class: Optional[str], prices: PriceCatalog) -> str:
    # Keep public FRUIT_NAME_MAP entry-point compatible, but source names from config.
    FRUIT_NAME_MAP.clear()
    FRUIT_NAME_MAP.update(prices.pretty_names)
    return prices.get_pretty_name(fruit_class)


def get_price_per_kg(fruit_class: Optional[str], prices: PriceCatalog) -> Optional[float]:
    return prices.get_price(fruit_class)


def _format_number(value: Optional[float], decimals: int) -> str:
    if value is None:
        return "—"
    format_str = f"{{:.{decimals}f}}"
    return format_str.format(value)


def _derive_quality(fruit: Optional[FruitSummary]) -> tuple[str, str]:
    if fruit is None:
        return "Нет данных о качестве", "unknown"

    if fruit.defects:
        return "Обнаружены дефекты продукта", "bad"

    return "Продукт соответствует стандарту качества", "good"


def build_view_model(
    scan: Optional[ScanResult],
    prices: PriceCatalog,
) -> Dict[str, Any]:
    fruit: Optional[FruitSummary] = None
    if scan and scan.fruits:
        fruit = scan.fruits[0]

    fruit_class = fruit.fruit_class if fruit else None
    
    # Show "Мульти-фрукт" when multiple unique fruit types are detected
    # (e.g., 1 apple + 1 banana, not 2 apples)
    unique_fruit_classes = {f.fruit_class for f in scan.fruits} if scan and scan.fruits else set()
    is_multi_fruit = len(unique_fruit_classes) > 1
    if is_multi_fruit:
        fruit_name = "Мульти-фрукт"
    else:
        fruit_name = get_pretty_name(fruit_class, prices)

    weight_kg_val: Optional[float] = None
    if scan:
        weight_kg_val = round(scan.weight_grams / 1000, 3)

    # No price for multi-fruit (show dash)
    price_val = None if is_multi_fruit else get_price_per_kg(fruit_class, prices)
    total_price_val: Optional[float] = None
    if weight_kg_val is not None and price_val is not None:
        total_price_val = round(weight_kg_val * price_val, 2)

    quality_text, quality_state = _derive_quality(fruit)

    # Determine price display: dash for multi-fruit, "нет цены" for missing price
    if is_multi_fruit:
        price_display = "—"
    elif price_val is not None:
        price_display = _format_number(price_val, 2)
    else:
        price_display = "нет цены"

    return {
        "fruit_name": fruit_name,
        "weight_display": _format_number(weight_kg_val, 3),
        "price_display": price_display,
        "total_display": _format_number(total_price_val, 2),
        "quality_text": quality_text,
        "quality_state": quality_state,
        "image_id": scan.image_id if scan else None,
        "session_id": str(scan.session_id) if scan else None,
        "raw_scan": _dump_scan(scan),
        "has_data": scan is not None,
    }


def _dump_scan(scan: Optional[ScanResult]) -> Optional[Dict[str, Any]]:
    if not scan:
        return None
    dump_fn = getattr(scan, "model_dump", None)
    if callable(dump_fn):
        return dump_fn(mode="json")
    return scan.dict()  # type: ignore[no-any-return]



