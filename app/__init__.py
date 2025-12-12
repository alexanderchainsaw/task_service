from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import tasks
from app.clients.rabbitmq import client as rabbitmq_client
from app.config import settings
from app.db.models import Base
from app.db.session import engine

__all__ = ["__version__", "app"]

__version__ = "0.1.0"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # start
    await rabbitmq_client.connect()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # shutdown
    await rabbitmq_client.close()
    await engine.dispose()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(tasks.router, prefix=settings.api_prefix)
