"""Image processing task implementations."""

from app.tasks import TaskName, register_task


@register_task(TaskName.RESIZE_IMAGE)
async def resize_image_task() -> dict:
    """Resize an image."""
    # TODO: Implement actual image resizing logic
    return {"width": 800, "height": 600, "format": "JPEG"}


@register_task(TaskName.COMPRESS_IMAGE)
async def compress_image_task() -> dict:
    """Compress an image."""
    # TODO: Implement actual image compression logic
    return {"original_size": 1024000, "compressed_size": 256000, "ratio": 0.25}


