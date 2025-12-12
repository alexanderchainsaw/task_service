"""Repository for Task data access operations."""

from datetime import datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy import and_, asc, case, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import PaginationParams
from app.db.models import Task, TaskPriority, TaskStatus


class TaskRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, task: Task) -> Task:
        """Create a new task"""
        self.session.add(task)
        await self.session.flush()  # Flush to get ID and trigger database defaults
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: UUID, with_lock: bool = False) -> Task | None:
        """Get task by ID, optionally with row-level lock for concurrent access safety."""
        if with_lock:
            stmt = select(Task).where(Task.id == task_id).with_for_update()
            result = await self.session.scalar(stmt)
            return result
        return await self.session.get(Task, task_id)

    async def fetch_new_tasks_for_publishing(self, limit: int = 10) -> list[Task]:
        """
        Fetch NEW tasks with row-level locking to prevent duplicate publishing.
        Uses SELECT FOR UPDATE SKIP LOCKED to allow multiple publishers to work concurrently
        without conflicts.
        """
        # Order by priority (HIGH=3, MEDIUM=2, LOW=1) then by created_at
        priority_order = case(
            (Task.priority == TaskPriority.HIGH, 3),
            (Task.priority == TaskPriority.MEDIUM, 2),
            (Task.priority == TaskPriority.LOW, 1),
            else_=0,
        )
        stmt = (
            select(Task)
            .where(Task.status == TaskStatus.NEW)
            .order_by(desc(priority_order), asc(Task.created_at))
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        pagination: PaginationParams | None = None,
    ) -> Iterable[Task]:
        """List tasks with optional filters and pagination."""
        pagination = pagination or PaginationParams()
        stmt = select(Task)
        filters = []

        if status:
            filters.append(Task.status == status)
        if priority:
            filters.append(Task.priority == priority)
        if created_from:
            filters.append(Task.created_at >= created_from)
        if created_to:
            filters.append(Task.created_at <= created_to)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Order by priority (HIGH=3, MEDIUM=2, LOW=1) then by created_at
        priority_order = case(
            (Task.priority == TaskPriority.HIGH, 3),
            (Task.priority == TaskPriority.MEDIUM, 2),
            (Task.priority == TaskPriority.LOW, 1),
            else_=0,
        )
        stmt = (
            stmt.order_by(desc(priority_order), asc(Task.created_at))
            .limit(pagination.limit)
            .offset(pagination.offset)
        )

        result = await self.session.scalars(stmt)
        return result.all()

    async def update(self, task: Task) -> Task:
        """Update a task in the database. Commit is handled by session context."""
        await self.session.flush()  # Flush changes to database
        await self.session.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        """Delete a task from the database. Commit is handled by session context."""
        await self.session.delete(task)
        # No flush needed - commit happens automatically
