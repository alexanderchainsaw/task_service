"""Task implementations that always raise exceptions for testing error handling."""

from app.tasks import TaskName, register_task


@register_task(TaskName.ALWAYS_FAIL)
async def always_fail_task() -> None:
    """Task that always raises a generic Exception."""
    raise Exception("This task always fails")


@register_task(TaskName.ALWAYS_RAISE_VALUE_ERROR)
async def always_raise_value_error_task() -> None:
    """Task that always raises a ValueError."""
    raise ValueError("Invalid value provided to task")


@register_task(TaskName.ALWAYS_RAISE_RUNTIME_ERROR)
async def always_raise_runtime_error_task() -> None:
    """Task that always raises a RuntimeError."""
    raise RuntimeError("Runtime error occurred in task")
