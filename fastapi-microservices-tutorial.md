# Microservices Architecture Tutorial: Python with FastAPI

## Table of Contents
1. [Introduction](#introduction)
2. [Clean Architecture Setup](#clean-architecture-setup)
3. [Distributed Caching Implementation](#distributed-caching-implementation)
4. [Message Queue with RabbitMQ](#message-queue-with-rabbitmq)
5. [Complete Example: User Service](#complete-example-user-service)

---

## Introduction

This tutorial will guide you through building a microservices architecture using Python and FastAPI. We'll implement:

- **Clean Architecture**: Separation of concerns with layers (Domain, Application, Infrastructure, Presentation)
- **Distributed Caching**: A FusionCache-like solution using Redis
- **Message Queue**: MassTransit-like abstraction using RabbitMQ

### Prerequisites
- Python 3.10+
- pip (Python package manager)
- Docker (for Redis and RabbitMQ)
- Understanding of Python basics and async/await

---

## Clean Architecture Setup

Clean Architecture organizes code into layers, ensuring business logic is independent of frameworks and external concerns.

### Project Structure

```
user_service/
├── src/
│   ├── domain/           # Business entities and rules
│   │   ├── entities/
│   │   └── interfaces/
│   ├── application/      # Use cases and business logic
│   │   ├── use_cases/
│   │   └── dto/
│   ├── infrastructure/   # External concerns (DB, Cache, MQ)
│   │   ├── database/
│   │   ├── cache/
│   │   └── messaging/
│   └── presentation/     # API layer (FastAPI routes)
│       ├── controllers/
│       └── routers/
├── requirements.txt
└── pyproject.toml
```

### Step 1: Initialize Project

```bash
mkdir user_service && cd user_service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install fastapi uvicorn[standard] pydantic python-dotenv
```

### Step 2: Domain Layer - Entities

**File: `src/domain/entities/user.py`**

```python
"""
Domain Entity: User

This represents the core business entity.
It contains only business logic and validation rules.
No framework dependencies here!
"""
from datetime import datetime
from typing import Optional
import re


class User:
    """
    User domain entity
    
    This class encapsulates business rules and validation.
    It's independent of any framework (FastAPI, SQLAlchemy, etc.)
    """
    
    def __init__(
        self,
        id: str,
        email: str,
        name: str,
        created_at: datetime
    ):
        self.id = id
        self.email = email
        self.name = name
        self.created_at = created_at
        
        # Validate on creation
        self._validate()
    
    def _validate(self) -> None:
        """
        Business rule: Email must be valid
        """
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, self.email):
            raise ValueError('Invalid email format')
        
        if not self.name or not self.name.strip():
            raise ValueError('Name is required')
    
    def is_active(self) -> bool:
        """
        Business logic: Check if user is active
        
        Business rule: Users created more than 30 days ago are considered active
        """
        days_since_creation = (datetime.now() - self.created_at).days
        return days_since_creation > 30
    
    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, name={self.name})"
```

**File: `src/domain/interfaces/user_repository.py`**

```python
"""
Repository Interface (Domain Layer)

Defines what operations we need, not how they're implemented.
This keeps our domain independent of database technology.
"""
from abc import ABC, abstractmethod
from typing import Optional
from ..entities.user import User


class IUserRepository(ABC):
    """
    User Repository Interface
    
    This interface defines the contract for user persistence.
    Implementations can use any database (PostgreSQL, MongoDB, etc.)
    """
    
    @abstractmethod
    async def find_by_id(self, user_id: str) -> Optional[User]:
        """Find user by ID"""
        pass
    
    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email"""
        pass
    
    @abstractmethod
    async def save(self, user: User) -> User:
        """Save user"""
        pass
    
    @abstractmethod
    async def delete(self, user_id: str) -> None:
        """Delete user"""
        pass
```

### Step 3: Application Layer - Use Cases

**File: `src/application/use_cases/create_user.py`**

```python
"""
Use Case: Create User

This contains the application-specific business logic.
It orchestrates domain entities and repositories.
"""
import uuid
from datetime import datetime
from typing import Protocol
from ...domain.entities.user import User
from ...domain.interfaces.user_repository import IUserRepository
from ...domain.interfaces.message_bus import IMessageBus


class CreateUserDto:
    """Data Transfer Object for creating a user"""
    def __init__(self, email: str, name: str):
        self.email = email
        self.name = name


class CreateUserUseCase:
    """
    Create User Use Case
    
    This method:
    1. Validates business rules (via User entity)
    2. Checks for duplicates
    3. Saves the user
    4. Publishes event
    5. Returns the result
    """
    
    def __init__(
        self,
        user_repository: IUserRepository,
        message_bus: IMessageBus
    ):
        self.user_repository = user_repository
        self.message_bus = message_bus
    
    async def execute(self, dto: CreateUserDto) -> User:
        """
        Execute the use case
        
        This is where the business logic lives.
        It's independent of FastAPI, HTTP, etc.
        """
        # Check if user already exists
        existing_user = await self.user_repository.find_by_email(dto.email)
        if existing_user:
            raise ValueError('User with this email already exists')
        
        # Create domain entity (this validates the data)
        user = User(
            id=str(uuid.uuid4()),
            email=dto.email,
            name=dto.name,
            created_at=datetime.now()
        )
        
        # Save via repository
        saved_user = await self.user_repository.save(user)
        
        # Publish event: UserCreated
        # This allows other services to react to user creation
        from ...domain.interfaces.message_bus import Message
        
        event = Message(
            type='UserCreated',
            payload={
                'user_id': saved_user.id,
                'email': saved_user.email,
                'name': saved_user.name,
            },
            timestamp=datetime.now(),
            correlation_id=saved_user.id
        )
        
        await self.message_bus.publish('user-events', 'user.created', event)
        
        return saved_user
```

**File: `src/application/use_cases/get_user.py`**

```python
"""
Use Case: Get User
"""
from typing import Protocol
from ...domain.entities.user import User
from ...domain.interfaces.user_repository import IUserRepository
from ...domain.interfaces.cache_service import ICacheService


class GetUserUseCase:
    """
    Get User Use Case with caching
    """
    
    def __init__(
        self,
        user_repository: IUserRepository,
        cache_service: ICacheService
    ):
        self.user_repository = user_repository
        self.cache_service = cache_service
    
    async def execute(self, user_id: str) -> User:
        """
        Get user with caching
        
        This demonstrates the get_or_set pattern:
        - First checks cache
        - If cache miss, fetches from repository
        - Caches the result for 5 minutes
        - Returns the user
        """
        cache_key = f"user:{user_id}"
        ttl_seconds = 300  # 5 minutes
        
        async def factory():
            """Factory function: executed only on cache miss"""
            db_user = await self.user_repository.find_by_id(user_id)
            if not db_user:
                raise ValueError('User not found')
            return db_user
        
        user = await self.cache_service.get_or_set(
            cache_key,
            factory,
            ttl_seconds
        )
        
        return user
```

### Step 4: Infrastructure Layer - Database Implementation

**File: `src/infrastructure/database/in_memory_user_repository.py`**

```python
"""
Infrastructure: In-Memory Repository Implementation

This implements the repository interface using in-memory storage.
In production, you'd use PostgreSQL, MongoDB, etc.
The domain layer doesn't care about this implementation!
"""
from typing import Optional, Dict
from ...domain.entities.user import User
from ...domain.interfaces.user_repository import IUserRepository


class InMemoryUserRepository(IUserRepository):
    """
    In-Memory User Repository
    
    This is a simple implementation for demonstration.
    In production, use SQLAlchemy, MongoDB, etc.
    """
    
    def __init__(self):
        self._users: Dict[str, User] = {}
    
    async def find_by_id(self, user_id: str) -> Optional[User]:
        """Find user by ID"""
        return self._users.get(user_id)
    
    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email"""
        for user in self._users.values():
            if user.email == email:
                return user
        return None
    
    async def save(self, user: User) -> User:
        """Save user"""
        self._users[user.id] = user
        return user
    
    async def delete(self, user_id: str) -> None:
        """Delete user"""
        if user_id in self._users:
            del self._users[user_id]
```

---

## Distributed Caching Implementation

Now let's implement a FusionCache-like distributed caching solution using Redis.

### Step 1: Install Dependencies

```bash
pip install redis aioredis
```

### Step 2: Create Cache Interface (Domain Layer)

**File: `src/domain/interfaces/cache_service.py`**

```python
"""
Cache Service Interface

Similar to FusionCache, provides a unified caching interface.
The implementation can be Redis, Memcached, or in-memory.
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Callable, Awaitable, Optional
import json

T = TypeVar('T')


class ICacheService(ABC):
    """
    Cache Service Interface
    
    Provides a unified interface for caching operations.
    Similar to FusionCache in .NET.
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Set value in cache with expiration
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds (optional)
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass
    
    @abstractmethod
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl_seconds: Optional[int] = None
    ) -> T:
        """
        Get or set pattern (like FusionCache's GetOrSet)
        
        If key exists, return cached value.
        If not, execute factory function, cache result, and return it.
        
        This prevents cache stampede and reduces code duplication.
        
        Args:
            key: Cache key
            factory: Async function that returns the value if cache miss
            ttl_seconds: Time to live in seconds (optional)
            
        Returns:
            Cached or newly computed value
        """
        pass
```

### Step 3: Redis Implementation (Infrastructure Layer)

**File: `src/infrastructure/cache/redis_cache_service.py`**

```python
"""
Infrastructure: Redis Cache Implementation

Implements distributed caching using Redis.
This is similar to FusionCache in .NET.
"""
import json
import logging
from typing import Optional, TypeVar, Callable, Awaitable
import redis.asyncio as redis
from ...domain.interfaces.cache_service import ICacheService

logger = logging.getLogger(__name__)
T = TypeVar('T')


class RedisCacheService(ICacheService):
    """
    Redis Cache Service
    
    Provides distributed caching using Redis.
    Similar to FusionCache in .NET.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis connection
        
        Args:
            redis_url: Redis connection URL (defaults to REDIS_URL env var)
        """
        url = redis_url or 'redis://localhost:6379'
        self.client = redis.from_url(url, decode_responses=False)
        logger.info('Redis cache service initialized')
    
    async def get(self, key: str) -> Optional[any]:
        """
        Get value from Redis cache
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized value or None if not found
        """
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.error(f'Cache get error for key {key}: {e}')
            return None
    
    async def set(
        self,
        key: str,
        value: any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Set value in Redis cache with optional TTL
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds (optional)
        """
        try:
            serialized = json.dumps(value).encode('utf-8')
            if ttl_seconds:
                await self.client.setex(key, ttl_seconds, serialized)
            else:
                await self.client.set(key, serialized)
        except Exception as e:
            logger.error(f'Cache set error for key {key}: {e}')
            raise
    
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        result = await self.client.exists(key)
        return result == 1
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl_seconds: Optional[int] = None
    ) -> T:
        """
        Get or Set pattern (FusionCache-like)
        
        This is a powerful pattern:
        1. Try to get from cache
        2. If not found, execute factory function
        3. Cache the result
        4. Return the value
        
        This prevents cache stampede and reduces code duplication.
        
        Args:
            key: Cache key
            factory: Async function that returns the value if cache miss
            ttl_seconds: Time to live in seconds (optional)
            
        Returns:
            Cached or newly computed value
        """
        # Try to get from cache first
        cached = await self.get(key)
        if cached is not None:
            logger.debug(f'Cache hit for key {key}')
            return cached
        
        # Cache miss - execute factory function
        logger.debug(f'Cache miss for key {key}, executing factory')
        value = await factory()
        
        # Cache the result
        await self.set(key, value, ttl_seconds)
        
        return value
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        await self.client.close()
        logger.info('Redis cache service disconnected')
```

---

## Message Queue with RabbitMQ

Now let's implement a MassTransit-like message queue abstraction using RabbitMQ.

### Step 1: Install Dependencies

```bash
pip install aio-pika pika
```

### Step 2: Create Message Bus Interface (Domain Layer)

**File: `src/domain/interfaces/message_bus.py`**

```python
"""
Message Bus Interface

Similar to MassTransit, provides abstraction over message queue.
Allows publishing and consuming messages without knowing RabbitMQ details.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Awaitable, Dict
from dataclasses import dataclass


@dataclass
class Message:
    """
    Message structure
    
    Similar to MassTransit's message envelope.
    """
    type: str
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None


class IMessageBus(ABC):
    """
    Message Bus Interface
    
    Provides abstraction over message queue.
    Similar to MassTransit in .NET.
    """
    
    @abstractmethod
    async def publish(
        self,
        exchange: str,
        routing_key: str,
        message: Message
    ) -> None:
        """
        Publish a message to an exchange
        
        Args:
            exchange: Exchange name
            routing_key: Routing key (for topic exchanges)
            message: Message to publish
        """
        pass
    
    @abstractmethod
    async def subscribe(
        self,
        queue: str,
        handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """
        Subscribe to messages from a queue
        
        Args:
            queue: Queue name
            handler: Async function to handle messages
        """
        pass
    
    @abstractmethod
    async def bind_queue(
        self,
        queue: str,
        exchange: str,
        routing_key: str
    ) -> None:
        """
        Create a queue and bind it to an exchange
        
        Args:
            queue: Queue name
            exchange: Exchange name
            routing_key: Routing key pattern
        """
        pass
```

### Step 3: RabbitMQ Implementation (Infrastructure Layer)

**File: `src/infrastructure/messaging/rabbitmq_message_bus.py`**

```python
"""
Infrastructure: RabbitMQ Message Bus Implementation

Implements message queue using RabbitMQ.
Similar to MassTransit in .NET.
"""
import json
import logging
import uuid
from typing import Callable, Awaitable, Optional
from aio_pika import connect_robust, Message as RabbitMQMessage, ExchangeType
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractQueue
from ...domain.interfaces.message_bus import IMessageBus, Message

logger = logging.getLogger(__name__)


class RabbitMQMessageBus(IMessageBus):
    """
    RabbitMQ Message Bus
    
    Implements message queue using RabbitMQ.
    Similar to MassTransit in .NET.
    """
    
    def __init__(self, connection_url: Optional[str] = None):
        """
        Initialize RabbitMQ connection
        
        Args:
            connection_url: RabbitMQ connection URL (defaults to RABBITMQ_URL env var)
        """
        import os
        self.connection_url = connection_url or os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        logger.info('RabbitMQ message bus initialized')
    
    async def _ensure_connection(self) -> AbstractChannel:
        """Ensure connection and channel are established"""
        if self.connection is None or self.connection.is_closed:
            self.connection = await connect_robust(self.connection_url)
            logger.info('RabbitMQ connected')
        
        if self.channel is None or self.channel.is_closed:
            self.channel = await self.connection.channel()
            logger.info('RabbitMQ channel created')
        
        return self.channel
    
    async def publish(
        self,
        exchange: str,
        routing_key: str,
        message: Message
    ) -> None:
        """
        Publish a message to an exchange
        
        This is similar to MassTransit's Publish method.
        Messages are published to an exchange with a routing key.
        
        Args:
            exchange: Exchange name
            routing_key: Routing key
            message: Message to publish
        """
        channel = await self._ensure_connection()
        
        # Declare exchange (create if not exists)
        exchange_obj = await channel.declare_exchange(
            exchange,
            ExchangeType.TOPIC,
            durable=True  # Survive broker restart
        )
        
        # Serialize message
        message_body = json.dumps({
            'type': message.type,
            'payload': message.payload,
            'timestamp': message.timestamp.isoformat(),
            'correlation_id': message.correlation_id or str(uuid.uuid4())
        }).encode('utf-8')
        
        # Publish message
        await exchange_obj.publish(
            RabbitMQMessage(
                message_body,
                delivery_mode=2,  # Persistent (survives broker restart)
                message_id=message.correlation_id or str(uuid.uuid4()),
                timestamp=message.timestamp
            ),
            routing_key=routing_key
        )
        
        logger.info(f'Published message to {exchange} with routing key {routing_key}')
    
    async def subscribe(
        self,
        queue: str,
        handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """
        Subscribe to messages from a queue
        
        This is similar to MassTransit's Consumer.
        Messages are consumed from a queue and processed by the handler.
        
        Args:
            queue: Queue name
            handler: Async function to handle messages
        """
        channel = await self._ensure_connection()
        
        # Declare queue
        queue_obj: AbstractQueue = await channel.declare_queue(
            queue,
            durable=True  # Queue survives broker restart
        )
        
        # Set prefetch to process one message at a time
        await channel.set_qos(prefetch_count=1)
        
        async def process_message(rabbitmq_message: RabbitMQMessage) -> None:
            """Process incoming message"""
            async with rabbitmq_message.process():
                try:
                    # Deserialize message
                    message_data = json.loads(rabbitmq_message.body.decode('utf-8'))
                    message = Message(
                        type=message_data['type'],
                        payload=message_data['payload'],
                        timestamp=datetime.fromisoformat(message_data['timestamp']),
                        correlation_id=message_data.get('correlation_id')
                    )
                    
                    # Process message
                    await handler(message)
                    
                    logger.info(f'Processed message from queue {queue}')
                except Exception as e:
                    logger.error(f'Error processing message from queue {queue}: {e}')
                    # Message will be nacked and requeued
                    raise
        
        # Start consuming
        await queue_obj.consume(process_message)
        logger.info(f'Subscribed to queue {queue}')
    
    async def bind_queue(
        self,
        queue: str,
        exchange: str,
        routing_key: str
    ) -> None:
        """
        Bind queue to exchange
        
        Args:
            queue: Queue name
            exchange: Exchange name
            routing_key: Routing key pattern
        """
        channel = await self._ensure_connection()
        
        # Declare exchange
        exchange_obj = await channel.declare_exchange(
            exchange,
            ExchangeType.TOPIC,
            durable=True
        )
        
        # Declare queue
        queue_obj = await channel.declare_queue(queue, durable=True)
        
        # Bind queue to exchange
        await queue_obj.bind(exchange_obj, routing_key=routing_key)
        logger.info(f'Bound queue {queue} to exchange {exchange} with routing key {routing_key}')
    
    async def close(self) -> None:
        """Close connections"""
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
        logger.info('RabbitMQ message bus closed')
```

### Step 4: Create Event Handler (Consumer)

**File: `src/application/handlers/user_created_handler.py`**

```python
"""
Event Handler: User Created

This handles UserCreated events from the message queue.
Similar to MassTransit consumers.
"""
import logging
from ...domain.interfaces.message_bus import Message

logger = logging.getLogger(__name__)


class UserCreatedHandler:
    """
    User Created Event Handler
    
    This handles UserCreated events from the message queue.
    """
    
    async def handle(self, message: Message) -> None:
        """
        Handle UserCreated event
        
        This could:
        - Send welcome email
        - Create user profile
        - Update analytics
        - etc.
        
        Args:
            message: UserCreated message
        """
        logger.info(f'UserCreated event received: {message.payload}')
        
        # Example: Send welcome email (simulated)
        await self._send_welcome_email(message.payload['email'])
        
        # Example: Update analytics
        await self._update_analytics(message.payload['user_id'])
    
    async def _send_welcome_email(self, email: str) -> None:
        """Send welcome email"""
        logger.info(f'Sending welcome email to {email}')
        # In production, integrate with email service
    
    async def _update_analytics(self, user_id: str) -> None:
        """Update analytics"""
        logger.info(f'Updating analytics for user {user_id}')
        # In production, send to analytics service
```

---

## Complete Example: User Service

### Step 1: Dependency Injection Setup

**File: `src/infrastructure/di/container.py`**

```python
"""
Dependency Injection Container

This wires up all dependencies.
In production, use a DI library like dependency-injector.
"""
from ...infrastructure.database.in_memory_user_repository import InMemoryUserRepository
from ...infrastructure.cache.redis_cache_service import RedisCacheService
from ...infrastructure.messaging.rabbitmq_message_bus import RabbitMQMessageBus
from ...application.use_cases.create_user import CreateUserUseCase
from ...application.use_cases.get_user import GetUserUseCase
from ...application.handlers.user_created_handler import UserCreatedHandler


class Container:
    """
    Dependency Injection Container
    
    Wires up all dependencies for the application.
    """
    
    def __init__(self):
        # Infrastructure
        self.user_repository = InMemoryUserRepository()
        self.cache_service = RedisCacheService()
        self.message_bus = RabbitMQMessageBus()
        
        # Use Cases
        self.create_user_use_case = CreateUserUseCase(
            self.user_repository,
            self.message_bus
        )
        self.get_user_use_case = GetUserUseCase(
            self.user_repository,
            self.cache_service
        )
        
        # Handlers
        self.user_created_handler = UserCreatedHandler()
    
    async def initialize(self) -> None:
        """Initialize message queue subscriptions"""
        # Bind queue to exchange
        await self.message_bus.bind_queue(
            'user-created-queue',
            'user-events',
            'user.created'
        )
        
        # Subscribe to messages
        await self.message_bus.subscribe(
            'user-created-queue',
            self.user_created_handler.handle
        )
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        await self.cache_service.disconnect()
        await self.message_bus.close()
```

### Step 2: Presentation Layer - FastAPI Controllers

**File: `src/presentation/controllers/user_controller.py`**

```python
"""
Presentation Layer: User Controller

Handles HTTP requests/responses.
Delegates business logic to use cases.
"""
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr
from ...application.use_cases.create_user import CreateUserUseCase, CreateUserDto
from ...application.use_cases.get_user import GetUserUseCase


class CreateUserRequest(BaseModel):
    """Request model for creating a user"""
    email: EmailStr
    name: str


class UserResponse(BaseModel):
    """Response model for user"""
    id: str
    email: str
    name: str
    created_at: str
    
    class Config:
        from_attributes = True


class UserController:
    """
    User Controller
    
    Handles HTTP requests and delegates to use cases.
    """
    
    def __init__(
        self,
        create_user_use_case: CreateUserUseCase,
        get_user_use_case: GetUserUseCase
    ):
        self.create_user_use_case = create_user_use_case
        self.get_user_use_case = get_user_use_case
    
    async def create_user(self, request: CreateUserRequest) -> UserResponse:
        """
        POST /users
        Creates a new user
        """
        try:
            dto = CreateUserDto(
                email=request.email,
                name=request.name
            )
            user = await self.create_user_use_case.execute(dto)
            
            return UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                created_at=user.created_at.isoformat()
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def get_user(self, user_id: str) -> UserResponse:
        """
        GET /users/{user_id}
        Gets a user by ID
        """
        try:
            user = await self.get_user_use_case.execute(user_id)
            return UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                created_at=user.created_at.isoformat()
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
```

### Step 3: FastAPI Routers

**File: `src/presentation/routers/user_router.py`**

```python
"""
FastAPI Router for User endpoints
"""
from fastapi import APIRouter
from ..controllers.user_controller import UserController, CreateUserRequest, UserResponse


def create_user_router(user_controller: UserController) -> APIRouter:
    """
    Create user router with endpoints
    
    Args:
        user_controller: User controller instance
        
    Returns:
        Configured FastAPI router
    """
    router = APIRouter(prefix='/users', tags=['users'])
    
    @router.post('/', response_model=UserResponse, status_code=201)
    async def create_user(request: CreateUserRequest):
        """Create a new user"""
        return await user_controller.create_user(request)
    
    @router.get('/{user_id}', response_model=UserResponse)
    async def get_user(user_id: str):
        """Get user by ID"""
        return await user_controller.get_user(user_id)
    
    return router
```

### Step 4: Application Entry Point

**File: `src/main.py`**

```python
"""
Application Entry Point

Sets up FastAPI server and initializes all components.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from .infrastructure.di.container import Container
from .presentation.routers.user_router import create_user_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global container
container = Container()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info('Starting application...')
    await container.initialize()
    logger.info('Application started')
    
    yield
    
    # Shutdown
    logger.info('Shutting down application...')
    await container.cleanup()
    logger.info('Application shut down')


# Create FastAPI app
app = FastAPI(
    title='User Service',
    description='Microservice example with Clean Architecture, Caching, and Message Queue',
    version='1.0.0',
    lifespan=lifespan
)

# Register routes
app.include_router(create_user_router(container.user_controller))


@app.get('/health')
async def health_check():
    """Health check endpoint"""
    return {'status': 'ok'}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
```

### Step 5: Configuration Files

**File: `requirements.txt`**

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0
redis==5.0.1
aio-pika==9.3.0
pika==1.3.2
```

**File: `pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.black]
line-length = 100
target-version = ['py310']

[tool.isort]
profile = "black"
line_length = 100
```

**File: `.env.example`**

```env
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

### Step 6: Docker Compose for Dependencies

**File: `docker-compose.yml`**

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports:
      - "5672:5672"
      - "15672:15672"  # Management UI
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    volumes:
      - rabbitmq-data:/data

volumes:
  redis-data:
  rabbitmq-data:
```

### Running the Application

```bash
# Start dependencies
docker-compose up -d

# Install dependencies
pip install -r requirements.txt

# Run in development
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or use Python directly
python -m src.main
```

### API Documentation

FastAPI automatically generates interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Key Concepts Explained

### Clean Architecture Benefits

1. **Independence**: Business logic doesn't depend on FastAPI, Redis, or RabbitMQ
2. **Testability**: Easy to mock interfaces and test use cases
3. **Flexibility**: Swap Redis for Memcached without changing business logic
4. **Maintainability**: Clear separation makes code easier to understand

### Distributed Caching Pattern

The `get_or_set` pattern (like FusionCache) provides:
- **Cache-aside**: Check cache first, fallback to database
- **Automatic caching**: Factory function only runs on cache miss
- **TTL support**: Automatic expiration
- **Prevents cache stampede**: Only one request executes factory on cache miss

### Message Queue Pattern

The message bus abstraction (like MassTransit) provides:
- **Decoupling**: Services communicate via events, not direct calls
- **Reliability**: Messages are persisted and retried on failure
- **Scalability**: Multiple consumers can process messages in parallel
- **Event-driven architecture**: Services react to events asynchronously

### Async/Await in Python

Python's `async/await` syntax allows:
- **Non-blocking I/O**: Handle multiple requests concurrently
- **Better performance**: Especially for I/O-bound operations (database, cache, MQ)
- **Clean code**: Similar to C# async/await or JavaScript async/await

---

## Next Steps

1. Add request validation with Pydantic models
2. Add error handling middleware
3. Add logging (structlog or python-json-logger)
4. Add unit tests (pytest)
5. Add integration tests
6. Implement database persistence (SQLAlchemy, Tortoise ORM)
7. Add API authentication (JWT, OAuth2)
8. Add monitoring (Prometheus, Grafana)
9. Add distributed tracing (OpenTelemetry)

---

## Summary

You've learned:
- ✅ Clean Architecture with Python
- ✅ Distributed caching with Redis (FusionCache-like)
- ✅ Message queue with RabbitMQ (MassTransit-like)
- ✅ How to structure a microservice with FastAPI
- ✅ Async/await patterns for I/O operations

This architecture is production-ready and can scale horizontally!
