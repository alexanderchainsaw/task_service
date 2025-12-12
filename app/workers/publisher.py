"""Publisher workers that polls for NEW tasks and publishes them to RabbitMQ."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.models import PaginationParams
from app.clients.rabbitmq import client as rabbitmq_client
from app.config import settings
from app.db.models import TaskPriority, TaskStatus
from app.db.repository import TaskRepository
from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def _priority_to_int(priority: TaskPriority) -> int:
    """Convert task priority to RabbitMQ priority."""
    if priority == TaskPriority.HIGH:
        return 9
    if priority == TaskPriority.MEDIUM:
        return 5
    return 1


class TaskPublisherWorker:
    """Worker that publishes NEW tasks to RabbitMQ queue."""

    def __init__(self) -> None:
        self._engine = create_async_engine(settings.database_url, future=True, echo=False)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )
        self._running = False

    async def start(self) -> None:
        """Start the publisher workers."""
        await rabbitmq_client.connect()
        self._running = True
        logger.info("Publisher workers started. Polling for NEW tasks...")

    async def stop(self) -> None:
        """Stop the publisher workers."""
        self._running = False
        await rabbitmq_client.close()
        await self._engine.dispose()
        logger.info("Publisher workers stopped.")

    async def process_new_tasks(self, batch_size: int = 10) -> int:
        """
        Process a batch of NEW tasks and publish them to the queue.
        Uses SELECT FOR UPDATE SKIP LOCKED to prevent duplicate publishing when multiple
        publisher instances are running.
        """
        async with self._session_factory() as session:
            repository = TaskRepository(session)

            # Fetch NEW tasks with row-level locking to prevent race conditions
            # SKIP LOCKED allows other publishers to pick up different tasks
            task_list = await repository.fetch_new_tasks_for_publishing(limit=batch_size)

            if not task_list:
                return 0

            published_count = 0
            for task in task_list:
                try:
                    # Publish to queue
                    await rabbitmq_client.publish(
                        {"task_id": str(task.id)},
                        priority=_priority_to_int(task.priority),
                    )
                    # Mark as PENDING
                    task.mark_pending()
                    await repository.update(task)  # Uses flush() internally
                    await session.commit()  # Commit since we manage our own session
                    published_count += 1
                    logger.info(f"Published task {task.id} to queue")
                except Exception as exc:
                    logger.error(f"Failed to publish task {task.id}: {exc}", exc_info=True)
                    await session.rollback()  # Rollback on error
                    # Task remains in NEW status for retry

            return published_count

    async def run(self, poll_interval: float = 1.0, batch_size: int = 10) -> None:
        """Run the publisher workers loop."""
        await self.start()
        try:
            while self._running:
                try:
                    count = await self.process_new_tasks(batch_size=batch_size)
                    if count > 0:
                        logger.info(f"Published {count} task(s) to queue")
                except Exception as exc:
                    logger.error(f"Error in publisher workers: {exc}", exc_info=True)
                await asyncio.sleep(poll_interval)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Publisher workers interrupted")
        finally:
            await self.stop()


async def main() -> None:
    """Main entry point for publisher workers."""
    worker = TaskPublisherWorker()
    await worker.run(poll_interval=1.0, batch_size=10)


if __name__ == "__main__":
    asyncio.run(main())
