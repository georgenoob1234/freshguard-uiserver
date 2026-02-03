from __future__ import annotations

import logging
from pathlib import Path
import asyncio
from typing import Any, Dict, List, Optional, Set

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates

from .camera_client import CameraClient, CameraClientError, CameraImageNotFound
from .config import Settings, get_settings
from .models import ScanResult
from .pricing import PriceCatalog
from .services.ui_mapping import build_view_model
from .storage import LatestScanStorage

logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Scale UI Service")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

settings = get_settings()
storage = LatestScanStorage()
price_catalog = PriceCatalog(settings.resolve_price_path())
camera_client = CameraClient(str(settings.camera_service_base_url))
SCAN_RESULT_EVENT = "scan_result"


class WebSocketConnectionManager:
    """Tracks active websocket connections and handles broadcasts."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        async with self._lock:
            connections: List[WebSocket] = list(self._connections)

        if not connections:
            return

        stale: List[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)

        for connection in stale:
            await self.disconnect(connection)


ws_manager = WebSocketConnectionManager()


def _build_scan_message(scan: Optional[ScanResult], prices: PriceCatalog) -> Optional[Dict[str, Any]]:
    if not scan:
        return None
    payload = build_view_model(scan, prices)
    return {"type": SCAN_RESULT_EVENT, "payload": payload}


def get_price_catalog(_: Settings = Depends(get_settings)) -> PriceCatalog:
    return price_catalog


def get_camera_client(_: Settings = Depends(get_settings)) -> CameraClient:
    return camera_client


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/update")
async def update_scan(
    result: ScanResult,
    price_catalog: PriceCatalog = Depends(get_price_catalog),
) -> Dict[str, str]:
    await storage.set_latest(result)
    message = _build_scan_message(result, price_catalog)
    if message:
        await ws_manager.broadcast(message)
    return {"status": "ok"}


@app.get("/api/current")
async def get_current_scan(
    price_catalog: PriceCatalog = Depends(get_price_catalog),
) -> Dict[str, Any]:
    scan = await storage.get_latest()
    if not scan:
        return {"has_data": False}
    return {"has_data": True, "result": build_view_model(scan, price_catalog)}


@app.get("/", response_class=Response)
async def render_root(
    request: Request,
    price_catalog: PriceCatalog = Depends(get_price_catalog),
) -> Any:
    scan = await storage.get_latest()
    view = build_view_model(scan, price_catalog)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "view": view,
        },
    )


@app.get("/image/{image_id}")
async def proxy_image(
    image_id: str,
    camera_client: CameraClient = Depends(get_camera_client),
) -> Response:
    try:
        content, content_type = await camera_client.fetch_image_bytes(image_id)
        return Response(content=content, media_type=content_type)
    except CameraImageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CameraClientError as exc:
        logger.exception("Camera service error: %s", exc)
        raise HTTPException(status_code=502, detail="Ошибка камеры") from exc


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    price_catalog: PriceCatalog = Depends(get_price_catalog),
) -> None:
    await ws_manager.connect(websocket)
    try:
        latest = await storage.get_latest()
        message = _build_scan_message(latest, price_catalog)
        if message:
            await websocket.send_json(message)

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)
        raise


