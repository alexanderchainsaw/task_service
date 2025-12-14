"""Unit tests for consumer result handling."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.db.models import Task, TaskName, TaskStatus
from app.workers.consumer import TaskWorker


@pytest.mark.asyncio
async def test_execute_task_with_string_result():
    """Test that task result is stored when task function returns a string."""
    worker = TaskWorker()
    
    task = Task(
        id=uuid4(),
        task_name=TaskName.SEND_EMAIL,
        status=TaskStatus.IN_PROGRESS,
    )
    
    mock_session = AsyncMock()
    
    # Mock task function that returns a string
    async def task_with_result() -> str:
        return "Email sent successfully"
    
    with patch("app.workers.consumer.get_task_function", return_value=task_with_result):
        await worker._execute_task({}, mock_session, task)
        
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "Email sent successfully"
        mock_session.flush.assert_called()
        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_execute_task_with_dict_result():
    """Test that task result is stored as JSONB when task function returns a dict."""
    worker = TaskWorker()
    
    task = Task(
        id=uuid4(),
        task_name=TaskName.EXPORT_DATA,
        status=TaskStatus.IN_PROGRESS,
    )
    
    mock_session = AsyncMock()
    
    # Mock task function that returns a dict
    async def task_with_dict_result() -> dict:
        return {"file_path": "/path/to/file.csv", "rows": 1000}
    
    with patch("app.workers.consumer.get_task_function", return_value=task_with_dict_result):
        await worker._execute_task({}, mock_session, task)
        
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"file_path": "/path/to/file.csv", "rows": 1000}
        mock_session.flush.assert_called()
        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_execute_task_with_none_result():
    """Test that task result is None when task function returns None."""
    worker = TaskWorker()
    
    task = Task(
        id=uuid4(),
        task_name=TaskName.SEND_EMAIL,
        status=TaskStatus.IN_PROGRESS,
    )
    
    mock_session = AsyncMock()
    
    # Mock task function that returns None
    async def task_with_none_result() -> None:
        return None
    
    with patch("app.workers.consumer.get_task_function", return_value=task_with_none_result):
        await worker._execute_task({}, mock_session, task)
        
        assert task.status == TaskStatus.COMPLETED
        assert task.result is None
        mock_session.flush.assert_called()
        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_execute_task_with_exception():
    """Test that task exceptions are properly handled and task is marked as failed."""
    worker = TaskWorker()
    
    task = Task(
        id=uuid4(),
        task_name=TaskName.ALWAYS_FAIL,
        status=TaskStatus.IN_PROGRESS,
    )
    
    mock_session = AsyncMock()
    
    # Mock task function that raises an exception
    async def task_raises_exception() -> None:
        raise ValueError("Task failed intentionally")
    
    with patch("app.workers.consumer.get_task_function", return_value=task_raises_exception):
        # The exception should be caught by process_message, but we test _execute_task directly
        with pytest.raises(ValueError, match="Task failed intentionally"):
            await worker._execute_task({}, mock_session, task)


