from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_task_service
from app.api.models import PaginationParams
from app.db.models import TaskPriority, TaskStatus
from app.db.schemas import TaskCreate, TaskRead, TaskStatusRead
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate, svc: Annotated[TaskService, Depends(get_task_service)]
) -> TaskRead:
    """Create a new task with NEW status. Publishing is handled by a separate workers."""
    task = await svc.create(task_in)
    return TaskRead.model_validate(task)


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    svc: Annotated[TaskService, Depends(get_task_service)],
    task_status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[TaskRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    tasks = await svc.list(
        status=task_status,
        priority=priority,
        created_from=created_from,
        created_to=created_to,
        pagination=pagination,
    )
    return [TaskRead.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: UUID, svc: Annotated[TaskService, Depends(get_task_service)]
) -> TaskRead:
    task = await svc.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskRead.model_validate(task)


@router.get("/{task_id}/status", response_model=TaskStatusRead)
async def get_task_status(
    task_id: UUID, svc: Annotated[TaskService, Depends(get_task_service)]
) -> TaskStatusRead:
    task = await svc.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskStatusRead.model_validate(task)


@router.delete("/{task_id}", response_model=TaskRead)
async def cancel_task(
    task_id: UUID, svc: Annotated[TaskService, Depends(get_task_service)]
) -> TaskRead:
    task = await svc.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    updated = await svc.cancel(task)
    return TaskRead.model_validate(updated)
