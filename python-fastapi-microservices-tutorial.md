# Microservices Architecture Tutorial: Python + FastAPI

## Table of Contents
1. [Introduction](#introduction)
2. [Project Setup](#project-setup)
3. [Clean Architecture Overview](#clean-architecture-overview)
4. [Implementing Clean Architecture](#implementing-clean-architecture)
5. [Distributed Caching with Redis](#distributed-caching-with-redis)
6. [Message Queue with RabbitMQ](#message-queue-with-rabbitmq)
7. [Complete Microservice Example](#complete-microservice-example)
8. [Best Practices](#best-practices)

---

## Introduction

This tutorial will guide you through building a microservices architecture using Python and FastAPI. We'll implement:

- **Clean Architecture**: Separation of concerns with clear layer boundaries
- **Distributed Caching**: Using Redis with aiocache (similar to FusionCache in .NET)
- **Message Queue**: Using aio-pika with RabbitMQ (similar to MassTransit in .NET)

### Prerequisites
- Python 3.10+ installed
- Basic knowledge of Python and FastAPI
- Docker installed (for Redis and RabbitMQ)

---

## Project Setup

### Step 1: Create Project Structure

```bash
mkdir microservices-tutorial
cd microservices-tutorial
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

Create `requirements.txt`:

```txt
# Web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Distributed caching
redis==5.0.1
aiocache==0.12.2
hiredis==2.2.3

# Message queue
aio-pika==9.2.0

# Utilities
python-dotenv==1.0.0
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### Step 4: Project Structure

```
microservices-tutorial/
├── src/
│   ├── domain/           # Business logic and entities
│   │   ├── entities/
│   │   └── interfaces/
│   ├── application/      # Use cases
│   │   └── usecases/
│   ├── infrastructure/   # External concerns
│   │   ├── cache/
│   │   ├── messaging/
│   │   └── repositories/
│   ├── presentation/     # API layer
│   │   ├── controllers/
│   │   ├── middleware/
│   │   └── routes/
│   └── shared/           # Shared utilities
│       └── types/
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

## Clean Architecture Overview

Clean Architecture organizes code into layers with clear dependencies:

```
┌─────────────────────────────────────┐
│      Presentation Layer             │  ← Controllers, Routes
├─────────────────────────────────────┤
│      Application Layer              │  ← Use Cases, DTOs
├─────────────────────────────────────┤
│      Domain Layer                   │  ← Entities, Interfaces
├─────────────────────────────────────┤
│      Infrastructure Layer           │  ← Database, Cache, Messaging
└─────────────────────────────────────┘
```

**Key Principles:**
- **Dependency Rule**: Inner layers don't depend on outer layers
- **Separation of Concerns**: Each layer has a single responsibility
- **Testability**: Easy to mock dependencies

---

## Implementing Clean Architecture

### Step 1: Domain Layer - Entities

Create `src/domain/entities/user.py`:

```python
"""
Domain Entity: User

This represents the core business entity. It contains only business logic
and has no dependencies on external frameworks or libraries.
"""
from datetime import datetime
from typing import Optional
import re


class User:
    """
    User domain entity with business logic.
    
    This is a pure Python class with no framework dependencies.
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
    
    def is_valid_email(self) -> bool:
        """
        Business logic: Validate user email format
        
        Returns:
            bool: True if email format is valid
        """
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        return bool(re.match(email_regex, self.email))
    
    def is_recently_created(self, days: int = 7) -> bool:
        """
        Business logic: Check if user is recently created
        
        Args:
            days: Number of days to consider as "recent"
            
        Returns:
            bool: True if user was created within the specified days
        """
        days_since_creation = (datetime.now() - self.created_at).days
        return days_since_creation <= days
    
    def to_dict(self) -> dict:
        """
        Convert entity to dictionary (for serialization)
        
        Returns:
            dict: Dictionary representation of the user
        """
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat()
        }
```

### Step 2: Domain Layer - Repository Interfaces

Create `src/domain/interfaces/user_repository.py`:

```python
"""
Repository Interface (Domain Layer)

This interface defines what operations we need, not how they're implemented.
The implementation will be in the Infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import Optional
from src.domain.entities.user import User


class IUserRepository(ABC):
    """
    User repository interface.
    
    This abstraction allows us to swap implementations
    without changing business logic.
    """
    
    @abstractmethod
    async def find_by_id(self, user_id: str) -> Optional[User]:
        """
        Find user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            User if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email.
        
        Args:
            email: User email address
            
        Returns:
            User if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def save(self, user: User) -> User:
        """
        Save user (create or update).
        
        Args:
            user: User entity to save
            
        Returns:
            Saved user entity
        """
        pass
    
    @abstractmethod
    async def delete(self, user_id: str) -> None:
        """
        Delete user by ID.
        
        Args:
            user_id: User identifier
        """
        pass
```

### Step 3: Application Layer - Use Cases

Create `src/application/usecases/get_user_usecase.py`:

```python
"""
Use Case: Get User by ID

This orchestrates the business logic:
1. Check cache first
2. If not in cache, fetch from repository
3. Store in cache for future requests
"""
from typing import Optional
from src.domain.entities.user import User
from src.domain.interfaces.user_repository import IUserRepository
from src.domain.interfaces.cache_service import ICacheService


class GetUserUseCase:
    """
    Use case for retrieving a user by ID.
    
    Implements cache-aside pattern for distributed caching.
    """
    
    def __init__(
        self,
        user_repository: IUserRepository,
        cache_service: ICacheService
    ):
        self.user_repository = user_repository
        self.cache_service = cache_service
    
    async def execute(self, user_id: str) -> Optional[User]:
        """
        Execute the use case.
        
        Args:
            user_id: User identifier
            
        Returns:
            User if found, None otherwise
        """
        # Check cache first (distributed caching)
        cache_key = f"user:{user_id}"
        cached_user = await self.cache_service.get(cache_key)
        
        if cached_user:
            print(f"Cache hit for user {user_id}")
            # Reconstruct User object from cached data
            return User(
                id=cached_user['id'],
                email=cached_user['email'],
                name=cached_user['name'],
                created_at=cached_user['created_at']
            )
        
        # Cache miss - fetch from repository
        print(f"Cache miss for user {user_id}")
        user = await self.user_repository.find_by_id(user_id)
        
        if user:
            # Store in cache for 1 hour (3600 seconds)
            await self.cache_service.set(
                cache_key,
                user.to_dict(),
                ttl=3600
            )
        
        return user
```

Create `src/application/usecases/create_user_usecase.py`:

```python
"""
Use Case: Create User

This demonstrates:
1. Business logic validation
2. Repository interaction
3. Event publishing (message queue)
"""
from datetime import datetime
import uuid
import re
from src.domain.entities.user import User
from src.domain.interfaces.user_repository import IUserRepository
from src.domain.interfaces.message_publisher import IMessagePublisher


class CreateUserUseCase:
    """
    Use case for creating a new user.
    
    Handles validation, persistence, and event publishing.
    """
    
    def __init__(
        self,
        user_repository: IUserRepository,
        message_publisher: IMessagePublisher
    ):
        self.user_repository = user_repository
        self.message_publisher = message_publisher
    
    async def execute(self, email: str, name: str) -> User:
        """
        Execute the use case.
        
        Args:
            email: User email address
            name: User name
            
        Returns:
            Created user entity
            
        Raises:
            ValueError: If validation fails or user already exists
        """
        # Business logic validation
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, email):
            raise ValueError('Invalid email format')
        
        if not name or not name.strip():
            raise ValueError('Name is required')
        
        # Check if user already exists
        existing_user = await self.user_repository.find_by_email(email)
        if existing_user:
            raise ValueError('User with this email already exists')
        
        # Create new user
        user = User(
            id=self._generate_id(),
            email=email,
            name=name,
            created_at=datetime.now()
        )
        
        # Save to repository
        saved_user = await self.user_repository.save(user)
        
        # Publish event to message queue (asynchronous processing)
        await self.message_publisher.publish(
            routing_key='user.created',
            message={
                'user_id': saved_user.id,
                'email': saved_user.email,
                'name': saved_user.name,
                'timestamp': saved_user.created_at.isoformat()
            }
        )
        
        return saved_user
    
    def _generate_id(self) -> str:
        """
        Generate unique user ID.
        
        Returns:
            str: Unique identifier
        """
        return f"user_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:9]}"
```

### Step 4: Infrastructure Layer - Cache Service

Create `src/infrastructure/cache/redis_cache_service.py`:

```python
"""
Redis Cache Service Implementation

This is similar to FusionCache in .NET:
- Distributed caching across multiple instances
- TTL (Time To Live) support
- Automatic serialization/deserialization
"""
import json
from typing import Optional, Any
import redis.asyncio as redis
from src.domain.interfaces.cache_service import ICacheService


class RedisCacheService(ICacheService):
    """
    Redis-based distributed cache service.
    
    Provides distributed caching capabilities similar to FusionCache.
    """
    
    def __init__(self, redis_url: str):
        """
        Initialize Redis cache service.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis = await redis.from_url(
                self.redis_url,
                decode_responses=False  # We'll handle JSON ourselves
            )
            # Test connection
            await self.redis.ping()
            print('Connected to Redis')
        except Exception as e:
            print(f'Redis connection error: {e}')
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            print('Disconnected from Redis')
    
    async def get(self, key: str) -> Optional[dict]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value as dictionary, or None if not found
        """
        if not self.redis:
            raise RuntimeError('Redis not connected. Call connect() first.')
        
        try:
            value = await self.redis.get(key)
            if not value:
                return None
            return json.loads(value)
        except Exception as e:
            print(f'Cache get error for key {key}: {e}')
            return None  # Fail gracefully
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (optional)
        """
        if not self.redis:
            raise RuntimeError('Redis not connected. Call connect() first.')
        
        try:
            serialized = json.dumps(value)
            if ttl:
                await self.redis.setex(key, ttl, serialized)
            else:
                await self.redis.set(key, serialized)
        except Exception as e:
            print(f'Cache set error for key {key}: {e}')
            # Fail gracefully - don't throw
    
    async def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
        """
        if not self.redis:
            raise RuntimeError('Redis not connected. Call connect() first.')
        
        try:
            await self.redis.delete(key)
        except Exception as e:
            print(f'Cache delete error for key {key}: {e}')
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.redis:
            raise RuntimeError('Redis not connected. Call connect() first.')
        
        try:
            result = await self.redis.exists(key)
            return bool(result)
        except Exception as e:
            print(f'Cache exists error for key {key}: {e}')
            return False
    
    async def clear(self) -> None:
        """
        Clear all cache (use with caution!).
        """
        if not self.redis:
            raise RuntimeError('Redis not connected. Call connect() first.')
        
        try:
            await self.redis.flushdb()
        except Exception as e:
            print(f'Cache clear error: {e}')
```

### Step 5: Infrastructure Layer - Message Queue Service

Create `src/infrastructure/messaging/rabbitmq_service.py`:

```python
"""
RabbitMQ Service Implementation

This is similar to MassTransit in .NET:
- Publish/subscribe pattern
- Queue management
- Message routing
- Consumer handling
"""
import json
from typing import Callable, Awaitable, Optional
import aio_pika
from aio_pika import Connection, Channel, Exchange, Queue
from src.domain.interfaces.message_publisher import IMessagePublisher, IMessageConsumer


class RabbitMQService(IMessagePublisher, IMessageConsumer):
    """
    RabbitMQ service for message publishing and consuming.
    
    Provides capabilities similar to MassTransit in .NET.
    """
    
    def __init__(self, connection_url: str):
        """
        Initialize RabbitMQ service.
        
        Args:
            connection_url: RabbitMQ connection URL
        """
        self.connection_url = connection_url
        self.connection: Optional[Connection] = None
        self.channel: Optional[Channel] = None
        self.exchange: Optional[Exchange] = None
        self.exchange_name = 'microservices_exchange'
        self.exchange_type = aio_pika.ExchangeType.TOPIC
    
    async def connect(self) -> None:
        """Connect to RabbitMQ and set up exchange."""
        try:
            self.connection = await aio_pika.connect_robust(self.connection_url)
            self.channel = await self.connection.channel()
            
            # Declare exchange (similar to MassTransit's exchange)
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                self.exchange_type,
                durable=True  # Survive broker restarts
            )
            
            print('Connected to RabbitMQ')
        except Exception as e:
            print(f'RabbitMQ connection error: {e}')
            raise
    
    async def disconnect(self) -> None:
        """Close connections."""
        try:
            if self.channel:
                await self.channel.close()
            if self.connection:
                await self.connection.close()
            print('Disconnected from RabbitMQ')
        except Exception as e:
            print(f'Error disconnecting from RabbitMQ: {e}')
    
    async def publish(self, routing_key: str, message: dict) -> None:
        """
        Publish message to exchange.
        
        Similar to MassTransit's Publish method.
        
        Args:
            routing_key: Message routing key
            message: Message payload as dictionary
        """
        if not self.exchange:
            raise RuntimeError(
                'RabbitMQ not connected. Call connect() first.'
            )
        
        try:
            message_body = json.dumps(message).encode()
            
            await self.exchange.publish(
                aio_pika.Message(
                    message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    timestamp=aio_pika.MessageTimestamp.now()
                ),
                routing_key=routing_key
            )
            
            print(f'Published message to {routing_key}: {message}')
        except Exception as e:
            print(f'Error publishing message to {routing_key}: {e}')
            raise
    
    async def subscribe(
        self,
        queue_name: str,
        routing_key: str,
        handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        """
        Subscribe to messages.
        
        Similar to MassTransit's Consumer.
        
        Args:
            queue_name: Name of the queue
            routing_key: Routing key to bind to
            handler: Async function to handle messages
        """
        if not self.channel or not self.exchange:
            raise RuntimeError(
                'RabbitMQ not connected. Call connect() first.'
            )
        
        try:
            # Declare queue
            queue = await self.channel.declare_queue(
                queue_name,
                durable=True  # Queue survives broker restarts
            )
            
            # Bind queue to exchange with routing key
            await queue.bind(self.exchange, routing_key=routing_key)
            
            # Consume messages
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        try:
                            content = json.loads(message.body.decode())
                            print(f'Received message on {queue_name}: {content}')
                            
                            # Process message
                            await handler(content)
                            
                            # Message is automatically acknowledged
                        except Exception as e:
                            print(f'Error processing message on {queue_name}: {e}')
                            # Message will be requeued if not acknowledged
                            raise  # Re-raise to requeue
            
            print(f'Subscribed to queue {queue_name} with routing key {routing_key}')
        except Exception as e:
            print(f'Error subscribing to {queue_name}: {e}')
            raise
```

### Step 6: Domain Interfaces for Infrastructure

Create `src/domain/interfaces/cache_service.py`:

```python
"""
Cache Service Interface

This abstraction allows us to swap cache implementations
without changing business logic.
"""
from abc import ABC, abstractmethod
from typing import Optional, Any


class ICacheService(ABC):
    """Interface for cache service."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[dict]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value, or None if not found
        """
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache."""
        pass
```

Create `src/domain/interfaces/message_publisher.py`:

```python
"""
Message Publisher/Consumer Interfaces

These abstractions allow us to swap messaging implementations
without changing business logic.
"""
from abc import ABC, abstractmethod
from typing import Callable, Awaitable


class IMessagePublisher(ABC):
    """Interface for message publishing."""
    
    @abstractmethod
    async def publish(self, routing_key: str, message: dict) -> None:
        """
        Publish message.
        
        Args:
            routing_key: Message routing key
            message: Message payload
        """
        pass


class IMessageConsumer(ABC):
    """Interface for message consuming."""
    
    @abstractmethod
    async def subscribe(
        self,
        queue_name: str,
        routing_key: str,
        handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        """
        Subscribe to messages.
        
        Args:
            queue_name: Queue name
            routing_key: Routing key to bind to
            handler: Async function to handle messages
        """
        pass
```

### Step 7: Infrastructure Layer - Repository Implementation

Create `src/infrastructure/repositories/in_memory_user_repository.py`:

```python
"""
In-Memory User Repository

For simplicity, we're using in-memory storage.
In production, this would connect to a database.
"""
from typing import Optional
from src.domain.entities.user import User
from src.domain.interfaces.user_repository import IUserRepository


class InMemoryUserRepository(IUserRepository):
    """
    In-memory implementation of user repository.
    
    Uses a dictionary for storage. In production, replace with
    database-backed implementation.
    """
    
    def __init__(self):
        """Initialize repository with empty storage."""
        self._users: dict[str, User] = {}
    
    async def find_by_id(self, user_id: str) -> Optional[User]:
        """Find user by ID."""
        return self._users.get(user_id)
    
    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email."""
        for user in self._users.values():
            if user.email == email:
                return user
        return None
    
    async def save(self, user: User) -> User:
        """Save user (create or update)."""
        self._users[user.id] = user
        return user
    
    async def delete(self, user_id: str) -> None:
        """Delete user by ID."""
        self._users.pop(user_id, None)
```

### Step 8: Presentation Layer - Controllers

Create `src/presentation/controllers/user_controller.py`:

```python
"""
User Controller

This handles HTTP requests and delegates to use cases.
It's part of the Presentation layer.
"""
from fastapi import HTTPException
from src.application.usecases.get_user_usecase import GetUserUseCase
from src.application.usecases.create_user_usecase import CreateUserUseCase


class UserController:
    """
    Controller for user-related endpoints.
    
    Handles HTTP request/response and delegates to use cases.
    """
    
    def __init__(
        self,
        get_user_usecase: GetUserUseCase,
        create_user_usecase: CreateUserUseCase
    ):
        self.get_user_usecase = get_user_usecase
        self.create_user_usecase = create_user_usecase
    
    async def get_user(self, user_id: str) -> dict:
        """
        Get user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            User data as dictionary
            
        Raises:
            HTTPException: If user not found
        """
        try:
            user = await self.get_user_usecase.execute(user_id)
            
            if not user:
                raise HTTPException(
                    status_code=404,
                    detail='User not found'
                )
            
            return {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'created_at': user.created_at.isoformat()
            }
        except Exception as e:
            print(f'Error getting user: {e}')
            raise HTTPException(
                status_code=500,
                detail='Internal server error'
            )
    
    async def create_user(self, email: str, name: str) -> dict:
        """
        Create new user.
        
        Args:
            email: User email address
            name: User name
            
        Returns:
            Created user data as dictionary
            
        Raises:
            HTTPException: If validation fails or user already exists
        """
        try:
            user = await self.create_user_usecase.execute(email, name)
            
            return {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'created_at': user.created_at.isoformat()
            }
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        except Exception as e:
            print(f'Error creating user: {e}')
            raise HTTPException(
                status_code=500,
                detail='Internal server error'
            )
```

### Step 9: Presentation Layer - Routes

Create `src/presentation/routes/user_routes.py`:

```python
"""
User Routes

FastAPI route definitions for user endpoints.
"""
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from src.presentation.controllers.user_controller import UserController


class CreateUserRequest(BaseModel):
    """Request model for creating a user."""
    email: EmailStr
    name: str


def create_user_routes(user_controller: UserController) -> APIRouter:
    """
    Create user routes.
    
    Args:
        user_controller: User controller instance
        
    Returns:
        Configured FastAPI router
    """
    router = APIRouter(prefix='/users', tags=['users'])
    
    @router.get('/{user_id}')
    async def get_user(user_id: str):
        """Get user by ID."""
        return await user_controller.get_user(user_id)
    
    @router.post('/', status_code=201)
    async def create_user(request: CreateUserRequest):
        """Create new user."""
        return await user_controller.create_user(
            email=request.email,
            name=request.name
        )
    
    return router
```

### Step 10: Application Entry Point

Create `src/main.py`:

```python
"""
Application Entry Point

Sets up FastAPI application with all dependencies.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import os

from src.infrastructure.repositories.in_memory_user_repository import (
    InMemoryUserRepository
)
from src.infrastructure.cache.redis_cache_service import RedisCacheService
from src.infrastructure.messaging.rabbitmq_service import RabbitMQService
from src.application.usecases.get_user_usecase import GetUserUseCase
from src.application.usecases.create_user_usecase import CreateUserUseCase
from src.presentation.controllers.user_controller import UserController
from src.presentation.routes.user_routes import create_user_routes

load_dotenv()


# Global instances (will be initialized in lifespan)
cache_service: RedisCacheService = None
message_service: RabbitMQService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    
    Handles startup and shutdown logic.
    """
    # Startup
    global cache_service, message_service
    
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    rabbitmq_url = os.getenv(
        'RABBITMQ_URL',
        'amqp://guest:guest@localhost:5672/'
    )
    
    # Initialize infrastructure services
    cache_service = RedisCacheService(redis_url)
    message_service = RabbitMQService(rabbitmq_url)
    
    # Connect to services
    await cache_service.connect()
    await message_service.connect()
    
    # Initialize repositories
    user_repository = InMemoryUserRepository()
    
    # Initialize use cases
    get_user_usecase = GetUserUseCase(user_repository, cache_service)
    create_user_usecase = CreateUserUseCase(
        user_repository,
        message_service
    )
    
    # Initialize controllers
    user_controller = UserController(
        get_user_usecase,
        create_user_usecase
    )
    
    # Setup routes
    app.include_router(create_user_routes(user_controller))
    
    # Setup message consumer in background
    async def handle_user_created(message: dict):
        """Handle user.created event."""
        print(f'Processing user.created event: {message}')
        # Here you could:
        # - Send welcome email
        # - Update analytics
        # - Notify other services
        # - etc.
    
    # Start consumer in background task
    async def consume_messages():
        """Background task for consuming messages."""
        try:
            await message_service.subscribe(
                queue_name='user_created_queue',
                routing_key='user.created',
                handler=handle_user_created
            )
        except Exception as e:
            print(f'Error in message consumer: {e}')
    
    # Start consumer task
    consumer_task = asyncio.create_task(consume_messages())
    
    yield  # Application runs here
    
    # Shutdown
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    
    await cache_service.disconnect()
    await message_service.disconnect()


# Create FastAPI app
app = FastAPI(
    title='Microservices Tutorial',
    description='FastAPI microservices with Clean Architecture',
    version='1.0.0',
    lifespan=lifespan
)


@app.get('/health')
async def health_check():
    """Health check endpoint."""
    return {
        'status': 'ok',
        'timestamp': __import__('datetime').datetime.now().isoformat()
    }
```

### Step 11: Environment Configuration

Create `.env`:

```env
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

### Step 12: Docker Compose for Services

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports:
      - "5672:5672"    # AMQP port
      - "15672:15672"  # Management UI
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

volumes:
  redis_data:
  rabbitmq_data:
```

### Step 13: Create __init__.py Files

Create `src/__init__.py`:
```python
# Empty file to make src a package
```

Create `src/domain/__init__.py`:
```python
# Empty file
```

Create `src/domain/entities/__init__.py`:
```python
# Empty file
```

Create `src/domain/interfaces/__init__.py`:
```python
# Empty file
```

Create `src/application/__init__.py`:
```python
# Empty file
```

Create `src/application/usecases/__init__.py`:
```python
# Empty file
```

Create `src/infrastructure/__init__.py`:
```python
# Empty file
```

Create `src/infrastructure/cache/__init__.py`:
```python
# Empty file
```

Create `src/infrastructure/messaging/__init__.py`:
```python
# Empty file
```

Create `src/infrastructure/repositories/__init__.py`:
```python
# Empty file
```

Create `src/presentation/__init__.py`:
```python
# Empty file
```

Create `src/presentation/controllers/__init__.py`:
```python
# Empty file
```

Create `src/presentation/routes/__init__.py`:
```python
# Empty file
```

---

## Complete Microservice Example

### Running the Application

1. **Start infrastructure services:**
```bash
docker-compose up -d
```

2. **Start the application:**
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

3. **Access API documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

4. **Test the API:**

Create a user:
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "name": "John Doe"}'
```

Get a user (with caching):
```bash
curl http://localhost:8000/users/{userId}
```

### How It Works

1. **Clean Architecture Flow:**
   - Request → Controller → Use Case → Repository/Cache/Message Queue
   - Each layer has clear responsibilities
   - Easy to test and maintain

2. **Distributed Caching:**
   - First request: Cache miss → Fetch from repository → Store in cache
   - Subsequent requests: Cache hit → Return from cache
   - Works across multiple service instances

3. **Message Queue:**
   - User created → Event published to RabbitMQ
   - Consumer processes event asynchronously
   - Enables loose coupling between services

---

## Best Practices

### 1. Error Handling
- Use FastAPI's HTTPException for HTTP errors
- Handle exceptions at appropriate layers
- Log errors for debugging

### 2. Caching Strategy
- Use appropriate TTL values
- Invalidate cache on updates
- Consider cache-aside pattern

### 3. Message Queue Patterns
- Use idempotent handlers
- Implement retry logic
- Handle dead letter queues

### 4. Testing
- Unit test use cases
- Integration test with real services
- Mock external dependencies

### 5. Monitoring
- Log important operations
- Monitor cache hit rates
- Track message processing times

### 6. Async/Await
- Use async/await throughout
- Don't block the event loop
- Use proper connection pooling

---

## Summary

This tutorial demonstrated:

✅ **Clean Architecture**: Clear separation of concerns across layers  
✅ **Distributed Caching**: Redis implementation similar to FusionCache  
✅ **Message Queue**: RabbitMQ implementation similar to MassTransit  
✅ **FastAPI**: Modern, fast web framework with automatic API docs  
✅ **Python**: Clean, readable code with type hints  

The architecture is scalable, maintainable, and follows industry best practices for microservices.
