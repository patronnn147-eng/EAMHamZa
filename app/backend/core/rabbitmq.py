import json
import logging
import os
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import aio_pika
from aio_pika import ExchangeType

logger = logging.getLogger(__name__)

DEFAULT_RABBITMQ_URL = "amqps://guest:guest@localhost:5671//"

EXCHANGE_WORK_ORDERS = "work_orders"
EXCHANGE_INTERVENTIONS = "interventions"

ROUTING_KEY_WO_CREATED = "work_order.created"
ROUTING_KEY_WO_UPDATED = "work_order.updated"
ROUTING_KEY_WO_ASSIGNED = "work_order.assigned"
ROUTING_KEY_WO_STATUS_CHANGED = "work_order.status_changed"

ROUTING_KEY_INT_REQUESTED = "intervention.requested"
ROUTING_KEY_INT_APPROVED = "intervention.approved"
ROUTING_KEY_INT_DECLINED = "intervention.declined"
# Backward compatibility (older code/status naming)
ROUTING_KEY_INT_REJECTED = ROUTING_KEY_INT_DECLINED
ROUTING_KEY_INT_STATUS_CHANGED = "intervention.status_changed"


def _is_secure_rabbitmq_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme.lower() == "amqps"

def _get_rabbitmq_url() -> str:
    url = os.environ.get("CELERY_BROKER_URL", DEFAULT_RABBITMQ_URL)
    if not _is_secure_rabbitmq_url(url):
        logger.warning(
            "Using clear-text RabbitMQ broker URL; set CELERY_BROKER_URL to amqps://... for TLS."
        )
    return url


class RabbitMQService:
    _instance: Optional["RabbitMQService"] = None
    _connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
    _channel: Optional[aio_pika.abc.AbstractChannel] = None
    _wo_exchange: Optional[aio_pika.abc.AbstractExchange] = None
    _int_exchange: Optional[aio_pika.abc.AbstractExchange] = None

    @classmethod
    async def get_instance(cls) -> "RabbitMQService":
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance._connect()
        return cls._instance

    async def _connect(self) -> None:
        try:
            self._connection = await aio_pika.connect_robust(_get_rabbitmq_url())
            self._channel = await self._connection.channel()

            self._wo_exchange = await self._channel.declare_exchange(
                EXCHANGE_WORK_ORDERS,
                ExchangeType.TOPIC,
                durable=True,
            )
            self._int_exchange = await self._channel.declare_exchange(
                EXCHANGE_INTERVENTIONS,
                ExchangeType.TOPIC,
                durable=True,
            )

            logger.info("RabbitMQ connected and exchanges declared")
        except Exception as e:
            logger.exception(f"Failed to connect to RabbitMQ: {e}")
            self._connection = None
            self._channel = None

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("RabbitMQ connection closed")
        self._connection = None
        self._channel = None
        self._wo_exchange = None
        self._int_exchange = None
        RabbitMQService._instance = None

    def _serialize(self, data: dict) -> bytes:
        def _default(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(data, default=_default).encode()

    async def _publish(self, exchange: aio_pika.Exchange, routing_key: str, payload: dict, event_type: str) -> None:
        if exchange is None:
            logger.warning("RabbitMQ not connected, skipping %s event publish", event_type)
            return
        try:
            message = aio_pika.Message(
                body=self._serialize(payload),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            await exchange.publish(message, routing_key=routing_key)
            logger.info("Published %s event: %s", event_type, routing_key)
        except Exception as e:
            logger.exception("Failed to publish %s event %s: %s", event_type, routing_key, e)

    async def publish_work_order_event(self, routing_key: str, payload: dict) -> None:
        await self._publish(self._wo_exchange, routing_key, payload, "work order")

    async def publish_intervention_event(self, routing_key: str, payload: dict) -> None:
        await self._publish(self._int_exchange, routing_key, payload, "intervention")


async def get_rabbitmq() -> RabbitMQService:
    return await RabbitMQService.get_instance()
