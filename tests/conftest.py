"""Shared pytest fixtures for unit and integration tests."""
import os
from datetime import datetime, timezone
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.api import deps
from app.api.routes import tasks as tasks_router
from app.db.session import get_session
from app.db.models import Base, Task, TaskName, TaskPriority, TaskStatus
from app.db.repository import TaskRepository
from app.services.task_service import TaskService


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for testing using testcontainers."""
    # Allow override via environment variable for CI/CD or manual testing
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if test_db_url:
        # If TEST_DATABASE_URL is provided, use it directly (no container)
        yield None
        return
    
    # Simple testcontainers setup as per their docs
    with PostgresContainer("postgres:14-alpine", driver='asyncpg') as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="session")
async def test_engine(postgres_container):
    """Create test database engine using PostgreSQL."""
    # test_db_url = os.getenv("TEST_DATABASE_URL")
    #
    # if test_db_url:
    #     database_url = test_db_url
    # elif postgres_container:
    #     # Get connection URL and convert to asyncpg format
    #     container_url = postgres_container.get_connection_url()
    #     # Convert postgresql:// to postgresql+asyncpg://
    #     database_url = container_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # else:
    #     raise RuntimeError("No database URL provided and container failed to start")
    # Simple engine creation
    from sqlalchemy.pool import NullPool
    engine = create_async_engine(postgres_container.get_connection_url(), echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session - simple setup."""
    async_session_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


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
        "task_name": TaskName.SEND_EMAIL,
        "status": TaskStatus.NEW,
        "priority": TaskPriority.MEDIUM,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return Task(**defaults)

