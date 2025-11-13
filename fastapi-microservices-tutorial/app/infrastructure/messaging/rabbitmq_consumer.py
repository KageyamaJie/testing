import json
import os
from typing import Callable, Any
import aio_pika
from app.domain.services.message_consumer import IMessageConsumer

class RabbitMQConsumer(IMessageConsumer):
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
            
            # Set prefetch to process one message at a time
            await self.channel.set_qos(prefetch_count=1)
            
            print("Connected to RabbitMQ (Consumer)")
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def consume(
        self,
        queue: str,
        handler: Callable[[Any], None]
    ) -> None:
        """Consume messages from queue"""
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")

        try:
            # Declare queue (create if it doesn't exist)
            queue_obj = await self.channel.declare_queue(
                queue,
                durable=True  # Survive broker restarts
            )

            print(f"Waiting for messages in queue: {queue}")

            async def process_message(message: aio_pika.IncomingMessage):
                """Process incoming message"""
                async with message.process():
                    try:
                        # Parse message
                        content = json.loads(message.body.decode('utf-8'))
                        print(f"Received message: {content}")

                        # Process message
                        await handler(content)

                        print("Message processed successfully")
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        # Message will be requeued if not acknowledged
                        raise  # Re-raise to requeue

            # Start consuming
            await queue_obj.consume(process_message)
        except Exception as e:
            print(f"Error setting up consumer: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ"""
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
