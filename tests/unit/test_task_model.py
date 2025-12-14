"""Unit tests for Task model."""
from datetime import datetime, timezone

import pytest

from app.db.models import Task, TaskName, TaskPriority, TaskStatus
from tests.conftest import create_task


@pytest.mark.asyncio
async def test_task_initial_state():
    """Test that a new task has correct initial state."""
    task = create_task(
        task_name=TaskName.SEND_EMAIL,
        description="Test Description",
        priority=TaskPriority.HIGH,
    )
    assert task.task_name == TaskName.SEND_EMAIL
    assert task.description == "Test Description"
    assert task.priority == TaskPriority.HIGH
    assert task.status == TaskStatus.NEW
    assert task.result is None
    assert task.error is None
    assert task.created_at is not None
    assert task.started_at is None
    assert task.completed_at is None


@pytest.mark.asyncio
async def test_task_mark_pending():
    """Test marking task as pending."""
    task = create_task(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task.mark_pending()
    assert task.status == TaskStatus.PENDING
    assert task.started_at is None
    assert task.completed_at is None


@pytest.mark.asyncio
async def test_task_mark_in_progress():
    """Test marking task as in progress."""
    task = create_task(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    before = datetime.now(timezone.utc)
    task.mark_in_progress()
    after = datetime.now(timezone.utc)
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.started_at is not None
    assert before <= task.started_at <= after
    assert task.completed_at is None


@pytest.mark.asyncio
async def test_task_mark_completed():
    """Test marking task as completed."""
    task = create_task(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task.mark_in_progress()
    before = datetime.now(timezone.utc)
    task.mark_completed(result="Task completed successfully")
    after = datetime.now(timezone.utc)
    assert task.status == TaskStatus.COMPLETED
    assert task.result == "Task completed successfully"
    assert task.completed_at is not None
    assert before <= task.completed_at <= after


@pytest.mark.asyncio
async def test_task_mark_completed_without_result():
    """Test marking task as completed without result."""
    task = create_task(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task.mark_completed()
    assert task.status == TaskStatus.COMPLETED
    assert task.result is None
    assert task.completed_at is not None


@pytest.mark.asyncio
async def test_task_mark_failed():
    """Test marking task as failed."""
    task = create_task(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task.mark_in_progress()
    error_msg = "Something went wrong"
    before = datetime.now(timezone.utc)
    task.mark_failed(error=error_msg)
    after = datetime.now(timezone.utc)
    assert task.status == TaskStatus.FAILED
    assert task.error == error_msg
    assert task.completed_at is not None
    assert before <= task.completed_at <= after


@pytest.mark.asyncio
async def test_task_mark_cancelled():
    """Test marking task as cancelled."""
    task = create_task(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task.mark_pending()
    before = datetime.now(timezone.utc)
    task.mark_cancelled()
    after = datetime.now(timezone.utc)
    assert task.status == TaskStatus.CANCELLED
    assert task.completed_at is not None
    assert before <= task.completed_at <= after


@pytest.mark.asyncio
async def test_task_status_transitions():
    """Test valid status transitions."""
    task = create_task(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    assert task.status == TaskStatus.NEW

    task.mark_pending()
    assert task.status == TaskStatus.PENDING

    task.mark_in_progress()
    assert task.status == TaskStatus.IN_PROGRESS

    task.mark_completed()
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_task_cancellation_from_pending():
    """Test cancelling task from pending state."""
    task = create_task(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task.mark_pending()
    task.mark_cancelled()
    assert task.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_task_cancellation_from_in_progress():
    """Test cancelling task from in_progress state."""
    task = create_task(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task.mark_pending()
    task.mark_in_progress()
    task.mark_cancelled()
    assert task.status == TaskStatus.CANCELLED

