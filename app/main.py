from __future__ import annotations

import hmac
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .camera_client import CameraClient, CameraClientError, CameraImageNotFound
from .config import Settings, get_settings
from .models import ScanResult
from .pricing import PriceCatalog
from .services.ui_mapping import build_view_model
from .storage import LatestScanStorage

logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Scale UI Service")

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

settings = get_settings()
storage = LatestScanStorage()
price_catalog = PriceCatalog(settings.resolve_fruit_path())
camera_client = CameraClient(str(settings.camera_service_base_url))
SCAN_RESULT_EVENT = "scan_result"
_logged_template_name: Optional[str] = None
_warned_default_staff_password = False


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


class StaffUnlockRequest(BaseModel):
    password: str = ""


def _log_staff_password_warning(app_settings: Settings) -> None:
    global _warned_default_staff_password
    if _warned_default_staff_password:
        return
    if app_settings.using_default_staff_password():
        logger.warning("UI_STAFF_PASSWORD is not set; default staff password is in use.")
    _warned_default_staff_password = True


def _get_active_template_name(app_settings: Settings) -> str:
    global _logged_template_name
    template_name = app_settings.resolve_template_name(TEMPLATES_DIR)
    if _logged_template_name != template_name:
        logger.info("Active UI template: %s", template_name)
        _logged_template_name = template_name
    return template_name


def _build_scan_message(scan: Optional[ScanResult], prices: PriceCatalog) -> Optional[Dict[str, Any]]:
    if not scan:
        return None
    payload = build_view_model(scan, prices)
    return {"type": SCAN_RESULT_EVENT, "payload": payload}


def get_price_catalog(_: Settings = Depends(get_settings)) -> PriceCatalog:
    return price_catalog


def get_camera_client(_: Settings = Depends(get_settings)) -> CameraClient:
    return camera_client


@app.on_event("startup")
async def startup_checks() -> None:
    _log_staff_password_warning(settings)
    _get_active_template_name(settings)


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
    app_settings: Settings = Depends(get_settings),
) -> Any:
    scan = await storage.get_latest()
    view = build_view_model(scan, price_catalog)
    _log_staff_password_warning(app_settings)
    template_name = _get_active_template_name(app_settings)
    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "view": view,
        },
    )


@app.post("/staff/unlock")
async def staff_unlock(
    payload: StaffUnlockRequest,
    request: Request,
    app_settings: Settings = Depends(get_settings),
) -> Dict[str, bool]:
    _log_staff_password_warning(app_settings)
    is_valid = hmac.compare_digest(payload.password, app_settings.staff_password)
    client_host = request.client.host if request.client else "unknown"
    if is_valid:
        logger.info("Staff unlock succeeded from %s", client_host)
    else:
        logger.warning("Staff unlock failed from %s", client_host)
    return {"ok": is_valid}


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


