"""Per-app notification preferences service."""
from tortoise import Tortoise
from auth.models import User


# Apps that support notifications (must match frontend app IDs)
NOTIFIABLE_APPS = [
    "agentic-barista",
    "agentic-lms",
    "insurance-claims",
    "llms-fine-tuning",
    "data-analysis",
]


class NotificationPrefsService:
    """Service for managing per-app notification preferences."""

    async def get_user_prefs(self, user_id: int) -> dict[str, dict]:
        """
        Get all notification preferences for a user.
        Returns dict: {app_id: {email_enabled: bool, in_app_enabled: bool}}
        Apps without preferences default to False (explicit opt-in required).
        """
        conn = Tortoise.get_connection("default")
        result = await conn.execute_query(
            """
            SELECT app_id, email_enabled, in_app_enabled
            FROM user_app_notification_prefs
            WHERE user_id = $1
            """,
            [user_id],
        )
        prefs = {}
        for row in result[1]:
            prefs[row["app_id"]] = {
                "email_enabled": row["email_enabled"],
                "in_app_enabled": row["in_app_enabled"],
            }
        # Fill in defaults for apps without preferences
        for app_id in NOTIFIABLE_APPS:
            if app_id not in prefs:
                prefs[app_id] = {"email_enabled": False, "in_app_enabled": False}
        return prefs

    async def update_user_pref(
        self,
        user_id: int,
        app_id: str,
        email_enabled: bool,
        in_app_enabled: bool,
    ) -> None:
        """Update or create a preference for a specific app."""
        conn = Tortoise.get_connection("default")
        await conn.execute_query(
            """
            INSERT INTO user_app_notification_prefs (user_id, app_id, email_enabled, in_app_enabled, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (user_id, app_id)
            DO UPDATE SET email_enabled = $3, in_app_enabled = $4
            """,
            [user_id, app_id, email_enabled, in_app_enabled],
        )

    async def should_send_email(self, user_id: int, app_id: str) -> bool:
        """
        Check if email notification should be sent.
        Returns True only if:
        1. User's global email_notifications_enabled is True (master switch)
        2. User's per-app email_enabled is True
        """
        # Check global master switch
        user = await User.get_or_none(id=user_id)
        if not user or not user.email_notifications_enabled or not user.email:
            return False

        # Check per-app preference
        conn = Tortoise.get_connection("default")
        result = await conn.execute_query(
            """
            SELECT email_enabled FROM user_app_notification_prefs
            WHERE user_id = $1 AND app_id = $2
            """,
            [user_id, app_id],
        )
        if not result[1]:
            return False  # No preference means not opted in
        return result[1][0]["email_enabled"]

    async def should_send_in_app(self, user_id: int, app_id: str) -> bool:
        """
        Check if in-app notification should be sent.
        Returns True only if user's per-app in_app_enabled is True.
        (In-app notifications are independent of global email toggle)
        """
        conn = Tortoise.get_connection("default")
        result = await conn.execute_query(
            """
            SELECT in_app_enabled FROM user_app_notification_prefs
            WHERE user_id = $1 AND app_id = $2
            """,
            [user_id, app_id],
        )
        if not result[1]:
            return False  # No preference means not opted in
        return result[1][0]["in_app_enabled"]


notification_prefs = NotificationPrefsService()
