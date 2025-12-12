"""Shared pytest fixtures for unit and integration tests."""
from datetime import datetime, timezone
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import deps
from app.api.routes import tasks as tasks_router
from app.db.session import get_session
from app.db.models import Base, Task, TaskPriority, TaskStatus
from app.db.repository import TaskRepository
from app.services.task_service import TaskService


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with transaction rollback."""
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = async_sessionmaker(bind=connection, expire_on_commit=False, class_=AsyncSession)()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def mock_publisher(monkeypatch):
    """Mock RabbitMQ publisher to avoid actual queue connections."""
    published_messages = []

    async def mock_publish(payload: dict, priority: int = 0):
        published_messages.append({"payload": payload, "priority": priority})

    from app.clients.rabbitmq import client

    monkeypatch.setattr(client, "publish", mock_publish)
    return published_messages


@pytest_asyncio.fixture
async def test_app(test_engine, mock_publisher) -> FastAPI:
    """Create FastAPI test application with overridden dependencies."""
    SessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async def get_test_session():
        async with SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # Let the dependency chain work naturally - repository depends on session, service depends on repository
    app = FastAPI(title="Test Tasks Service")
    app.dependency_overrides[get_session] = get_test_session
    app.include_router(tasks_router.router, prefix="/api/v1")
    return app


@pytest_asyncio.fixture
async def test_client(test_app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create test HTTP client."""
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def task_repository(test_session) -> TaskRepository:
    """Create TaskRepository instance for unit tests."""
    return TaskRepository(test_session)


@pytest_asyncio.fixture
async def task_service(task_repository, mock_publisher) -> TaskService:
    """Create TaskService instance for unit tests."""
    # Note: This is async because it depends on async fixtures, but returns a sync object
    return TaskService(task_repository)


@pytest_asyncio.fixture
async def test_session_for_commit(test_session):
    """Provide test session for tests that need to commit manually."""
    return test_session


def create_task(**kwargs) -> Task:
    """Factory function to create Task instances for tests with defaults."""
    defaults = {
        "status": TaskStatus.NEW,
        "priority": TaskPriority.MEDIUM,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return Task(**defaults)

