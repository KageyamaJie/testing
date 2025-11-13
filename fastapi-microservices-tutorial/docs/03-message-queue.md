# Message Queue with RabbitMQ

## What is a Message Queue?

A message queue allows services to communicate **asynchronously** by sending messages. This is similar to **MassTransit** in .NET, providing:
- **Decoupling** - Services don't need to know about each other
- **Reliability** - Messages are persisted until processed
- **Scalability** - Multiple workers can process messages

## Why RabbitMQ?

RabbitMQ is a robust message broker that:
- Supports multiple messaging patterns (pub/sub, work queues, routing)
- Guarantees message delivery
- Has excellent management UI
- Is widely used in production
- Has great Python support with `aio-pika` (async) and `pika` (sync)

## Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   FastAPI   │────────▶│  RabbitMQ   │────────▶│ Notification│
│  (Publisher)│         │  (Exchange) │         │   Service   │
└─────────────┘         └─────────────┘         └─────────────┘
```

## Step 1: Create Messaging Interface (Domain Layer)

```python
# app/domain/services/message_publisher.py
from abc import ABC, abstractmethod
from typing import Any

class IMessagePublisher(ABC):
    @abstractmethod
    async def publish(
        self,
        exchange: str,
        routing_key: str,
        message: Any
    ) -> None:
        """Publish message to exchange"""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Connect to message broker"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from message broker"""
        pass
```

```python
# app/domain/services/message_consumer.py
from abc import ABC, abstractmethod
from typing import Callable, Any

class IMessageConsumer(ABC):
    @abstractmethod
    async def consume(
        self,
        queue: str,
        handler: Callable[[Any], None]
    ) -> None:
        """Consume messages from queue"""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Connect to message broker"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from message broker"""
        pass
```

**Why interfaces?** Domain layer defines contracts. Infrastructure implements them.

## Step 2: RabbitMQ Publisher Implementation

```python
# app/infrastructure/messaging/rabbitmq_publisher.py
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
```

**Explanation:**
- **Exchange**: Routes messages to queues (like a post office)
- **Routing Key**: Determines which queue receives the message
- **Topic Exchange**: Flexible routing based on patterns
- **Persistent**: Messages survive broker restarts
- **aio-pika**: Async RabbitMQ client for Python

## Step 3: RabbitMQ Consumer Implementation

```python
# app/infrastructure/messaging/rabbitmq_consumer.py
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
```

**Key Concepts:**
- **Queue**: Stores messages until consumed
- **Acknowledgment**: Message is removed only after successful processing
- **Prefetch**: Limits unacknowledged messages (prevents overload)
- **Requeue**: Failed messages can be retried

## Step 4: Update Use Case to Publish Events

```python
# app/application/use_cases/create_user_use_case.py
import uuid
from datetime import datetime
from typing import Optional
from app.domain.entities.user import User
from app.domain.repositories.user_repository import IUserRepository
from app.domain.services.message_publisher import IMessagePublisher
from app.application.dto.create_user_dto import CreateUserDTO
import os

class CreateUserUseCase:
    def __init__(
        self,
        user_repository: IUserRepository,
        message_publisher: Optional[IMessagePublisher] = None
    ):
        self.user_repository = user_repository
        self.message_publisher = message_publisher

    async def execute(self, dto: CreateUserDTO) -> User:
        """Execute the create user use case"""
        # Business validation
        if not dto.email or '@' not in dto.email:
            raise ValueError("Invalid email address")

        # Check if user already exists
        existing_user = await self.user_repository.find_by_email(dto.email)
        if existing_user:
            raise ValueError("User already exists")

        # Create new user entity
        user = User(
            id=dto.id or str(uuid.uuid4()),
            email=dto.email,
            name=dto.name,
            created_at=datetime.utcnow()
        )

        # Save through repository
        saved_user = await self.user_repository.save(user)

        # Publish event (if publisher is available)
        if self.message_publisher:
            await self.message_publisher.publish(
                os.getenv("RABBITMQ_EXCHANGE", "user_events"),
                "user.created",
                {
                    "user_id": saved_user.id,
                    "email": saved_user.email,
                    "name": saved_user.name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        return saved_user
```

**Explanation:**
- After creating a user, we publish an event
- Other services can listen to this event
- The use case doesn't know about RabbitMQ - it uses the interface

## Step 5: Create Event Handler Service

```python
# app/application/services/user_event_handler.py

class UserEventHandler:
    async def handle_user_created(self, event: dict) -> None:
        """Handle user created event"""
        print(f"📧 Sending welcome email to: {event['email']}")
        print(f"📱 Sending SMS notification to: {event['email']}")
        # In a real app, you'd call email/SMS services here
```

## Step 6: Setup Consumer in Application

```python
# app/infrastructure/messaging/setup_consumers.py
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
```

## Step 7: Update Main Application

```python
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.presentation.api.user_router import router as user_router
from app.infrastructure.messaging.setup_consumers import setup_consumers
import asyncio

# Background task for consumers
consumer_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global consumer_task
    
    # Startup
    print("🚀 Starting microservices application...")
    print("📨 Setting up message consumers...")
    
    # Start consumer in background
    consumer_task = asyncio.create_task(setup_consumers())
    
    yield
    
    # Shutdown
    print("Shutting down...")
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="Microservices Tutorial",
    description="FastAPI microservices with Clean Architecture",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(user_router, prefix="/api")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
```

**Explanation:**
- FastAPI's `lifespan` context manager handles startup/shutdown
- Consumers run in background tasks
- Graceful shutdown ensures connections are closed

## Step 8: Update Dependencies with Message Publisher

```python
# app/presentation/dependencies.py
from app.application.use_cases.create_user_use_case import CreateUserUseCase
from app.application.use_cases.get_user_use_case import GetUserUseCase
from app.infrastructure.repositories.in_memory_user_repository import InMemoryUserRepository
from app.infrastructure.repositories.cached_user_repository import CachedUserRepository
from app.infrastructure.cache.redis_cache_repository import RedisCacheRepository
from app.infrastructure.messaging.rabbitmq_publisher import RabbitMQPublisher

# Create singleton instances
_base_repository = InMemoryUserRepository()
_cache = RedisCacheRepository()
_cached_repository = CachedUserRepository(_base_repository, _cache)

_message_publisher = RabbitMQPublisher()

# Connect publisher (in real app, do this in lifespan)
async def init_message_publisher():
    await _message_publisher.connect()

def get_create_user_use_case() -> CreateUserUseCase:
    """Dependency: Create user use case"""
    return CreateUserUseCase(_cached_repository, _message_publisher)

def get_user_use_case() -> GetUserUseCase:
    """Dependency: Get user use case"""
    return GetUserUseCase(_cached_repository)
```

## Testing Message Queue

```bash
# Start RabbitMQ
docker-compose up -d rabbitmq

# Start the server
uvicorn main:app --reload

# Create a user (this will publish a message)
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"email":"jane@example.com","name":"Jane Doe"}'

# Check RabbitMQ Management UI
# Open http://localhost:15672 (admin/admin123)
# You'll see messages in the queue!
```

## Message Queue Patterns

1. **Publish-Subscribe**: One message to many consumers
2. **Work Queue**: Distribute work among multiple workers
3. **Routing**: Route messages based on routing keys
4. **Topics**: Pattern-based routing (what we're using)

## Benefits

- **Decoupling**: Services don't need to know about each other
- **Reliability**: Messages are persisted until processed
- **Scalability**: Add more workers to process messages faster
- **Resilience**: Failed messages can be retried
- **Async Support**: Python's async/await works perfectly with aio-pika

## Python-Specific Advantages

- **Async/Await**: Native async support in Python 3.7+
- **Type Hints**: Full type safety with interfaces
- **Context Managers**: Clean resource management
- **Exception Handling**: Robust error handling

## Advanced: Connection Pooling and Retry Logic

```python
# app/infrastructure/messaging/rabbitmq_publisher_robust.py
import json
import os
from typing import Any
import aio_pika
from aio_pika.pool import Pool
from app.domain.services.message_publisher import IMessagePublisher

class RobustRabbitMQPublisher(IMessagePublisher):
    def __init__(self):
        self.connection_pool: Pool = None
        self.channel_pool: Pool = None

    async def connect(self) -> None:
        """Connect to RabbitMQ with connection pooling"""
        url = os.getenv(
            "RABBITMQ_URL",
            "amqp://admin:admin123@localhost:5672/"
        )
        
        # Create connection pool
        self.connection_pool = Pool(
            lambda: aio_pika.connect_robust(url),
            max_size=10
        )
        
        # Create channel pool
        self.channel_pool = Pool(
            lambda: self._create_channel(),
            max_size=20
        )

    async def _create_channel(self) -> aio_pika.Channel:
        """Create channel from connection pool"""
        async with self.connection_pool.acquire() as connection:
            return await connection.channel()

    async def publish(
        self,
        exchange: str,
        routing_key: str,
        message: Any
    ) -> None:
        """Publish message with retry logic"""
        async with self.channel_pool.acquire() as channel:
            exchange_obj = await channel.declare_exchange(
                exchange,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            message_body = json.dumps(message).encode('utf-8')
            
            await exchange_obj.publish(
                aio_pika.Message(
                    message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=routing_key
            )

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ"""
        if self.channel_pool:
            await self.channel_pool.close()
        if self.connection_pool:
            await self.connection_pool.close()
```

## Next Steps

- [Complete Example](./04-complete-example.md)
