"""Task registry."""

from typing import Any, Awaitable, Callable

from app.db.models import TaskName

# Re-export TaskName for convenience
__all__ = ["TaskName", "TASK_REGISTRY", "register_task", "get_task_function"]


# Type alias for task function signature
# Task functions can return a result (str, dict, etc.) that will be stored in task.result
# Tasks are pure functions with no dependencies on Task model or database session
TaskFunction = Callable[[], Awaitable[Any]]


# Registry mapping task names to their implementation functions
TASK_REGISTRY: dict[TaskName, TaskFunction] = {}


def register_task(task_name: TaskName) -> Callable[[TaskFunction], TaskFunction]:
    """Decorator to register a task function in the registry."""

    def decorator(func: TaskFunction) -> TaskFunction:
        if task_name in TASK_REGISTRY:
            raise ValueError(f"Task {task_name} is already registered")
        TASK_REGISTRY[task_name] = func
        return func

    return decorator


def get_task_function(task_name: TaskName) -> TaskFunction:
    """Get the task function for a given task name."""
    if task_name not in TASK_REGISTRY:
        raise ValueError(f"Task {task_name} is not registered in the registry")
    return TASK_REGISTRY[task_name]


# Import all task modules to ensure they register themselves
# This must be at the bottom to avoid circular imports - the functions above
# need to be defined before the task modules try to import them
from app.tasks import data_tasks, email_tasks, failing_tasks, image_tasks  # noqa: F401, E402
