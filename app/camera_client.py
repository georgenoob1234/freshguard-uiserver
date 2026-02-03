from __future__ import annotations

import httpx


class CameraClientError(Exception):
    """Base class for camera client errors."""


class CameraImageNotFound(CameraClientError):
    """Raised when the camera service returns 404."""


class CameraClient:
    """Thin wrapper around the Camera service image endpoint."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def fetch_image_bytes(self, image_id: str) -> tuple[bytes, str]:
        image_filename = f"{image_id}.jpg"
        url = f"{self._base_url}/api/images/{image_filename}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url)

        if response.status_code == 404:
            raise CameraImageNotFound(f"Image {image_id} not found")

        if response.is_error:
            raise CameraClientError(
                f"Camera service error {response.status_code}: {response.text}"
            )

        content_type = response.headers.get("content-type", "image/jpeg")
        return response.content, content_type


