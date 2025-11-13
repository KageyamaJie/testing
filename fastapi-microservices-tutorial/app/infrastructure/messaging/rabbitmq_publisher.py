import json
import os
from typing import Any
import aio_pika
from app.domain.services.message_publisher import IMessagePublisher

class RabbitMQPublisher(IMessagePublisher):
    def __init__(self):
        self.connection: aio_pika.Connection = None
        self.channel: aio_pika.Channel = None

    async def connect(self) -> None:
        """Connect to RabbitMQ"""
        try:
            url = os.getenv(
                "RABBITMQ_URL",
                "amqp://admin:admin123@localhost:5672/"
            )
            self.connection = await aio_pika.connect_robust(url)
            self.channel = await self.connection.channel()
            print("Connected to RabbitMQ")
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def publish(
        self,
        exchange: str,
        routing_key: str,
        message: Any
    ) -> None:
        """Publish message to exchange"""
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")

        try:
            # Declare exchange (create if it doesn't exist)
            exchange_obj = await self.channel.declare_exchange(
                exchange,
                aio_pika.ExchangeType.TOPIC,
                durable=True  # Survive broker restarts
            )

            # Serialize message
            message_body = json.dumps(message).encode('utf-8')

            # Publish message
            await exchange_obj.publish(
                aio_pika.Message(
                    message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT  # Survive broker restarts
                ),
                routing_key=routing_key
            )

            print(f"Published message to {exchange} with key {routing_key}")
        except Exception as e:
            print(f"Error publishing message: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ"""
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
