from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TaskRepository
from app.db.session import get_session
from app.services.task_service import TaskService


async def get_task_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TaskRepository:
    """Dependency to get TaskRepository instance."""
    return TaskRepository(session)


async def get_task_service(
    repository: Annotated[TaskRepository, Depends(get_task_repository)],
) -> TaskService:
    """Dependency to get TaskService instance."""
    return TaskService(repository)
