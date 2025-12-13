from __future__ import annotations

import json
import os
from typing import Any, Optional

from redis.asyncio import Redis, from_url


class StateStore:
    def __init__(self) -> None:
        self._redis: Optional[Redis] = None

    def _build_redis_url(self) -> Optional[str]:
        url = os.getenv("REDIS_URL", "").strip()
        if url:
            return url
        host = os.getenv("REDIS_HOST", "").strip()
        if not host:
            return None
        port = os.getenv("REDIS_PORT", "6379").strip() or "6379"
        tls = os.getenv("REDIS_TLS", "true").strip().lower() in {"1", "true", "yes", "y"}
        scheme = "rediss" if tls else "redis"
        return f"{scheme}://{host}:{port}/0"

    async def _get_redis(self) -> Optional[Redis]:
        if self._redis is not None:
            return self._redis

        redis_url = self._build_redis_url()
        if not redis_url:
            return None

        client = from_url(redis_url, encoding="utf-8", decode_responses=True)
        await client.ping()
        self._redis = client
        return self._redis

    async def available(self) -> bool:
        try:
            return await self._get_redis() is not None
        except Exception:
            self._redis = None
            return False

    @staticmethod
    def key(*, app: str, session_id: str, kind: str) -> str:
        return f"state:{app}:{session_id}:{kind}"

    async def get_json(self, key: str, default: Any) -> Any:
        redis_client = await self._get_redis()
        if redis_client is None:
            return default

        value = await redis_client.get(key)
        if not value:
            return default

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    async def set_json(self, key: str, value: Any, *, ttl_seconds: int) -> None:
        redis_client = await self._get_redis()
        if redis_client is None:
            return
        await redis_client.set(key, json.dumps(value), ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        redis_client = await self._get_redis()
        if redis_client is None:
            return
        await redis_client.delete(key)


state_store = StateStore()
