import json
import logging
import os
from datetime import datetime
from typing import Optional

import aio_pika
from aio_pika import ExchangeType

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.environ.get(
    "CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//"
)

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
            self._connection = await aio_pika.connect_robust(RABBITMQ_URL)
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
            logger.error(f"Failed to connect to RabbitMQ: {e}")
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

    async def publish_work_order_event(self, routing_key: str, payload: dict) -> None:
        if self._wo_exchange is None:
            logger.warning("RabbitMQ not connected, skipping work order event publish")
            return
        try:
            message = aio_pika.Message(
                body=self._serialize(payload),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            await self._wo_exchange.publish(message, routing_key=routing_key)
            logger.info(f"Published work order event: {routing_key}")
        except Exception as e:
            logger.error(f"Failed to publish work order event {routing_key}: {e}")

    async def publish_intervention_event(self, routing_key: str, payload: dict) -> None:
        if self._int_exchange is None:
            logger.warning(
                "RabbitMQ not connected, skipping intervention event publish"
            )
            return
        try:
            message = aio_pika.Message(
                body=self._serialize(payload),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            await self._int_exchange.publish(message, routing_key=routing_key)
            logger.info(f"Published intervention event: {routing_key}")
        except Exception as e:
            logger.error(f"Failed to publish intervention event {routing_key}: {e}")


async def get_rabbitmq() -> RabbitMQService:
    return await RabbitMQService.get_instance()
