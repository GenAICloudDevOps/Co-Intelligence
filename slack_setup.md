# Slack Notifications Setup Guide

Co-Intelligence supports sending real-time notifications to a Slack channel for key events across its various applications.

## Prerequisites

- A Slack Workspace where you have permissions to add apps/integrations.
- Access to the Co-Intelligence backend configuration (specifically `.env`).

## Step 1: Create a Slack Webhook

**⚠️ IMPORTANT:** You cannot do this inside the Slack Chat App (where you see Home, DMs, Activity). You must go to the **Developer Website** in your browser.

1.  Open your web browser and go to: **[https://api.slack.com/apps](https://api.slack.com/apps)**
    - You might need to sign in with your Slack credentials again.
2.  Click the button **Create New App**.
3.  Choose **From scratch**.
4.  Name App: "Co-Intelligence" (or similar).
5.  Select Workspace: Choose your team's workspace.
6.  Click **Create App**.

**Now you will see the "Basic Information" page (white dashboard).**

7.  Look at the **Left Sidebar** of this webpage (it has a dark gray background).
8.  Find the **Features** heading.
9.  Click **Incoming Webhooks**.
10. Toggle the switch to **On**.
11. Click **Add New Webhook to Workspace** (at the bottom).
12. Select your channel and authorize.
13. Copy the URL.

## Step 2: Configure Backend

1.  Open your backend `.env` file (located in `co-intelligence/`).
2.  Add the `SLACK_WEBHOOK_URL` variable:

    ```ini
    SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL_HERE
    ```

3.  Restart your backend service to apply the changes.

## Step 3: Enable Notifications

Notifications are valid per-app and are **opt-in** by default.

1.  Log in to the Co-Intelligence web application.
2.  Click your user avatar/profile menu in the top right.
3.  You will see the **Per-App Settings** panel on the left.
4.  Find the app you want alerts for (e.g., "Agentic Barista" or "Insurance Claims").
5.  Check the box under the **Slack** column.

## Troubleshooting

- **Notifications not arriving?**
    - Check the backend logs for `[SLACK]` messages.
    - Ensure your `.env` file is loaded correctly.
    - Verify `slack_enabled` is set to `true` for your user/app in the database.
    - Manually test using the Python shell:
      ```bash
      cd backend
      python -c "import asyncio; from services.slack_notifications import slack_notifications; asyncio.run(slack_notifications.send_notification('Test message'))"
      ```

- **Missing "Slack" column in UI?**
    - Ensure you have pulled the latest frontend code.
    - Hard refresh your browser to clear cache.
