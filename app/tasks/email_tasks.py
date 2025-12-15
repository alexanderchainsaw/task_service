"""Email-related task implementations."""

from app.tasks import TaskName, register_task


@register_task(TaskName.SEND_EMAIL)
async def send_email_task() -> str:
    """Send a single email."""
    # TODO: Implement actual email sending logic
    return "Email sent successfully"


@register_task(TaskName.SEND_BULK_EMAIL)
async def send_bulk_email_task() -> dict:
    """Send bulk emails."""
    # TODO: Implement actual bulk email sending logic
    return {"emails_sent": 100, "status": "completed"}
