from __future__ import annotations

import asyncio
import hashlib
import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from tortoise import Tortoise

from services.email_notifications import email_notifications
from services.slack_notifications import slack_notifications
from services.notification_templates import render_email, render_slack, TemplateError


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_idempotency_key(*parts: Any) -> str:
    raw = ":".join(str(p) for p in parts if p is not None)
    if len(raw) <= 200:
        return raw
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"hash:{digest}"


@dataclass
class DeliveryRecord:
    delivery_id: int
    user_id: Optional[int]
    channel: str
    event_type: str
    app_id: Optional[str]
    payload: dict[str, Any]
    attempts: int
    max_attempts: int


class NotificationDeliveryService:
    async def enqueue(
        self,
        *,
        channel: str,
        event_type: str,
        app_id: Optional[str],
        user_id: Optional[int],
        payload: dict[str, Any],
        idempotency_key: str,
        max_attempts: int = 5,
    ) -> Optional[int]:
        conn = Tortoise.get_connection("default")
        try:
            result = await conn.execute_query(
                """
                INSERT INTO notification_deliveries (
                    user_id,
                    channel,
                    event_type,
                    app_id,
                    idempotency_key,
                    status,
                    attempts,
                    max_attempts,
                    next_attempt_at,
                    payload,
                    created_at,
                    updated_at
                )
                VALUES ($1, $2, $3, $4, $5, 'pending', 0, $6, NOW(), $7, NOW(), NOW())
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id
                """,
                [user_id, channel, event_type, app_id, idempotency_key, max_attempts, json.dumps(payload)],
            )
        except Exception:
            return None

        rows = result[1] if result else []
        if not rows:
            return None
        return rows[0]["id"]

    async def enqueue_email(
        self,
        *,
        event_type: str,
        app_id: Optional[str],
        user_id: int,
        to_email: str,
        template_data: dict[str, Any],
        idempotency_key: str,
    ) -> Optional[int]:
        payload = {
            "to_email": to_email,
            "template_data": template_data,
        }
        return await self.enqueue(
            channel="email",
            event_type=event_type,
            app_id=app_id,
            user_id=user_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )

    async def enqueue_slack(
        self,
        *,
        event_type: str,
        app_id: Optional[str],
        user_id: int,
        template_data: dict[str, Any],
        idempotency_key: str,
    ) -> Optional[int]:
        payload = {
            "template_data": template_data,
        }
        return await self.enqueue(
            channel="slack",
            event_type=event_type,
            app_id=app_id,
            user_id=user_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )

    async def claim_deliveries(self, *, limit: int, stale_after_seconds: int) -> list[DeliveryRecord]:
        conn = Tortoise.get_connection("default")
        stale_cutoff = _utcnow() - timedelta(seconds=stale_after_seconds)
        result = await conn.execute_query(
            """
            WITH candidates AS (
                SELECT id
                FROM notification_deliveries
                WHERE (
                    status = 'pending' AND next_attempt_at <= NOW()
                ) OR (
                    status = 'sending' AND updated_at < $2
                )
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT $1
            )
            UPDATE notification_deliveries
            SET status = 'sending',
                attempts = attempts + 1,
                updated_at = NOW()
            WHERE id IN (SELECT id FROM candidates)
            RETURNING id, user_id, channel, event_type, app_id, payload, attempts, max_attempts
            """,
            [limit, stale_cutoff],
        )
        records: list[DeliveryRecord] = []
        for row in result[1]:
            payload = row.get("payload") or {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {}
            records.append(
                DeliveryRecord(
                    delivery_id=row["id"],
                    user_id=row.get("user_id"),
                    channel=row["channel"],
                    event_type=row["event_type"],
                    app_id=row.get("app_id"),
                    payload=payload,
                    attempts=int(row.get("attempts") or 0),
                    max_attempts=int(row.get("max_attempts") or 5),
                )
            )
        return records

    async def mark_sent(self, delivery_id: int, provider_response: Optional[str] = None) -> None:
        conn = Tortoise.get_connection("default")
        await conn.execute_query(
            """
            UPDATE notification_deliveries
            SET status = 'sent',
                sent_at = NOW(),
                updated_at = NOW(),
                last_error = NULL,
                provider_response = $2
            WHERE id = $1
            """,
            [delivery_id, provider_response],
        )

    async def mark_failed(self, delivery_id: int, error: str, *, retry_at: Optional[datetime]) -> None:
        conn = Tortoise.get_connection("default")
        if retry_at:
            await conn.execute_query(
                """
                UPDATE notification_deliveries
                SET status = 'pending',
                    next_attempt_at = $2,
                    updated_at = NOW(),
                    last_error = $3
                WHERE id = $1
                """,
                [delivery_id, retry_at, error],
            )
        else:
            await conn.execute_query(
                """
                UPDATE notification_deliveries
                SET status = 'failed',
                    updated_at = NOW(),
                    last_error = $2
                WHERE id = $1
                """,
                [delivery_id, error],
            )


def _compute_backoff_seconds(attempts: int) -> float:
    base = 5.0
    max_delay = 300.0
    delay = min(base * (2 ** max(attempts - 1, 0)), max_delay)
    jitter = random.uniform(0, 2.0)
    return delay + jitter


class NotificationDeliveryWorker:
    def __init__(self, service: NotificationDeliveryService):
        self._service = service
        self._stop_event = asyncio.Event()
        self._poll_interval = 2.0
        self._batch_size = 10
        self._stale_after_seconds = 300

    def stop(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                deliveries = await self._service.claim_deliveries(
                    limit=self._batch_size,
                    stale_after_seconds=self._stale_after_seconds,
                )
            except Exception:
                deliveries = []

            if not deliveries:
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self._poll_interval)
                except asyncio.TimeoutError:
                    continue
                continue

            for delivery in deliveries:
                if self._stop_event.is_set():
                    return
                await self._process_delivery(delivery)

    async def _process_delivery(self, delivery: DeliveryRecord) -> None:
        payload = delivery.payload or {}
        template_data = payload.get("template_data") or {}
        try:
            if delivery.channel == "email":
                if not email_notifications.is_configured():
                    raise RuntimeError("Email service not configured")
                to_email = payload.get("to_email")
                if not to_email:
                    raise RuntimeError("Missing email recipient")
                subject, body = render_email(delivery.event_type, template_data)
                await asyncio.to_thread(
                    email_notifications.send_text_email,
                    to_email=to_email,
                    subject=subject,
                    body=body,
                )
                await self._service.mark_sent(delivery.delivery_id)
                return

            if delivery.channel == "slack":
                if not slack_notifications.is_configured():
                    raise RuntimeError("Slack webhook not configured")
                title, message, color = render_slack(delivery.event_type, template_data)
                ok = await slack_notifications.send_notification(message=message, title=title, color=color)
                if not ok:
                    raise RuntimeError("Slack send failed")
                await self._service.mark_sent(delivery.delivery_id)
                return

            raise RuntimeError(f"Unknown delivery channel: {delivery.channel}")
        except TemplateError as exc:
            await self._service.mark_failed(delivery.delivery_id, str(exc), retry_at=None)
        except Exception as exc:
            if delivery.attempts >= delivery.max_attempts:
                await self._service.mark_failed(delivery.delivery_id, str(exc), retry_at=None)
                return
            delay_seconds = _compute_backoff_seconds(delivery.attempts)
            retry_at = _utcnow() + timedelta(seconds=delay_seconds)
            await self._service.mark_failed(delivery.delivery_id, str(exc), retry_at=retry_at)


notification_delivery = NotificationDeliveryService()
notification_delivery_worker = NotificationDeliveryWorker(notification_delivery)
