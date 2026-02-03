from __future__ import annotations

import asyncio
from typing import Optional

from .models import ScanResult


class LatestScanStorage:
    """In-memory storage for the latest scan result."""

    def __init__(self) -> None:
        self._latest: Optional[ScanResult] = None
        self._lock = asyncio.Lock()

    async def set_latest(self, result: ScanResult) -> None:
        async with self._lock:
            self._latest = result

    async def get_latest(self) -> Optional[ScanResult]:
        async with self._lock:
            return self._latest


