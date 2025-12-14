from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import TaskName, TaskPriority, TaskStatus


class TaskBase(BaseModel):
    task_name: TaskName
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskCreate(TaskBase):
    pass


class TaskRead(TaskBase):
    id: UUID
    status: TaskStatus
    result: Any | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskStatusRead(BaseModel):
    id: UUID
    status: TaskStatus
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)
