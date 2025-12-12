import asyncio
import json
from typing import Any

import aio_pika

from app.config import settings


class RabbitMQClient:
    """Client for publishing tasks to RabbitMQ with priority support."""

    def __init__(self) -> None:
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self._connection and not self._connection.is_closed:
                return
            self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=settings.worker_prefetch)
            await self._channel.declare_queue(
                settings.queue_name,
                durable=True,
                arguments={"x-max-priority": settings.queue_max_priority},
            )

    async def publish(self, payload: dict[str, Any], priority: int = 0) -> None:
        if not self._channel:
            await self.connect()
        assert self._channel  # mypy quiet
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            priority=min(priority, settings.queue_max_priority),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self._channel.default_exchange.publish(message, routing_key=settings.queue_name)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None


# Global instance
client = RabbitMQClient()
