"""Unit tests for task registry."""

import pytest

from app.db.models import TaskName
from app.tasks import TASK_REGISTRY, get_task_function, register_task


@pytest.mark.asyncio
async def test_get_task_function_success():
    """Test getting a registered task function."""
    # All task modules should be imported and registered
    task_function = get_task_function(TaskName.SEND_EMAIL)
    assert task_function is not None
    assert callable(task_function)


@pytest.mark.asyncio
async def test_get_task_function_not_registered():
    """Test getting a task function that doesn't exist."""
    # We can't create a new TaskName enum value, but we can test the error handling
    # by temporarily removing a task from the registry
    original_func = TASK_REGISTRY.pop(TaskName.SEND_EMAIL, None)
    try:
        with pytest.raises(ValueError, match="not registered in the registry"):
            get_task_function(TaskName.SEND_EMAIL)
    finally:
        # Restore the original function
        if original_func:
            TASK_REGISTRY[TaskName.SEND_EMAIL] = original_func


@pytest.mark.asyncio
async def test_register_task_duplicate():
    """Test that registering the same task twice raises an error."""
    # Use a task name that's already registered
    # We'll temporarily remove it, register a new one, then try to register again
    original_func = TASK_REGISTRY.pop(TaskName.SEND_EMAIL, None)
    
    try:
        # Register it once
        async def mock_task() -> None:
            pass
        
        register_task(TaskName.SEND_EMAIL)(mock_task)
        
        # Try to register it again with a different function - should fail
        async def another_task() -> None:
            pass
        
        with pytest.raises(ValueError, match="already registered"):
            register_task(TaskName.SEND_EMAIL)(another_task)
    finally:
        # Restore the original function
        if original_func:
            TASK_REGISTRY[TaskName.SEND_EMAIL] = original_func


@pytest.mark.asyncio
async def test_task_registry_populated():
    """Test that the task registry is populated with all expected tasks."""
    # Verify all task names from the enum are registered
    expected_tasks = [
        TaskName.SEND_EMAIL,
        TaskName.SEND_BULK_EMAIL,
        TaskName.RESIZE_IMAGE,
        TaskName.COMPRESS_IMAGE,
        TaskName.EXPORT_DATA,
        TaskName.IMPORT_DATA,
        TaskName.ALWAYS_FAIL,
        TaskName.ALWAYS_RAISE_VALUE_ERROR,
        TaskName.ALWAYS_RAISE_RUNTIME_ERROR,
    ]
    
    for task_name in expected_tasks:
        assert task_name in TASK_REGISTRY, f"Task {task_name} should be registered"
        task_function = get_task_function(task_name)
        assert callable(task_function)


