from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from services.state_store import state_store


class NotificationEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _channel(user_id: int) -> str:
        return f"notifications:user:{user_id}"

    async def publish(self, user_id: int, event: dict[str, Any]) -> None:
        payload = dict(event)
        payload["user_id"] = user_id

        async with self._lock:
            queues = list(self._subscribers.get(user_id, set()))
        for queue in queues:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

        try:
            redis = await state_store.get_client()
            if redis is None:
                return
            await redis.publish(self._channel(user_id), json.dumps(payload))
        except Exception:
            return

    async def subscribe(self, user_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        async with self._lock:
            if user_id not in self._subscribers:
                self._subscribers[user_id] = set()
            self._subscribers[user_id].add(queue)
        return queue

    async def unsubscribe(self, user_id: int, queue: asyncio.Queue) -> None:
        async with self._lock:
            queues = self._subscribers.get(user_id)
            if not queues:
                return
            queues.discard(queue)
            if not queues:
                self._subscribers.pop(user_id, None)

    async def subscribe_redis(self, user_id: int) -> Optional[Any]:
        try:
            redis = await state_store.get_client()
            if redis is None:
                return None
            pubsub = redis.pubsub()
            await pubsub.subscribe(self._channel(user_id))
            return pubsub
        except Exception:
            return None


notification_events = NotificationEventBus()
