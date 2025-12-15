"""Unit tests for TaskPublisher."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import aio_pika
import pytest

from app.clients.rabbitmq import RabbitMQClient


@pytest.mark.asyncio
async def test_publisher_connect():
    """Test publisher connection."""
    client = RabbitMQClient()
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_queue = AsyncMock()

    with patch("aio_pika.connect_robust", return_value=mock_connection):
        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
        mock_channel.set_qos = AsyncMock()

        await client.connect()

        assert client._connection == mock_connection
        assert client._channel == mock_channel
        mock_channel.set_qos.assert_called_once()
        mock_channel.declare_queue.assert_called_once()


@pytest.mark.asyncio
async def test_publisher_connect_idempotent():
    """Test that connecting multiple times doesn't create multiple connections."""
    client = RabbitMQClient()
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_connection.is_closed = False

    with patch("aio_pika.connect_robust", return_value=mock_connection):
        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.declare_queue = AsyncMock()
        mock_channel.set_qos = AsyncMock()

        await client.connect()
        await client.connect()  # Second call should be no-op

        # Should only connect once
        assert mock_connection.channel.call_count == 1


@pytest.mark.asyncio
async def test_publisher_publish():
    """Test publishing a message."""
    client = RabbitMQClient()
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()

    with patch("aio_pika.connect_robust", return_value=mock_connection):
        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.declare_queue = AsyncMock()
        mock_channel.set_qos = AsyncMock()
        mock_channel.default_exchange = mock_exchange
        mock_exchange.publish = AsyncMock()

        await client.connect()

        payload = {"task_id": "123"}
        await client.publish(payload, priority=9)

        mock_exchange.publish.assert_called_once()
        call_args = mock_exchange.publish.call_args
        message = call_args[0][0]
        assert isinstance(message, aio_pika.Message)
        assert json.loads(message.body.decode()) == payload
        assert message.priority == 9
        assert message.delivery_mode == aio_pika.DeliveryMode.PERSISTENT


@pytest.mark.asyncio
async def test_publisher_publish_auto_connect():
    """Test that publish automatically connects if not connected."""
    client = RabbitMQClient()
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()

    with patch("aio_pika.connect_robust", return_value=mock_connection):
        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.declare_queue = AsyncMock()
        mock_channel.set_qos = AsyncMock()
        mock_channel.default_exchange = mock_exchange
        mock_exchange.publish = AsyncMock()

        # Publish without connecting first
        payload = {"task_id": "123"}
        await client.publish(payload, priority=5)

        # Should have connected automatically
        mock_connection.channel.assert_called_once()
        mock_exchange.publish.assert_called_once()


@pytest.mark.asyncio
async def test_publisher_publish_priority_capping():
    """Test that priority is capped at max priority."""
    client = RabbitMQClient()
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()

    with patch("aio_pika.connect_robust", return_value=mock_connection):
        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.declare_queue = AsyncMock()
        mock_channel.set_qos = AsyncMock()
        mock_channel.default_exchange = mock_exchange
        mock_exchange.publish = AsyncMock()

        await client.connect()

        # Try to publish with priority higher than max (10)
        payload = {"task_id": "123"}
        await client.publish(payload, priority=99)

        call_args = mock_exchange.publish.call_args
        message = call_args[0][0]
        assert message.priority == 10  # Should be capped at max


@pytest.mark.asyncio
async def test_publisher_close():
    """Test closing publisher connection."""
    client = RabbitMQClient()
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()

    with patch("aio_pika.connect_robust", return_value=mock_connection):
        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.declare_queue = AsyncMock()
        mock_channel.set_qos = AsyncMock()

        await client.connect()
        await client.close()

        mock_connection.close.assert_called_once()
        assert client._connection is None
        assert client._channel is None


@pytest.mark.asyncio
async def test_publisher_close_without_connection():
    """Test closing publisher when not connected."""
    client = RabbitMQClient()
    # Should not raise an error
    await client.close()
