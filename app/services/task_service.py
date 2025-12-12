"""Service layer for Task business logic."""

from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from app.api.models import PaginationParams
from app.db.models import Task, TaskPriority, TaskStatus
from app.db.repository import TaskRepository
from app.db.schemas import TaskCreate


class TaskService:
    """Service for Task business logic. Publishing is handled by a separate workers."""

    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    async def create(self, payload: TaskCreate) -> Task:
        """Create a new task with NEW status. Publishing is handled by a separate workers."""
        task = Task(
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            status=TaskStatus.NEW,
            created_at=datetime.now(timezone.utc),
        )
        return await self.repository.create(task)

    async def get(self, task_id: UUID) -> Task | None:
        """Get a task by ID."""
        return await self.repository.get_by_id(task_id)

    async def list(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        pagination: PaginationParams | None = None,
    ) -> Iterable[Task]:
        """List tasks with optional filters and pagination."""
        return await self.repository.list(
            status=status,
            priority=priority,
            created_from=created_from,
            created_to=created_to,
            pagination=pagination,
        )

    async def cancel(self, task: Task) -> Task:
        """Cancel a task if it's not already in a terminal state."""
        if task.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            return task

        task.mark_cancelled()
        return await self.repository.update(task)
