"""In-app notifications service for the notification center bell icon."""
from datetime import datetime, timezone
from typing import Optional
from tortoise import Tortoise

from services.notification_events import notification_events


class InAppNotificationService:
    """Service for creating and managing in-app notifications."""

    async def create_notification(
        self,
        user_id: int,
        app_id: str,
        title: str,
        message: Optional[str] = None,
        link: Optional[str] = None,
    ) -> int:
        """Create a new in-app notification. Returns the notification ID."""
        conn = Tortoise.get_connection("default")
        result = await conn.execute_query(
            """
            INSERT INTO in_app_notifications (user_id, app_id, title, message, link, is_read, created_at)
            VALUES ($1, $2, $3, $4, $5, FALSE, NOW())
            RETURNING id, created_at
            """,
            [user_id, app_id, title, message, link],
        )
        row = result[1][0]
        payload = {
            "id": row["id"],
            "app_id": app_id,
            "title": title,
            "message": message,
            "link": link,
            "is_read": False,
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        }
        try:
            await notification_events.publish(user_id, {"event": "notification", "notification": payload})
        except Exception:
            pass
        return row["id"]

    async def get_user_notifications(
        self,
        user_id: int,
        limit: int = 20,
        unread_only: bool = False,
    ) -> list[dict]:
        """Fetch notifications for a user, newest first."""
        conn = Tortoise.get_connection("default")
        if unread_only:
            result = await conn.execute_query(
                """
                SELECT id, app_id, title, message, link, is_read, created_at
                FROM in_app_notifications
                WHERE user_id = $1 AND is_read = FALSE
                ORDER BY created_at DESC
                LIMIT $2
                """,
                [user_id, limit],
            )
        else:
            result = await conn.execute_query(
                """
                SELECT id, app_id, title, message, link, is_read, created_at
                FROM in_app_notifications
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                [user_id, limit],
            )
        return [
            {
                "id": row["id"],
                "app_id": row["app_id"],
                "title": row["title"],
                "message": row["message"],
                "link": row["link"],
                "is_read": row["is_read"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in result[1]
        ]

    async def get_notifications_since(
        self,
        user_id: int,
        since_id: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        """Fetch notifications newer than a specific ID."""
        conn = Tortoise.get_connection("default")
        result = await conn.execute_query(
            """
            SELECT id, app_id, title, message, link, is_read, created_at
            FROM in_app_notifications
            WHERE user_id = $1 AND id > $2
            ORDER BY id ASC
            LIMIT $3
            """,
            [user_id, since_id, limit],
        )
        return [
            {
                "id": row["id"],
                "app_id": row["app_id"],
                "title": row["title"],
                "message": row["message"],
                "link": row["link"],
                "is_read": row["is_read"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in result[1]
        ]

    async def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a single notification as read. Returns True if updated."""
        conn = Tortoise.get_connection("default")
        result = await conn.execute_query(
            """
            UPDATE in_app_notifications
            SET is_read = TRUE
            WHERE id = $1 AND user_id = $2
            """,
            [notification_id, user_id],
        )
        return result[0] > 0

    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user. Returns count updated."""
        conn = Tortoise.get_connection("default")
        result = await conn.execute_query(
            """
            UPDATE in_app_notifications
            SET is_read = TRUE
            WHERE user_id = $1 AND is_read = FALSE
            """,
            [user_id],
        )
        return result[0]

    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user."""
        conn = Tortoise.get_connection("default")
        result = await conn.execute_query(
            """
            SELECT COUNT(*) as count
            FROM in_app_notifications
            WHERE user_id = $1 AND is_read = FALSE
            """,
            [user_id],
        )
        return result[1][0]["count"] if result[1] else 0


in_app_notifications = InAppNotificationService()
