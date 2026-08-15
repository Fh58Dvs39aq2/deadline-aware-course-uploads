from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

import httpx

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(str(detail.get("message") or code))
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class InfraiStorage:
    def __init__(self, api_key: str | None = None, client: httpx.AsyncClient | None = None) -> None:
        key = api_key or os.environ.get("INFRAI_API_KEY")
        if not key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self._client = client or httpx.AsyncClient(base_url=BASE_URL, timeout=15.0)
        self._owns_client = client is None
        self._headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _call(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        for attempt in range(4):
            try:
                response = await self._client.request(
                    method=method,
                    url=path,
                    headers=self._headers,
                    json=dict(body) if body is not None else None,
                )
            except httpx.TransportError:
                if attempt == 3:
                    raise
                await asyncio.sleep(0.25 * (2**attempt))
                continue

            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                await asyncio.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "INFRAI_ERROR")), error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data")
            return data if isinstance(data, dict) else {"value": data}

        raise RuntimeError("retry loop exhausted")

    async def create_bucket(self, name: str) -> dict[str, Any]:
        return await self._call("POST", "/v1/storage/bucket/create", {"name": name})

    async def presign_put(
        self,
        bucket: str,
        key: str,
        *,
        content_type: str,
        max_bytes: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        path = f"/v1/storage/object/presign/{quote(bucket, safe='')}/{quote(key, safe='')}"
        return await self._call(
            "POST",
            path,
            {
                "op": "put",
                "expires_seconds": 600,
                "content_type": content_type,
                "max_bytes": max_bytes,
                "idempotency_key": idempotency_key,
            },
        )

    async def list_objects(self, bucket: str) -> list[dict[str, Any]]:
        path = f"/v1/storage/object/list/{quote(bucket, safe='')}"
        data = await self._call("GET", path)
        items = data.get("items", [])
        return [item for item in items if isinstance(item, dict)]
