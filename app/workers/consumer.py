import asyncio
import json
import logging
from typing import Any
from uuid import UUID

import aio_pika
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models import Task, TaskStatus
from app.logging_config import setup_logging
from app.tasks import TaskName, get_task_function

setup_logging()
logger = logging.getLogger(__name__)


class TaskWorker:
    def __init__(self) -> None:
        self._engine = create_async_engine(settings.database_url, future=True, echo=False)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None

    async def start(self) -> None:
        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=settings.worker_prefetch)
        queue = await self._channel.declare_queue(
            settings.queue_name,
            durable=True,
            arguments={"x-max-priority": settings.queue_max_priority},
        )
        await queue.consume(self.process_message, no_ack=False)
        logger.info("Worker started. Waiting for messages...")

    async def stop(self) -> None:
        if self._connection:
            await self._connection.close()

    async def process_message(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process():
            payload = json.loads(message.body)
            task_id = UUID(payload["task_id"])
            logger.info(f"Processing task {task_id}")
            async with self._session_factory() as session:
                # Use SELECT FOR UPDATE to prevent concurrent processing of the same task
                # This is important if a message is redelivered or multiple consumers
                # somehow get the same message
                from app.db.repository import TaskRepository

                repository = TaskRepository(session)
                task = await repository.get_by_id(task_id, with_lock=True)
                if not task:
                    logger.warning(f"Task {task_id} not found, skipping")
                    return
                if task.status == TaskStatus.CANCELLED:
                    logger.info(f"Task {task_id} is cancelled, skipping")
                    return
                task.mark_in_progress()
                await session.flush()  # Flush to ensure changes are in session
                await session.commit()  # Commit since we manage our own session
                logger.info(f"Task {task_id} marked as IN_PROGRESS")
                try:
                    await self._execute_task(payload, session, task)
                except Exception as exc:  # noqa: BLE001
                    logger.error(f"Task {task_id} failed: {exc}", exc_info=True)
                    # Re-fetch task to ensure it's attached to the session after commit
                    task = await repository.get_by_id(task_id, with_lock=True)
                    if task:
                        error_message = str(exc) if str(exc) else repr(exc)
                        task.mark_failed(error=error_message)
                        await session.flush()
                        await session.commit()
                        logger.info(f"Task {task_id} marked as FAILED with error: {error_message}")

    async def _execute_task(
        self, payload: dict[str, Any], session: AsyncSession, task: Task
    ) -> None:
        """Execute the actual task function from the registry."""
        logger.info(f"Executing task {task.id} of type {task.task_name}")
        
        # Check if task was cancelled before execution
        if task.status == TaskStatus.CANCELLED:
            logger.info(f"Task {task.id} was cancelled before execution")
            return
        
        # Get the task function from registry
        # task.task_name is already a TaskName enum from the database
        try:
            task_function = get_task_function(task.task_name)
        except ValueError as exc:
            error_msg = f"Task {task.task_name} is not registered in the registry"
            logger.error(error_msg)
            raise ValueError(error_msg) from exc
        
        # Execute the task function and capture its return value
        # Tasks are now pure functions with no dependencies
        logger.info(f"Calling task function for {task.task_name}")
        task_result = await task_function()
        logger.info(f"Task function {task.task_name} completed with result: {task_result}")
        
        # Check if task was cancelled during execution
        if task.status == TaskStatus.CANCELLED:
            logger.info(f"Task {task.id} was cancelled during execution")
            # Still need to commit the cancellation status change
            await session.flush()
            await session.commit()
            return
        
        # Mark as completed with the result
        if task.status == TaskStatus.IN_PROGRESS:
            task.mark_completed(result=task_result)
        
        # Always flush and commit after task execution
        await session.flush()
        await session.commit()
        
        logger.info(f"Task {task.id} completed successfully")


async def main() -> None:
    worker = TaskWorker()
    await worker.start()
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
