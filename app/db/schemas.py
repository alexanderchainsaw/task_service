from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskCreate(TaskBase):
    pass


class TaskRead(TaskBase):
    id: UUID
    status: TaskStatus
    result: str | None = None
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
