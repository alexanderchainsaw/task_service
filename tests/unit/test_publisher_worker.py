"""Unit tests for TaskPublisherWorker."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import Task, TaskName, TaskPriority, TaskStatus
from app.workers.publisher import TaskPublisherWorker, _priority_to_int


def test_priority_to_int():
    """Test priority conversion to integer."""
    assert _priority_to_int(TaskPriority.HIGH) == 9
    assert _priority_to_int(TaskPriority.MEDIUM) == 5
    assert _priority_to_int(TaskPriority.LOW) == 1


@pytest.mark.asyncio
async def test_process_new_tasks_no_tasks():
    """Test processing when there are no new tasks."""
    worker = TaskPublisherWorker()

    # Mock session as async context manager
    mock_session = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_session_context)
    worker._session_factory = mock_session_factory

    mock_repository = AsyncMock()
    mock_repository.fetch_new_tasks_for_publishing = AsyncMock(return_value=[])

    with patch("app.workers.publisher.TaskRepository", return_value=mock_repository):
        count = await worker.process_new_tasks(batch_size=10)
        assert count == 0


@pytest.mark.asyncio
async def test_process_new_tasks_success():
    """Test successfully processing and publishing new tasks."""
    worker = TaskPublisherWorker()

    # Create test tasks
    task1 = Task(
        id=None,
        task_name=TaskName.SEND_EMAIL,
        priority=TaskPriority.HIGH,
        status=TaskStatus.NEW,
    )
    task2 = Task(
        id=None,
        task_name=TaskName.SEND_BULK_EMAIL,
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.NEW,
    )

    # Mock session as async context manager
    mock_session = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_session_context)
    worker._session_factory = mock_session_factory

    mock_repository = AsyncMock()
    mock_repository.fetch_new_tasks_for_publishing = AsyncMock(return_value=[task1, task2])
    mock_repository.update = AsyncMock()

    mock_rabbitmq_client = AsyncMock()

    with patch("app.workers.publisher.TaskRepository", return_value=mock_repository):
        with patch("app.workers.publisher.rabbitmq_client", mock_rabbitmq_client):
            count = await worker.process_new_tasks(batch_size=10)
            assert count == 2

            # Verify tasks were published
            assert mock_rabbitmq_client.publish.call_count == 2
            # Verify tasks were marked as pending
            assert task1.status == TaskStatus.PENDING
            assert task2.status == TaskStatus.PENDING
            # Verify tasks were updated
            assert mock_repository.update.call_count == 2
            # Verify session was committed
            assert mock_session.commit.call_count == 2


@pytest.mark.asyncio
async def test_process_new_tasks_publish_error():
    """Test handling publish errors with rollback."""
    worker = TaskPublisherWorker()

    # Create test task
    task = Task(
        id=None,
        task_name=TaskName.SEND_EMAIL,
        priority=TaskPriority.HIGH,
        status=TaskStatus.NEW,
    )

    # Mock session as async context manager
    mock_session = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_session_context)
    worker._session_factory = mock_session_factory

    mock_repository = AsyncMock()
    mock_repository.fetch_new_tasks_for_publishing = AsyncMock(return_value=[task])

    mock_rabbitmq_client = AsyncMock()
    mock_rabbitmq_client.publish = AsyncMock(side_effect=Exception("Publish failed"))

    with patch("app.workers.publisher.TaskRepository", return_value=mock_repository):
        with patch("app.workers.publisher.rabbitmq_client", mock_rabbitmq_client):
            count = await worker.process_new_tasks(batch_size=10)
            assert count == 0  # No tasks published due to error

            # Verify task status didn't change
            assert task.status == TaskStatus.NEW
            # Verify rollback was called
            mock_session.rollback.assert_called()


@pytest.mark.asyncio
async def test_process_new_tasks_partial_failure():
    """Test handling when some tasks publish successfully and others fail."""
    worker = TaskPublisherWorker()

    # Create test tasks
    task1 = Task(
        id=None,
        task_name=TaskName.SEND_EMAIL,
        priority=TaskPriority.HIGH,
        status=TaskStatus.NEW,
    )
    task2 = Task(
        id=None,
        task_name=TaskName.SEND_BULK_EMAIL,
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.NEW,
    )

    # Mock session as async context manager
    mock_session = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_session_context)
    worker._session_factory = mock_session_factory

    mock_repository = AsyncMock()
    mock_repository.fetch_new_tasks_for_publishing = AsyncMock(return_value=[task1, task2])
    mock_repository.update = AsyncMock()

    mock_rabbitmq_client = AsyncMock()
    # First publish succeeds, second fails
    mock_rabbitmq_client.publish = AsyncMock(side_effect=[None, Exception("Publish failed")])

    with patch("app.workers.publisher.TaskRepository", return_value=mock_repository):
        with patch("app.workers.publisher.rabbitmq_client", mock_rabbitmq_client):
            count = await worker.process_new_tasks(batch_size=10)
            assert count == 1  # Only one task published

            # First task should be pending
            assert task1.status == TaskStatus.PENDING
            # Second task should remain NEW
            assert task2.status == TaskStatus.NEW
            # Only first task should be updated
            assert mock_repository.update.call_count == 1
