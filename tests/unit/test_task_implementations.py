"""Unit tests for task implementations."""

import pytest

from app.tasks.data_tasks import export_data_task, import_data_task
from app.tasks.email_tasks import send_bulk_email_task, send_email_task
from app.tasks.failing_tasks import (
    always_fail_task,
    always_raise_runtime_error_task,
    always_raise_value_error_task,
)
from app.tasks.image_tasks import compress_image_task, resize_image_task


@pytest.mark.asyncio
async def test_send_email_task():
    """Test send_email task can be executed."""
    result = await send_email_task()
    assert result == "Email sent successfully"


@pytest.mark.asyncio
async def test_send_bulk_email_task():
    """Test send_bulk_email task can be executed."""
    result = await send_bulk_email_task()
    assert isinstance(result, dict)
    assert "emails_sent" in result


@pytest.mark.asyncio
async def test_resize_image_task():
    """Test resize_image task can be executed."""
    result = await resize_image_task()
    assert isinstance(result, dict)
    assert "width" in result


@pytest.mark.asyncio
async def test_compress_image_task():
    """Test compress_image task can be executed."""
    result = await compress_image_task()
    assert isinstance(result, dict)
    assert "compressed_size" in result


@pytest.mark.asyncio
async def test_export_data_task():
    """Test export_data task can be executed."""
    result = await export_data_task()
    assert isinstance(result, dict)
    assert "file_path" in result


@pytest.mark.asyncio
async def test_import_data_task():
    """Test import_data task can be executed."""
    result = await import_data_task()
    assert isinstance(result, dict)
    assert "rows_imported" in result


@pytest.mark.asyncio
async def test_always_fail_task():
    """Test that always_fail task raises an exception."""
    with pytest.raises(Exception, match="This task always fails"):
        await always_fail_task()


@pytest.mark.asyncio
async def test_always_raise_value_error_task():
    """Test that always_raise_value_error task raises ValueError."""
    with pytest.raises(ValueError, match="Invalid value provided to task"):
        await always_raise_value_error_task()


@pytest.mark.asyncio
async def test_always_raise_runtime_error_task():
    """Test that always_raise_runtime_error task raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Runtime error occurred in task"):
        await always_raise_runtime_error_task()


