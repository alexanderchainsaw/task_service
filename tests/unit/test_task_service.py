"""Unit tests for TaskService."""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.api.models import PaginationParams
from app.db.models import Task, TaskName, TaskPriority, TaskStatus
from app.db.repository import TaskRepository
from app.db.schemas import TaskCreate


@pytest.mark.asyncio
async def test_create_task(task_service, mock_publisher):
    """Test creating a new task."""
    payload = TaskCreate(
        task_name=TaskName.SEND_EMAIL,
        description="Test Description",
        priority=TaskPriority.HIGH,
    )
    task = await task_service.create(payload)

    assert task.id is not None
    assert task.task_name == TaskName.SEND_EMAIL
    assert task.description == "Test Description"
    assert task.priority == TaskPriority.HIGH
    assert (
        task.status == TaskStatus.NEW
    )  # Tasks are created with NEW status, publishing is handled by workers
    assert task.created_at is not None

    # Publishing is now handled by a separate workers, so no queue interaction here


@pytest.mark.asyncio
async def test_create_task_with_default_priority(task_service, mock_publisher):
    """Test creating task with default priority."""
    payload = TaskCreate(task_name=TaskName.SEND_EMAIL)
    task = await task_service.create(payload)

    assert task.priority == TaskPriority.MEDIUM
    assert task.status == TaskStatus.NEW  # Tasks are created with NEW status
    # Publishing is now handled by a separate workers, so no queue interaction here


@pytest.mark.asyncio
async def test_get_task(task_service, mock_publisher):
    """Test retrieving a task by ID."""
    payload = TaskCreate(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.LOW)
    created_task = await task_service.create(payload)

    retrieved_task = await task_service.get(created_task.id)
    assert retrieved_task is not None
    assert retrieved_task.id == created_task.id
    assert retrieved_task.task_name == TaskName.SEND_EMAIL


@pytest.mark.asyncio
async def test_get_nonexistent_task(task_service):
    """Test retrieving a non-existent task."""
    task = await task_service.get(uuid4())
    assert task is None


@pytest.mark.asyncio
async def test_list_tasks_no_filters(task_service, mock_publisher):
    """Test listing tasks without filters."""
    # Create multiple tasks and track their IDs
    created_task_ids = []
    task_names = [
        TaskName.SEND_EMAIL,
        TaskName.SEND_BULK_EMAIL,
        TaskName.RESIZE_IMAGE,
        TaskName.COMPRESS_IMAGE,
        TaskName.EXPORT_DATA,
    ]
    for task_name in task_names:
        payload = TaskCreate(task_name=task_name, priority=TaskPriority.MEDIUM)
        task = await task_service.create(payload)
        created_task_ids.append(task.id)

    # Use a large pagination limit to ensure we get all tasks (including from other tests)
    pagination = PaginationParams(limit=100, offset=0)
    tasks = await task_service.list(pagination=pagination)
    task_list = list(tasks)
    # Check that our created tasks are in the list by ID
    task_ids_list = [t.id for t in task_list]
    for task_id in created_task_ids:
        assert task_id in task_ids_list, f"Task ID '{task_id}' not found in list"
    # Verify we found exactly the 5 tasks we created
    found_tasks = [t for t in task_list if t.id in created_task_ids]
    assert len(found_tasks) == 5


@pytest.mark.asyncio
async def test_list_tasks_with_status_filter(task_service, task_repository, mock_publisher):
    """Test listing tasks filtered by status."""
    # Create tasks with different statuses
    payload1 = TaskCreate(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task1 = await task_service.create(payload1)  # Will be NEW

    payload2 = TaskCreate(task_name=TaskName.SEND_BULK_EMAIL, priority=TaskPriority.MEDIUM)
    task2 = await task_service.create(payload2)  # Will be NEW
    task2.mark_completed()
    await task_repository.update(task2)

    # Filter by NEW
    new_tasks = await task_service.list(status=TaskStatus.NEW)
    new_list = list(new_tasks)
    assert len(new_list) >= 1
    assert all(t.status == TaskStatus.NEW for t in new_list)

    # Filter by COMPLETED
    completed_tasks = await task_service.list(status=TaskStatus.COMPLETED)
    completed_list = list(completed_tasks)
    assert len(completed_list) >= 1
    assert all(t.status == TaskStatus.COMPLETED for t in completed_list)


@pytest.mark.asyncio
async def test_list_tasks_with_priority_filter(task_service, mock_publisher):
    """Test listing tasks filtered by priority."""
    # Create tasks with different priorities
    await task_service.create(TaskCreate(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.HIGH))
    await task_service.create(
        TaskCreate(task_name=TaskName.SEND_BULK_EMAIL, priority=TaskPriority.MEDIUM)
    )
    await task_service.create(
        TaskCreate(task_name=TaskName.RESIZE_IMAGE, priority=TaskPriority.LOW)
    )

    high_tasks = await task_service.list(priority=TaskPriority.HIGH)
    high_list = list(high_tasks)
    assert len(high_list) >= 1
    assert all(t.priority == TaskPriority.HIGH for t in high_list)


@pytest.mark.asyncio
async def test_list_tasks_with_date_filters(task_service, mock_publisher):
    """Test listing tasks filtered by creation date."""
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    # Create a task
    await task_service.create(
        TaskCreate(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    )

    # Filter by date range
    recent_tasks = await task_service.list(created_from=yesterday, created_to=tomorrow)
    recent_list = list(recent_tasks)
    assert len(recent_list) >= 1


@pytest.mark.asyncio
async def test_list_tasks_with_pagination(task_service, mock_publisher):
    """Test listing tasks with pagination."""
    # Create 10 tasks
    task_names = [
        TaskName.SEND_EMAIL,
        TaskName.SEND_BULK_EMAIL,
        TaskName.RESIZE_IMAGE,
        TaskName.COMPRESS_IMAGE,
        TaskName.EXPORT_DATA,
        TaskName.IMPORT_DATA,
    ]
    for i in range(10):
        task_name = task_names[i % len(task_names)]
        await task_service.create(TaskCreate(task_name=task_name, priority=TaskPriority.MEDIUM))

    # First page
    pagination = PaginationParams(limit=5, offset=0)
    page1 = await task_service.list(pagination=pagination)
    page1_list = list(page1)
    assert len(page1_list) == 5

    # Second page
    pagination = PaginationParams(limit=5, offset=5)
    page2 = await task_service.list(pagination=pagination)
    page2_list = list(page2)
    assert len(page2_list) == 5

    # Verify different tasks
    page1_ids = {t.id for t in page1_list}
    page2_ids = {t.id for t in page2_list}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.asyncio
async def test_list_tasks_ordering(task_service, task_repository, mock_publisher):
    """Test that tasks are ordered by priority (desc) and created_at (asc)."""
    # Create tasks with different priorities and unique task names to avoid conflicts
    low_task = await task_service.create(
        TaskCreate(task_name=TaskName.EXPORT_DATA, priority=TaskPriority.LOW)
    )
    await task_repository.update(low_task)  # Ensure it's committed
    await asyncio.sleep(0.01)  # Small delay to ensure different timestamps

    high_task = await task_service.create(
        TaskCreate(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.HIGH)
    )
    await task_repository.update(high_task)  # Ensure it's committed
    await asyncio.sleep(0.01)

    medium_task = await task_service.create(
        TaskCreate(task_name=TaskName.RESIZE_IMAGE, priority=TaskPriority.MEDIUM)
    )
    await task_repository.update(medium_task)  # Ensure it's committed

    # Use a large pagination limit to ensure we get all tasks (including from other tests)
    pagination = PaginationParams(limit=100, offset=0)
    tasks = await task_service.list(pagination=pagination)
    task_list = list(tasks)

    # Find our specific tasks in the list
    low_found = next(
        (
            t
            for t in task_list
            if t.task_name == TaskName.EXPORT_DATA and t.priority == TaskPriority.LOW
        ),
        None,
    )
    high_found = next(
        (
            t
            for t in task_list
            if t.task_name == TaskName.SEND_EMAIL and t.priority == TaskPriority.HIGH
        ),
        None,
    )
    medium_found = next(
        (
            t
            for t in task_list
            if t.task_name == TaskName.RESIZE_IMAGE and t.priority == TaskPriority.MEDIUM
        ),
        None,
    )

    assert (
        low_found is not None
    ), f"Low task not found. Available: {[t.task_name for t in task_list[:10]]}"
    assert (
        high_found is not None
    ), f"High task not found. Available: {[t.task_name for t in task_list[:10]]}"
    assert (
        medium_found is not None
    ), f"Medium task not found. Available: {[t.task_name for t in task_list[:10]]}"

    # Get indices
    low_idx = task_list.index(low_found)
    high_idx = task_list.index(high_found)
    medium_idx = task_list.index(medium_found)

    # High priority should come before medium and low
    assert high_idx < medium_idx
    assert high_idx < low_idx
    # Medium should come before low
    assert medium_idx < low_idx


@pytest.mark.asyncio
async def test_cancel_new_task(task_service, mock_publisher):
    """Test cancelling a new task."""
    payload = TaskCreate(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task = await task_service.create(payload)
    assert task.status == TaskStatus.NEW

    cancelled_task = await task_service.cancel(task)
    assert cancelled_task.status == TaskStatus.CANCELLED
    assert cancelled_task.completed_at is not None


@pytest.mark.asyncio
async def test_cancel_in_progress_task(task_service, task_repository, mock_publisher):
    """Test cancelling an in-progress task."""
    payload = TaskCreate(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task = await task_service.create(payload)
    task.mark_in_progress()
    await task_repository.update(task)

    cancelled_task = await task_service.cancel(task)
    assert cancelled_task.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_completed_task(task_service, task_repository, mock_publisher):
    """Test that cancelling a completed task has no effect."""
    payload = TaskCreate(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task = await task_service.create(payload)
    task.mark_completed()
    await task_repository.update(task)

    original_status = task.status
    cancelled_task = await task_service.cancel(task)
    assert cancelled_task.status == original_status  # Should not change


@pytest.mark.asyncio
async def test_cancel_failed_task(task_service, task_repository, mock_publisher):
    """Test that cancelling a failed task has no effect."""
    payload = TaskCreate(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task = await task_service.create(payload)
    task.mark_failed(error="Test error")
    await task_repository.update(task)

    original_status = task.status
    cancelled_task = await task_service.cancel(task)
    assert cancelled_task.status == original_status  # Should not change


@pytest.mark.asyncio
async def test_cancel_cancelled_task(task_service, task_repository, mock_publisher):
    """Test that cancelling an already cancelled task has no effect."""
    payload = TaskCreate(task_name=TaskName.SEND_EMAIL, priority=TaskPriority.MEDIUM)
    task = await task_service.create(payload)
    task.mark_cancelled()
    await task_repository.update(task)

    original_status = task.status
    cancelled_task = await task_service.cancel(task)
    assert cancelled_task.status == original_status  # Should not change
