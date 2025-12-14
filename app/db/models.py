import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TaskStatus(str, enum.Enum):
    NEW = "NEW"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskName(str, enum.Enum):
    """Enumeration of all available task types."""

    # Email tasks
    SEND_EMAIL = "SEND_EMAIL"
    SEND_BULK_EMAIL = "SEND_BULK_EMAIL"

    # Image tasks
    RESIZE_IMAGE = "RESIZE_IMAGE"
    COMPRESS_IMAGE = "COMPRESS_IMAGE"

    # Data processing tasks
    EXPORT_DATA = "EXPORT_DATA"
    IMPORT_DATA = "IMPORT_DATA"

    # Test tasks that always fail
    ALWAYS_FAIL = "ALWAYS_FAIL"
    ALWAYS_RAISE_VALUE_ERROR = "ALWAYS_RAISE_VALUE_ERROR"
    ALWAYS_RAISE_RUNTIME_ERROR = "ALWAYS_RAISE_RUNTIME_ERROR"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_name = Column(
        Enum(TaskName, name="task_name"),
        nullable=False,
    )
    description = Column(Text, nullable=True)
    priority = Column(
        Enum(TaskPriority, name="task_priority"),
        nullable=False,
        default=TaskPriority.MEDIUM,
    )
    status = Column(Enum(TaskStatus, name="task_status"), nullable=False, default=TaskStatus.NEW)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def mark_pending(self) -> None:
        self.status = TaskStatus.PENDING

    def mark_in_progress(self) -> None:
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc)

    def mark_completed(self, result: Any = None) -> None:
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc)

    def mark_cancelled(self) -> None:
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)
