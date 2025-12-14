"""Unit tests for TaskWorker consumer."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import aio_pika

from app.db.models import Task, TaskName, TaskStatus
from app.workers.consumer import TaskWorker


@pytest.mark.asyncio
async def test_process_message_task_not_found():
    """Test processing a message for a task that doesn't exist."""
    worker = TaskWorker()
    
    # Mock message
    mock_message = AsyncMock(spec=aio_pika.IncomingMessage)
    mock_message.body = json.dumps({"task_id": str(uuid4())}).encode()
    # Mock process as async context manager
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=None)
    mock_context_manager.__aexit__ = AsyncMock(return_value=None)
    mock_message.process = MagicMock(return_value=mock_context_manager)
    
    # Mock session factory as async context manager
    mock_session = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_session_context)
    worker._session_factory = mock_session_factory
    
    # Mock repository to return None (task not found)
    mock_repository = AsyncMock()
    mock_repository.get_by_id = AsyncMock(return_value=None)
    
    with patch("app.db.repository.TaskRepository", return_value=mock_repository):
        # Should not raise, just skip
        await worker.process_message(mock_message)
    
    # Verify it tried to get the task
    mock_repository.get_by_id.assert_called_once()


@pytest.mark.asyncio
async def test_process_message_task_cancelled():
    """Test processing a message for a cancelled task."""
    worker = TaskWorker()
    
    # Create a cancelled task
    task = Task(
        id=uuid4(),
        task_name=TaskName.SEND_EMAIL,
        status=TaskStatus.CANCELLED,
    )
    
    # Mock message
    mock_message = AsyncMock(spec=aio_pika.IncomingMessage)
    mock_message.body = json.dumps({"task_id": str(task.id)}).encode()
    # Mock process as async context manager
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=None)
    mock_context_manager.__aexit__ = AsyncMock(return_value=None)
    mock_message.process = MagicMock(return_value=mock_context_manager)
    
    # Mock session factory as async context manager
    mock_session = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_session_context)
    worker._session_factory = mock_session_factory
    
    # Mock repository to return cancelled task
    mock_repository = AsyncMock()
    mock_repository.get_by_id = AsyncMock(return_value=task)
    
    with patch("app.db.repository.TaskRepository", return_value=mock_repository):
        # Should not raise, just skip
        await worker.process_message(mock_message)
    
    # Verify it checked the task but didn't execute
    mock_repository.get_by_id.assert_called_once()


@pytest.mark.asyncio
async def test_execute_task_unregistered_task():
    """Test executing a task with an unregistered task name."""
    worker = TaskWorker()
    
    # Create a task
    task = Task(
        id=uuid4(),
        task_name=TaskName.SEND_EMAIL,
        status=TaskStatus.NEW,
    )
    
    mock_session = AsyncMock()
    
    # Mock get_task_function to raise ValueError (simulating unregistered task)
    with patch("app.workers.consumer.get_task_function", side_effect=ValueError("Task SEND_EMAIL is not registered in the registry")):
        with pytest.raises(ValueError, match="not registered"):
            await worker._execute_task({}, mock_session, task)


@pytest.mark.asyncio
async def test_execute_task_function_raises_error():
    """Test executing a task where the task function raises an error."""
    worker = TaskWorker()
    
    task = Task(
        id=uuid4(),
        task_name=TaskName.SEND_EMAIL,
        status=TaskStatus.IN_PROGRESS,
    )
    
    mock_session = AsyncMock()
    
    # Mock task function to raise an error
    async def failing_task() -> None:
        raise RuntimeError("Task execution failed")
    
    with patch("app.workers.consumer.get_task_function", return_value=failing_task):
        with pytest.raises(RuntimeError, match="Task execution failed"):
            await worker._execute_task({}, mock_session, task)


@pytest.mark.asyncio
async def test_execute_task_cancelled_during_execution():
    """Test executing a task that gets cancelled during execution."""
    worker = TaskWorker()
    
    task = Task(
        id=uuid4(),
        task_name=TaskName.SEND_EMAIL,
        status=TaskStatus.IN_PROGRESS,
    )
    
    mock_session = AsyncMock()
    
    # Mock task function that doesn't do anything
    async def simple_task() -> None:
        pass
    
    # Simulate task being cancelled externally (e.g., by another process)
    task.mark_cancelled()
    
    with patch("app.workers.consumer.get_task_function", return_value=simple_task):
        await worker._execute_task({}, mock_session, task)
        
        # Task should remain cancelled
        assert task.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_execute_task_auto_completion():
    """Test that task is auto-completed if task function doesn't mark it."""
    worker = TaskWorker()
    
    task = Task(
        id=uuid4(),
        task_name=TaskName.SEND_EMAIL,
        status=TaskStatus.IN_PROGRESS,
    )
    
    mock_session = AsyncMock()
    
    # Mock task function that doesn't change task status and returns None
    async def simple_task() -> None:
        pass
    
    with patch("app.workers.consumer.get_task_function", return_value=simple_task):
        await worker._execute_task({}, mock_session, task)
        
        # Task should be auto-completed with None result
        assert task.status == TaskStatus.COMPLETED
        assert task.result is None
        mock_session.flush.assert_called()
        mock_session.commit.assert_called()


