"""Slack notifications service for sending alerts to Slack channels."""
import httpx
import time
from typing import Optional

from config import settings


class SlackNotificationService:
    """Service for sending Slack notifications via webhook."""

    def is_configured(self) -> bool:
        """Check if Slack webhook URL is configured."""
        return bool(settings.SLACK_WEBHOOK_URL)

    async def send_notification(
        self,
        message: str,
        title: Optional[str] = None,
        color: str = "#6366F1",  # Indigo - Co-Intelligence brand color
    ) -> bool:
        """
        Send a simple notification to Slack.
        
        Args:
            message: The notification message
            title: Optional title for the notification
            color: Hex color for the sidebar (default: indigo)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            print("[SLACK] Webhook URL not configured, skipping notification")
            return False

        try:
            payload = {
                "attachments": [{
                    "color": color,
                    "title": title or "Co-Intelligence Notification",
                    "text": message,
                    "footer": "Co-Intelligence Platform",
                    "ts": int(time.time())
                }]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.SLACK_WEBHOOK_URL,
                    json=payload,
                    timeout=10.0
                )
                if response.status_code == 200:
                    print(f"[SLACK] Notification sent: {title or 'notification'}")
                    return True
                else:
                    print(f"[SLACK] Failed to send notification, status: {response.status_code}")
                    return False
        except Exception as e:
            print(f"[SLACK] Error sending notification: {e}")
            return False

    async def send_rich_notification(
        self,
        title: str,
        fields: dict,
        color: str = "#6366F1",
    ) -> bool:
        """
        Send a rich notification with structured fields.
        
        Args:
            title: Header text for the notification
            fields: Dictionary of field name -> value pairs
            color: Hex color for the sidebar
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            return False

        try:
            # Build Slack block fields
            slack_fields = []
            for key, value in fields.items():
                slack_fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}:*\n{value}"
                })

            payload = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": title}
                    },
                    {
                        "type": "section",
                        "fields": slack_fields
                    }
                ]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.SLACK_WEBHOOK_URL,
                    json=payload,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            print(f"[SLACK] Error sending rich notification: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Convenience methods for common notification types
    # ─────────────────────────────────────────────────────────────────────────

    async def send_barista_order_notification(
        self,
        order_id: int,
        customer: str,
        total: float,
        items_count: int,
    ) -> bool:
        """Send notification for new barista order."""
        return await self.send_notification(
            f"☕ New order placed!\n\n"
            f"*Order ID:* #{order_id}\n"
            f"*Customer:* {customer}\n"
            f"*Total:* ${total:.2f}\n"
            f"*Items:* {items_count}",
            title="Agentic Barista - New Order",
            color="#F59E0B",  # Amber
        )

    async def send_lms_enrollment_notification(
        self,
        course_name: str,
        student: str,
    ) -> bool:
        """Send notification for LMS course enrollment."""
        return await self.send_notification(
            f"🎓 New enrollment!\n\n"
            f"*Course:* {course_name}\n"
            f"*Student:* {student}",
            title="Agentic LMS - New Enrollment",
            color="#10B981",  # Green
        )

    async def send_insurance_claim_notification(
        self,
        claim_id: str,
        policy_holder: str,
        claim_type: str,
    ) -> bool:
        """Send notification for new insurance claim."""
        return await self.send_notification(
            f"🚗 New claim filed!\n\n"
            f"*Claim ID:* {claim_id}\n"
            f"*Policy Holder:* {policy_holder}\n"
            f"*Type:* {claim_type}",
            title="Insurance Claims - New Claim",
            color="#EF4444",  # Red
        )

    async def send_fine_tuning_complete_notification(
        self,
        run_id: str,
        model_name: str,
        status: str,
    ) -> bool:
        """Send notification for fine-tuning job completion."""
        color = "#10B981" if status == "completed" else "#EF4444"
        emoji = "✅" if status == "completed" else "❌"
        return await self.send_notification(
            f"{emoji} Fine-tuning job {status}!\n\n"
            f"*Run ID:* {run_id}\n"
            f"*Model:* {model_name}\n"
            f"*Status:* {status}",
            title="LLMs Fine-Tuning - Job Update",
            color=color,
        )

    async def send_data_analysis_complete_notification(
        self,
        run_id: str,
        source_type: str,
        status: str,
    ) -> bool:
        """Send notification for data analysis pipeline completion."""
        color = "#10B981" if status == "completed" else "#EF4444"
        emoji = "📊" if status == "completed" else "❌"
        return await self.send_notification(
            f"{emoji} Data analysis pipeline {status}!\n\n"
            f"*Run ID:* {run_id}\n"
            f"*Source:* {source_type}\n"
            f"*Status:* {status}",
            title="Data Analysis - Pipeline Update",
            color=color,
        )

    async def send_error_notification(
        self,
        error_type: str,
        error_message: str,
        app_id: Optional[str] = None,
    ) -> bool:
        """Send notification for system errors."""
        app_info = f"\n*App:* {app_id}" if app_id else ""
        return await self.send_notification(
            f"⚠️ System error occurred!{app_info}\n\n"
            f"*Type:* {error_type}\n"
            f"*Message:* {error_message}",
            title="System Error",
            color="#EF4444",  # Red
        )


# Singleton instance
slack_notifications = SlackNotificationService()
