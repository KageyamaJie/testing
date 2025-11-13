import os
from app.infrastructure.messaging.rabbitmq_consumer import RabbitMQConsumer
from app.application.services.user_event_handler import UserEventHandler

async def setup_consumers():
    """Setup message consumers"""
    consumer = RabbitMQConsumer()
    await consumer.connect()

    event_handler = UserEventHandler()

    # Consume user.created events
    async def handle_message(message: dict):
        routing_key = message.get("routing_key", "")
        if routing_key == "user.created":
            await event_handler.handle_user_created(message)

    await consumer.consume(
        os.getenv("RABBITMQ_QUEUE", "user_notifications"),
        handle_message
    )

    print("Consumers setup complete")
