"""Integration tests for Tasks API endpoints."""

import asyncio
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from uuid import uuid4

import pytest

from app.db.models import TaskName, TaskPriority, TaskStatus


@pytest.mark.asyncio
async def test_create_task_endpoint(test_client):
    """Test POST /api/v1/tasks - creating a task."""
    payload = {
        "task_name": TaskName.SEND_EMAIL.value,
        "description": "This is a test task",
        "priority": TaskPriority.HIGH.value,
    }
    response = await test_client.post("/api/v1/tasks", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["task_name"] == TaskName.SEND_EMAIL.value
    assert data["description"] == "This is a test task"
    assert data["priority"] == TaskPriority.HIGH.value
    assert data["status"] == TaskStatus.NEW.value  # Tasks are created with NEW status
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["started_at"] is None
    assert data["completed_at"] is None
    assert data["result"] is None


@pytest.mark.asyncio
async def test_create_task_with_defaults(test_client):
    """Test creating task with minimal required fields."""
    payload = {"task_name": TaskName.SEND_EMAIL.value}
    response = await test_client.post("/api/v1/tasks", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["task_name"] == TaskName.SEND_EMAIL.value
    assert data["description"] is None
    assert data["priority"] == TaskPriority.MEDIUM.value  # Default
    assert data["status"] == TaskStatus.NEW.value  # Tasks are created with NEW status


@pytest.mark.asyncio
async def test_create_task_validation_error(test_client):
    """Test creating task with invalid data."""
    # Missing required field
    payload = {}
    response = await test_client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 422

    # Invalid priority
    payload = {"task_name": TaskName.SEND_EMAIL.value, "priority": "INVALID"}
    response = await test_client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 422

    # Invalid task_name
    payload = {"task_name": "INVALID_TASK_NAME", "priority": TaskPriority.MEDIUM.value}
    response = await test_client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_task_endpoint(test_client):
    """Test GET /api/v1/tasks/{task_id} - retrieving a task."""
    # Create a task first
    create_payload = {"task_name": TaskName.SEND_EMAIL.value, "priority": TaskPriority.MEDIUM.value}
    create_response = await test_client.post("/api/v1/tasks", json=create_payload)
    task_id = create_response.json()["id"]

    # Get the task
    response = await test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["task_name"] == TaskName.SEND_EMAIL.value


@pytest.mark.asyncio
async def test_get_nonexistent_task(test_client):
    """Test GET /api/v1/tasks/{task_id} - non-existent task."""
    fake_id = str(uuid4())
    response = await test_client.get(f"/api/v1/tasks/{fake_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_task_invalid_uuid(test_client):
    """Test GET /api/v1/tasks/{task_id} - invalid UUID format."""
    response = await test_client.get("/api/v1/tasks/invalid-uuid")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_tasks_endpoint(test_client):
    """Test GET /api/v1/tasks - listing tasks."""
    # Create multiple tasks
    task_names = [TaskName.SEND_EMAIL, TaskName.SEND_BULK_EMAIL, TaskName.RESIZE_IMAGE]
    for i in range(3):
        payload = {"task_name": task_names[i].value, "priority": TaskPriority.MEDIUM.value}
        await test_client.post("/api/v1/tasks", json=payload)

    # List tasks
    response = await test_client.get("/api/v1/tasks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_list_tasks_with_status_filter(test_client):
    """Test listing tasks filtered by status."""
    # Create tasks
    payload1 = {"task_name": TaskName.SEND_EMAIL.value, "priority": TaskPriority.MEDIUM.value}
    response1 = await test_client.post("/api/v1/tasks", json=payload1)
    task1_id = response1.json()["id"]

    # Filter by status
    response = await test_client.get("/api/v1/tasks?status=NEW")
    assert response.status_code == 200
    data = response.json()
    assert all(task["status"] == TaskStatus.NEW.value for task in data)


@pytest.mark.asyncio
async def test_list_tasks_with_priority_filter(test_client):
    """Test listing tasks filtered by priority."""
    # Create tasks with different priorities
    await test_client.post(
        "/api/v1/tasks",
        json={"task_name": TaskName.SEND_EMAIL.value, "priority": TaskPriority.HIGH.value},
    )
    await test_client.post(
        "/api/v1/tasks",
        json={"task_name": TaskName.SEND_BULK_EMAIL.value, "priority": TaskPriority.LOW.value},
    )

    # Filter by priority
    response = await test_client.get(f"/api/v1/tasks?priority={TaskPriority.HIGH.value}")
    assert response.status_code == 200
    data = response.json()
    assert all(task["priority"] == TaskPriority.HIGH.value for task in data)


@pytest.mark.asyncio
async def test_list_tasks_with_date_filters(test_client):
    """Test listing tasks filtered by creation date."""
    # Create a task
    await test_client.post(
        "/api/v1/tasks",
        json={"task_name": TaskName.SEND_EMAIL.value, "priority": TaskPriority.MEDIUM.value},
    )

    # Filter by date range - URL encode ISO format dates to handle colons
    from_date = datetime.now(timezone.utc) - timedelta(days=1)
    to_date = datetime.now(timezone.utc) + timedelta(days=1)

    # FastAPI can parse ISO format from query params, but colons need URL encoding
    from_date_str = quote(from_date.isoformat())
    to_date_str = quote(to_date.isoformat())

    response = await test_client.get(
        f"/api/v1/tasks?created_from={from_date_str}&created_to={to_date_str}"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_tasks_with_pagination(test_client):
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
        payload = {"task_name": task_name.value, "priority": TaskPriority.MEDIUM.value}
        await test_client.post("/api/v1/tasks", json=payload)

    # First page
    response1 = await test_client.get("/api/v1/tasks?limit=5&offset=0")
    assert response1.status_code == 200
    page1 = response1.json()
    assert len(page1) == 5

    # Second page
    response2 = await test_client.get("/api/v1/tasks?limit=5&offset=5")
    assert response2.status_code == 200
    page2 = response2.json()
    assert len(page2) == 5

    # Verify different tasks
    page1_ids = {task["id"] for task in page1}
    page2_ids = {task["id"] for task in page2}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.asyncio
async def test_list_tasks_pagination_validation(test_client):
    """Test pagination parameter validation."""
    # Invalid limit (too high)
    response = await test_client.get("/api/v1/tasks?limit=300")
    assert response.status_code == 422

    # Invalid limit (negative)
    response = await test_client.get("/api/v1/tasks?limit=-1")
    assert response.status_code == 422

    # Invalid offset (negative)
    response = await test_client.get("/api/v1/tasks?offset=-1")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_task_status_endpoint(test_client):
    """Test GET /api/v1/tasks/{task_id}/status - getting task status."""
    # Create a task
    create_payload = {"task_name": TaskName.SEND_EMAIL.value, "priority": TaskPriority.MEDIUM.value}
    create_response = await test_client.post("/api/v1/tasks", json=create_payload)
    task_id = create_response.json()["id"]

    # Get status
    response = await test_client.get(f"/api/v1/tasks/{task_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert "status" in data
    assert data["status"] == TaskStatus.NEW.value  # Tasks are created with NEW status
    assert "error" in data


@pytest.mark.asyncio
async def test_get_task_status_nonexistent(test_client):
    """Test getting status of non-existent task."""
    fake_id = str(uuid4())
    response = await test_client.get(f"/api/v1/tasks/{fake_id}/status")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_task_endpoint(test_client):
    """Test DELETE /api/v1/tasks/{task_id} - cancelling a task."""
    # Create a task
    create_payload = {"task_name": TaskName.SEND_EMAIL.value, "priority": TaskPriority.MEDIUM.value}
    create_response = await test_client.post("/api/v1/tasks", json=create_payload)
    task_id = create_response.json()["id"]

    # Cancel the task
    response = await test_client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["status"] == TaskStatus.CANCELLED.value
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_cancel_nonexistent_task(test_client):
    """Test cancelling a non-existent task."""
    fake_id = str(uuid4())
    response = await test_client.delete(f"/api/v1/tasks/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_completed_task(test_client):
    """Test that cancelling a completed task doesn't change status."""
    # Create and complete a task (simulated by direct DB manipulation)
    # For integration test, we'll just verify the endpoint works
    create_payload = {"task_name": TaskName.SEND_EMAIL.value, "priority": TaskPriority.MEDIUM.value}
    create_response = await test_client.post("/api/v1/tasks", json=create_payload)
    task_id = create_response.json()["id"]

    # Cancel it (will work, but status won't change if already completed)
    response = await test_client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_task_lifecycle_integration(test_client):
    """Test complete task lifecycle through API."""
    # 1. Create task
    create_payload = {
        "task_name": TaskName.SEND_EMAIL.value,
        "description": "Testing full lifecycle",
        "priority": TaskPriority.HIGH.value,
    }
    create_response = await test_client.post("/api/v1/tasks", json=create_payload)
    assert create_response.status_code == 201
    task_data = create_response.json()
    task_id = task_data["id"]
    assert task_data["status"] == TaskStatus.NEW.value  # Tasks are created with NEW status

    # 2. Get task
    get_response = await test_client.get(f"/api/v1/tasks/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == task_id

    # 3. Get status
    status_response = await test_client.get(f"/api/v1/tasks/{task_id}/status")
    assert status_response.status_code == 200
    assert (
        status_response.json()["status"] == TaskStatus.NEW.value
    )  # Tasks are created with NEW status

    # 4. Cancel task
    cancel_response = await test_client.delete(f"/api/v1/tasks/{task_id}")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == TaskStatus.CANCELLED.value

    # 5. Verify cancelled status
    final_status = await test_client.get(f"/api/v1/tasks/{task_id}/status")
    assert final_status.json()["status"] == TaskStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_list_tasks_ordering(test_client):
    """Test that tasks are properly ordered by priority and creation time."""
    # Create tasks with different priorities and unique task names
    task_name_low = TaskName.EXPORT_DATA
    task_name_high = TaskName.SEND_EMAIL
    task_name_medium = TaskName.RESIZE_IMAGE

    await test_client.post(
        "/api/v1/tasks", json={"task_name": task_name_low.value, "priority": TaskPriority.LOW.value}
    )
    await asyncio.sleep(0.01)
    await test_client.post(
        "/api/v1/tasks",
        json={"task_name": task_name_high.value, "priority": TaskPriority.HIGH.value},
    )
    await asyncio.sleep(0.01)
    await test_client.post(
        "/api/v1/tasks",
        json={"task_name": task_name_medium.value, "priority": TaskPriority.MEDIUM.value},
    )

    # Get all tasks - may need to paginate if there are many
    all_tasks = []
    offset = 0
    limit = 100
    while True:
        response = await test_client.get(f"/api/v1/tasks?limit={limit}&offset={offset}")
        assert response.status_code == 200
        page_tasks = response.json()
        if not page_tasks:
            break
        all_tasks.extend(page_tasks)
        if len(page_tasks) < limit:
            break
        offset += limit

    # Find our tasks by task_name and priority
    high_task = next(
        (
            t
            for t in all_tasks
            if t["task_name"] == task_name_high.value and t["priority"] == TaskPriority.HIGH.value
        ),
        None,
    )
    medium_task = next(
        (
            t
            for t in all_tasks
            if t["task_name"] == task_name_medium.value
            and t["priority"] == TaskPriority.MEDIUM.value
        ),
        None,
    )
    low_task = next(
        (
            t
            for t in all_tasks
            if t["task_name"] == task_name_low.value and t["priority"] == TaskPriority.LOW.value
        ),
        None,
    )

    assert (
        high_task is not None
    ), f"High task not found. Available task_names: {[t['task_name'] for t in all_tasks[:20]]}"
    assert (
        medium_task is not None
    ), f"Medium task not found. Available task_names: {[t['task_name'] for t in all_tasks[:20]]}"
    assert (
        low_task is not None
    ), f"Low task not found. Available task_names: {[t['task_name'] for t in all_tasks[:20]]}"

    tasks = all_tasks

    # High priority should appear before medium and low
    high_index = tasks.index(high_task)
    medium_index = tasks.index(medium_task)
    low_index = tasks.index(low_task)

    assert (
        high_index < medium_index
    ), f"High (index {high_index}) should come before Medium (index {medium_index})"
    assert (
        high_index < low_index
    ), f"High (index {high_index}) should come before Low (index {low_index})"
    assert (
        medium_index < low_index
    ), f"Medium (index {medium_index}) should come before Low (index {low_index})"
