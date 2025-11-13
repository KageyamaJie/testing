# Microservices Architecture Tutorial: Python + FastAPI

## Table of Contents
1. [Introduction](#introduction)
2. [Project Setup](#project-setup)
3. [Clean Architecture Implementation](#clean-architecture-implementation)
4. [Distributed Caching with Redis](#distributed-caching-with-redis)
5. [Message Queue with RabbitMQ](#message-queue-with-rabbitmq)
6. [Complete Example: User Service](#complete-example-user-service)

---

## Introduction

This tutorial guides you through building microservices using **Python** and **FastAPI** following **Clean Architecture** principles. We'll implement:
- **Clean Architecture** for maintainable, testable code
- **Distributed Caching** using Redis (similar to FusionCache in .NET)
- **Message Queue** using RabbitMQ (similar to MassTransit in .NET)

### Prerequisites
- Python 3.10+ installed
- Basic knowledge of Python and FastAPI
- Docker installed (for Redis and RabbitMQ)

---

## Project Setup

### Step 1: Create Project Structure

```bash
mkdir microservices-python
cd microservices-python
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install fastapi uvicorn[standard] pydantic python-dotenv
pip install redis pika  # Redis and RabbitMQ clients
```

### Step 3: Project Structure

```
microservices-python/
├── src/
│   ├── domain/           # Business logic (entities, use cases)
│   ├── application/      # Application services
│   ├── infrastructure/   # External concerns (DB, cache, message queue)
│   ├── presentation/     # Controllers, routes
│   └── shared/           # Shared utilities
├── requirements.txt
└── main.py
```

---

## Clean Architecture Implementation

Clean Architecture separates code into layers with clear dependencies:

```
┌─────────────────────────────────────┐
│   Presentation Layer (Controllers)  │
├─────────────────────────────────────┤
│   Application Layer (Use Cases)     │
├─────────────────────────────────────┤
│   Domain Layer (Entities, Logic)    │
├─────────────────────────────────────┤
│   Infrastructure (DB, Cache, MQ)    │
└─────────────────────────────────────┘
```

### Domain Layer: Entities

**`src/domain/entities/user.py`**

```python
"""
Domain Entity: User

This is the core business entity. It contains:
- Business rules and validation
- No dependencies on external frameworks
- Pure business logic
"""
from datetime import datetime
from typing import Optional
import re


class User:
    """
    User domain entity
    
    This class represents a user in our domain.
    It contains business logic and validation rules.
    """
    
    def __init__(self, user_id: str, email: str, name: str, created_at: datetime):
        """
        Initialize a User entity
        
        Args:
            user_id: Unique identifier
            email: User email (will be validated)
            name: User name
            created_at: Creation timestamp
        """
        # Business rule: Email must be valid
        if not self._is_valid_email(email):
            raise ValueError('Invalid email format')
        
        self.id = user_id
        self.email = email
        self.name = name
        self.created_at = created_at
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """
        Business logic: Validate email format
        
        This is domain logic, not infrastructure concern.
        """
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        return bool(re.match(email_regex, email))
    
    def is_active(self) -> bool:
        """
        Business logic: Check if user is active
        
        Business rule: User is active if created within last 30 days
        """
        from datetime import timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        return self.created_at >= thirty_days_ago
    
    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, name={self.name})"
```

### Domain Layer: Repository Interface

**`src/domain/repositories/user_repository.py`**

```python
"""
Repository Interface (Port)

This defines WHAT we need, not HOW it's implemented.
Infrastructure layer will implement this interface.
This follows Dependency Inversion Principle.
"""
from abc import ABC, abstractmethod
from typing import Optional
from ..entities.user import User


class IUserRepository(ABC):
    """
    User Repository Interface
    
    This abstract class defines the contract for user persistence.
    Concrete implementations will be in the infrastructure layer.
    """
    
    @abstractmethod
    async def find_by_id(self, user_id: str) -> Optional[User]:
        """
        Find user by ID
        
        Args:
            user_id: User identifier
            
        Returns:
            User entity or None if not found
        """
        pass
    
    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email
        
        Args:
            email: User email
            
        Returns:
            User entity or None if not found
        """
        pass
    
    @abstractmethod
    async def save(self, user: User) -> User:
        """
        Save user (create or update)
        
        Args:
            user: User entity to save
            
        Returns:
            Saved user entity
        """
        pass
    
    @abstractmethod
    async def delete(self, user_id: str) -> None:
        """
        Delete user by ID
        
        Args:
            user_id: User identifier
        """
        pass
```

### Application Layer: Use Cases

**`src/application/use_cases/create_user_use_case.py`**

```python
"""
Use Case: Create User

This contains application-specific business logic:
- Orchestrates domain entities
- Coordinates with repositories
- Handles application-level concerns
"""
import uuid
from datetime import datetime
from typing import Optional
from ...domain.entities.user import User
from ...domain.repositories.user_repository import IUserRepository


class CreateUserUseCase:
    """
    Create User Use Case
    
    This use case handles the business logic for creating a new user.
    """
    
    def __init__(self, user_repository: IUserRepository):
        """
        Initialize use case with repository
        
        Args:
            user_repository: User repository implementation
        """
        self.user_repository = user_repository
    
    async def execute(self, email: str, name: str) -> User:
        """
        Execute the use case
        
        This method:
        1. Creates domain entity (User)
        2. Validates business rules (handled by User entity)
        3. Persists via repository
        4. Returns result
        
        Args:
            email: User email
            name: User name
            
        Returns:
            Created User entity
            
        Raises:
            ValueError: If user already exists or validation fails
        """
        # Check if user already exists
        existing_user = await self.user_repository.find_by_email(email)
        if existing_user:
            raise ValueError('User with this email already exists')
        
        # Create domain entity
        user = User(
            user_id=self._generate_id(),
            email=email,
            name=name,
            created_at=datetime.now()
        )
        
        # Persist via repository
        return await self.user_repository.save(user)
    
    def _generate_id(self) -> str:
        """
        Generate unique user ID
        
        Returns:
            Unique identifier string
        """
        return f"user_{uuid.uuid4().hex[:12]}"
```

**`src/application/use_cases/get_user_use_case.py`**

```python
"""
Use Case: Get User by ID

This use case demonstrates:
- Simple data retrieval
- Error handling
- Application-level logic
"""
from typing import Optional
from ...domain.entities.user import User
from ...domain.repositories.user_repository import IUserRepository


class GetUserUseCase:
    """
    Get User Use Case
    
    Retrieves a user by their ID.
    """
    
    def __init__(self, user_repository: IUserRepository):
        """
        Initialize use case with repository
        
        Args:
            user_repository: User repository implementation
        """
        self.user_repository = user_repository
    
    async def execute(self, user_id: str) -> User:
        """
        Execute the use case
        
        Args:
            user_id: User identifier
            
        Returns:
            User entity
            
        Raises:
            ValueError: If user not found
        """
        user = await self.user_repository.find_by_id(user_id)
        
        if not user:
            raise ValueError('User not found')
        
        return user
```

### Infrastructure Layer: Repository Implementation

**`src/infrastructure/repositories/user_repository_impl.py`**

```python
"""
Repository Implementation (Adapter)

This implements the repository interface using:
- In-memory storage (for simplicity)
- In production, this would use PostgreSQL, MongoDB, etc.

Key point: Domain layer doesn't know about this implementation!
"""
from typing import Optional, Dict
from ...domain.entities.user import User
from ...domain.repositories.user_repository import IUserRepository


class UserRepositoryImpl(IUserRepository):
    """
    In-Memory User Repository Implementation
    
    This is a simple implementation for demonstration.
    In production, replace with database-backed implementation.
    """
    
    def __init__(self):
        """
        Initialize repository with empty storage
        """
        self._users: Dict[str, User] = {}
    
    async def find_by_id(self, user_id: str) -> Optional[User]:
        """
        Find user by ID
        
        Args:
            user_id: User identifier
            
        Returns:
            User entity or None
        """
        return self._users.get(user_id)
    
    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email
        
        Args:
            email: User email
            
        Returns:
            User entity or None
        """
        for user in self._users.values():
            if user.email == email:
                return user
        return None
    
    async def save(self, user: User) -> User:
        """
        Save user (create or update)
        
        Args:
            user: User entity to save
            
        Returns:
            Saved user entity
        """
        self._users[user.id] = user
        return user
    
    async def delete(self, user_id: str) -> None:
        """
        Delete user by ID
        
        Args:
            user_id: User identifier
        """
        self._users.pop(user_id, None)
```

### Presentation Layer: DTOs (Data Transfer Objects)

**`src/presentation/dtos/user_dto.py`**

```python
"""
Data Transfer Objects (DTOs)

DTOs are used for API request/response serialization.
They separate API contracts from domain entities.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime


class CreateUserRequest(BaseModel):
    """
    Request DTO for creating a user
    """
    email: EmailStr
    name: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com",
                "name": "John Doe"
            }
        }


class UserResponse(BaseModel):
    """
    Response DTO for user data
    """
    id: str
    email: str
    name: str
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "user_abc123",
                "email": "john@example.com",
                "name": "John Doe",
                "created_at": "2024-01-01T00:00:00"
            }
        }
```

### Presentation Layer: Controller

**`src/presentation/controllers/user_controller.py`**

```python
"""
Controller (Presentation Layer)

Responsibilities:
- Handle HTTP requests/responses
- Parse input data
- Call use cases
- Format responses

This layer knows about FastAPI, but use cases don't!
"""
from fastapi import HTTPException
from ...application.use_cases.create_user_use_case import CreateUserUseCase
from ...application.use_cases.get_user_use_case import GetUserUseCase
from ..dtos.user_dto import CreateUserRequest, UserResponse


class UserController:
    """
    User Controller
    
    Handles HTTP requests related to users.
    """
    
    def __init__(
        self,
        create_user_use_case: CreateUserUseCase,
        get_user_use_case: GetUserUseCase
    ):
        """
        Initialize controller with use cases
        
        Args:
            create_user_use_case: Create user use case
            get_user_use_case: Get user use case
        """
        self.create_user_use_case = create_user_use_case
        self.get_user_use_case = get_user_use_case
    
    async def create_user(self, request: CreateUserRequest) -> UserResponse:
        """
        POST /users
        Create a new user
        
        Args:
            request: Create user request DTO
            
        Returns:
            User response DTO
            
        Raises:
            HTTPException: If creation fails
        """
        try:
            # Execute use case
            user = await self.create_user_use_case.execute(
                email=request.email,
                name=request.name
            )
            
            # Format response
            return UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                created_at=user.created_at
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def get_user(self, user_id: str) -> UserResponse:
        """
        GET /users/{user_id}
        Get user by ID
        
        Args:
            user_id: User identifier
            
        Returns:
            User response DTO
            
        Raises:
            HTTPException: If user not found
        """
        try:
            user = await self.get_user_use_case.execute(user_id)
            
            return UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                created_at=user.created_at
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
```

### Presentation Layer: Routes

**`src/presentation/routes/user_routes.py`**

```python
"""
Routes Configuration

This sets up:
- Dependency injection
- Route handlers
- FastAPI router
"""
from fastapi import APIRouter
from ..controllers.user_controller import UserController
from ..dtos.user_dto import CreateUserRequest, UserResponse
from ...application.use_cases.create_user_use_case import CreateUserUseCase
from ...application.use_cases.get_user_use_case import GetUserUseCase
from ...infrastructure.repositories.user_repository_impl import UserRepositoryImpl


def create_user_router() -> APIRouter:
    """
    Create user router with dependencies
    
    Returns:
        Configured FastAPI router
    """
    router = APIRouter(prefix="/users", tags=["users"])
    
    # Dependency Injection Setup
    # This is where we wire everything together
    user_repository = UserRepositoryImpl()
    create_user_use_case = CreateUserUseCase(user_repository)
    get_user_use_case = GetUserUseCase(user_repository)
    user_controller = UserController(create_user_use_case, get_user_use_case)
    
    # Define routes
    @router.post("", response_model=UserResponse, status_code=201)
    async def create_user(request: CreateUserRequest):
        """
        Create a new user
        
        - **email**: User email address
        - **name**: User full name
        """
        return await user_controller.create_user(request)
    
    @router.get("/{user_id}", response_model=UserResponse)
    async def get_user(user_id: str):
        """
        Get user by ID
        
        - **user_id**: User identifier
        """
        return await user_controller.get_user(user_id)
    
    return router
```

### Main Application Entry Point

**`main.py`**

```python
"""
Application Entry Point

This is where FastAPI app is configured and started.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.presentation.routes.user_routes import create_user_router

# Create FastAPI app
app = FastAPI(
    title="Microservices API",
    description="Microservices architecture with Clean Architecture",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(create_user_router())

# Health check
@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Distributed Caching with Redis

Redis provides distributed caching similar to FusionCache in .NET. Let's implement a caching layer.

### Step 1: Cache Service Interface

**`src/domain/services/cache_service.py`**

```python
"""
Cache Service Interface (Port)

Defines caching operations without knowing implementation details.
"""
from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic
import json

T = TypeVar('T')


class ICacheService(ABC):
    """
    Cache Service Interface
    
    Similar to FusionCache in .NET, provides:
    - Get/Set operations
    - TTL (Time To Live) support
    - Distributed caching across multiple instances
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        pass
    
    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Optional TTL in seconds
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete value from cache
        
        Args:
            key: Cache key
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    async def get_json(self, key: str) -> Optional[dict]:
        """
        Get JSON value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Parsed JSON dict or None
        """
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set_json(self, key: str, value: dict, ttl_seconds: Optional[int] = None) -> None:
        """
        Set JSON value in cache
        
        Args:
            key: Cache key
            value: Dict to cache
            ttl_seconds: Optional TTL in seconds
        """
        await self.set(key, json.dumps(value), ttl_seconds)
```

### Step 2: Redis Cache Implementation

**`src/infrastructure/cache/redis_cache_service.py`**

```python
"""
Redis Cache Service Implementation

This implements distributed caching using Redis.
Similar to FusionCache in .NET, it provides:
- Get/Set operations
- TTL (Time To Live) support
- Distributed caching across multiple instances
"""
import json
from typing import Optional
import redis.asyncio as aioredis
from ...domain.services.cache_service import ICacheService


class RedisCacheService(ICacheService):
    """
    Redis Cache Service
    
    Provides distributed caching using Redis.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis cache service
        
        Args:
            redis_url: Redis connection URL (default: redis://localhost:6379)
        """
        self.redis_url = redis_url or "redis://localhost:6379"
        self.client: Optional[aioredis.Redis] = None
    
    async def connect(self) -> None:
        """
        Connect to Redis
        
        In production, use connection pooling and error handling.
        """
        try:
            self.client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            print("Connected to Redis")
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """
        Close Redis connection
        """
        if self.client:
            await self.client.close()
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.client:
            return None
        
        try:
            value = await self.client.get(key)
            return value
        except Exception as e:
            print(f"Cache get error: {e}")
            return None  # Fail gracefully
    
    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Optional TTL in seconds
        """
        if not self.client:
            return
        
        try:
            if ttl_seconds:
                # Set with expiration
                await self.client.setex(key, ttl_seconds, value)
            else:
                # Set without expiration
                await self.client.set(key, value)
        except Exception as e:
            print(f"Cache set error: {e}")
            # Fail silently - cache is not critical
    
    async def delete(self, key: str) -> None:
        """
        Delete value from cache
        
        Args:
            key: Cache key
        """
        if not self.client:
            return
        
        try:
            await self.client.delete(key)
        except Exception as e:
            print(f"Cache delete error: {e}")
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.client:
            return False
        
        try:
            result = await self.client.exists(key)
            return result > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False
```

### Step 3: Cached Repository Decorator

**`src/infrastructure/repositories/cached_user_repository.py`**

```python
"""
Cached Repository Decorator

This is a decorator pattern implementation:
- Wraps the original repository
- Adds caching layer
- Transparent to the use cases

Similar to FusionCache's decorator pattern in .NET
"""
import json
from datetime import datetime
from typing import Optional
from ...domain.entities.user import User
from ...domain.repositories.user_repository import IUserRepository
from ...domain.services.cache_service import ICacheService


class CachedUserRepository(IUserRepository):
    """
    Cached User Repository
    
    Wraps a user repository with caching functionality.
    """
    
    CACHE_TTL = 300  # 5 minutes
    
    def __init__(self, repository: IUserRepository, cache: ICacheService):
        """
        Initialize cached repository
        
        Args:
            repository: Base repository implementation
            cache: Cache service implementation
        """
        self.repository = repository
        self.cache = cache
    
    async def find_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID with caching
        
        Flow:
        1. Check cache first
        2. If cache hit, return cached value
        3. If cache miss, fetch from repository
        4. Store in cache for next time
        
        Args:
            user_id: User identifier
            
        Returns:
            User entity or None
        """
        cache_key = f"user:{user_id}"
        
        # Try cache first
        cached_data = await self.cache.get_json(cache_key)
        if cached_data:
            print(f"Cache HIT for user:{user_id}")
            # Reconstruct User entity from cached data
            return User(
                user_id=cached_data["id"],
                email=cached_data["email"],
                name=cached_data["name"],
                created_at=datetime.fromisoformat(cached_data["created_at"])
            )
        
        # Cache miss - fetch from repository
        print(f"Cache MISS for user:{user_id}")
        user = await self.repository.find_by_id(user_id)
        
        # Store in cache if found
        if user:
            await self.cache.set_json(
                cache_key,
                {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "created_at": user.created_at.isoformat()
                },
                self.CACHE_TTL
            )
        
        return user
    
    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email with caching
        
        Args:
            email: User email
            
        Returns:
            User entity or None
        """
        cache_key = f"user:email:{email}"
        
        # Try cache first
        cached_data = await self.cache.get_json(cache_key)
        if cached_data:
            return User(
                user_id=cached_data["id"],
                email=cached_data["email"],
                name=cached_data["name"],
                created_at=datetime.fromisoformat(cached_data["created_at"])
            )
        
        # Cache miss
        user = await self.repository.find_by_email(email)
        
        if user:
            await self.cache.set_json(
                cache_key,
                {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "created_at": user.created_at.isoformat()
                },
                self.CACHE_TTL
            )
        
        return user
    
    async def save(self, user: User) -> User:
        """
        Save user and invalidate cache
        
        Args:
            user: User entity to save
            
        Returns:
            Saved user entity
        """
        # Save to repository
        saved_user = await self.repository.save(user)
        
        # Invalidate cache
        await self.cache.delete(f"user:{saved_user.id}")
        await self.cache.delete(f"user:email:{saved_user.email}")
        
        return saved_user
    
    async def delete(self, user_id: str) -> None:
        """
        Delete user and invalidate cache
        
        Args:
            user_id: User identifier
        """
        # Get user first to invalidate email cache
        user = await self.repository.find_by_id(user_id)
        
        # Delete from repository
        await self.repository.delete(user_id)
        
        # Invalidate cache
        await self.cache.delete(f"user:{user_id}")
        if user:
            await self.cache.delete(f"user:email:{user.email}")
```

### Step 4: Update Routes to Use Cached Repository

**`src/presentation/routes/user_routes.py`** (Updated)

```python
from fastapi import APIRouter
from ..controllers.user_controller import UserController
from ..dtos.user_dto import CreateUserRequest, UserResponse
from ...application.use_cases.create_user_use_case import CreateUserUseCase
from ...application.use_cases.get_user_use_case import GetUserUseCase
from ...infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from ...infrastructure.repositories.cached_user_repository import CachedUserRepository
from ...infrastructure.cache.redis_cache_service import RedisCacheService
from ...domain.services.cache_service import ICacheService


def create_user_router(cache_service: ICacheService) -> APIRouter:
    """
    Create user router with dependencies
    
    Args:
        cache_service: Cache service implementation
        
    Returns:
        Configured FastAPI router
    """
    router = APIRouter(prefix="/users", tags=["users"])
    
    # Setup caching
    base_repository = UserRepositoryImpl()
    cached_repository = CachedUserRepository(base_repository, cache_service)
    
    # Use cases with cached repository
    create_user_use_case = CreateUserUseCase(cached_repository)
    get_user_use_case = GetUserUseCase(cached_repository)
    user_controller = UserController(create_user_use_case, get_user_use_case)
    
    @router.post("", response_model=UserResponse, status_code=201)
    async def create_user(request: CreateUserRequest):
        """Create a new user"""
        return await user_controller.create_user(request)
    
    @router.get("/{user_id}", response_model=UserResponse)
    async def get_user(user_id: str):
        """Get user by ID"""
        return await user_controller.get_user(user_id)
    
    return router
```

---

## Message Queue with RabbitMQ

RabbitMQ provides message queuing similar to MassTransit in .NET. Let's implement pub/sub pattern.

### Step 1: Message Bus Interface

**`src/domain/services/message_bus.py`**

```python
"""
Message Bus Interface (Port)

Defines messaging operations:
- Publish messages
- Subscribe to messages

Similar to MassTransit's IBus in .NET
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Awaitable


class IMessageBus(ABC):
    """
    Message Bus Interface
    
    Provides pub/sub messaging capabilities.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Connect to message broker
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from message broker
        """
        pass
    
    @abstractmethod
    async def publish(
        self,
        exchange: str,
        routing_key: str,
        message: Dict[str, Any]
    ) -> None:
        """
        Publish a message
        
        Args:
            exchange: Exchange name (e.g., 'user.events')
            routing_key: Routing key (e.g., 'user.created')
            message: Message payload
        """
        pass
    
    @abstractmethod
    async def subscribe(
        self,
        exchange: str,
        queue: str,
        routing_key: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Subscribe to messages
        
        Args:
            exchange: Exchange name
            queue: Queue name
            routing_key: Routing key pattern (supports wildcards: *, #)
            handler: Message handler function
        """
        pass
```

### Step 2: RabbitMQ Message Bus Implementation

**`src/infrastructure/messaging/rabbitmq_message_bus.py`**

```python
"""
RabbitMQ Message Bus Implementation

This implements message queuing using RabbitMQ.
Similar to MassTransit in .NET, it provides:
- Publish/Subscribe pattern
- Exchange and queue management
- Message routing
"""
import json
import asyncio
from typing import Dict, Any, Callable, Awaitable, Optional
import pika
from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel
from ...domain.services.message_bus import IMessageBus


class RabbitMQMessageBus(IMessageBus):
    """
    RabbitMQ Message Bus
    
    Provides pub/sub messaging using RabbitMQ.
    """
    
    def __init__(self, rabbitmq_url: Optional[str] = None):
        """
        Initialize RabbitMQ message bus
        
        Args:
            rabbitmq_url: RabbitMQ connection URL
        """
        self.rabbitmq_url = rabbitmq_url or "amqp://guest:guest@localhost:5672/"
        self.connection: Optional[AsyncioConnection] = None
        self.channel: Optional[Channel] = None
    
    async def connect(self) -> None:
        """
        Connect to RabbitMQ
        
        This establishes connection and creates a channel.
        In production, implement reconnection logic.
        """
        try:
            parameters = pika.URLParameters(self.rabbitmq_url)
            self.connection = AsyncioConnection(parameters)
            self.channel = await self.connection.channel()
            
            print("Connected to RabbitMQ")
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self) -> None:
        """
        Close RabbitMQ connection
        """
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
    
    async def publish(
        self,
        exchange: str,
        routing_key: str,
        message: Dict[str, Any]
    ) -> None:
        """
        Publish a message
        
        Similar to MassTransit's Publish method
        
        Args:
            exchange: Exchange name (e.g., 'user.events')
            routing_key: Routing key (e.g., 'user.created')
            message: Message payload
        """
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")
        
        try:
            # Declare exchange (create if not exists)
            await self.channel.exchange_declare(
                exchange=exchange,
                exchange_type='topic',
                durable=True  # Survive broker restart
            )
            
            # Publish message
            message_body = json.dumps(message).encode('utf-8')
            await self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            print(f"Published message to {exchange}:{routing_key}")
        except Exception as e:
            print(f"Failed to publish message: {e}")
            raise
    
    async def subscribe(
        self,
        exchange: str,
        queue: str,
        routing_key: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Subscribe to messages
        
        Similar to MassTransit's Consumer pattern
        
        Args:
            exchange: Exchange name
            queue: Queue name
            routing_key: Routing key pattern (supports wildcards: *, #)
            handler: Message handler function
        """
        if not self.channel:
            raise RuntimeError("Not connected to RabbitMQ")
        
        try:
            # Declare exchange
            await self.channel.exchange_declare(
                exchange=exchange,
                exchange_type='topic',
                durable=True
            )
            
            # Declare queue
            await self.channel.queue_declare(
                queue=queue,
                durable=True  # Queue survives broker restart
            )
            
            # Bind queue to exchange with routing key
            await self.channel.queue_bind(
                exchange=exchange,
                queue=queue,
                routing_key=routing_key
            )
            
            # Define message handler
            async def on_message(
                channel: Channel,
                method: Any,
                properties: Any,
                body: bytes
            ):
                try:
                    # Parse message
                    message = json.loads(body.decode('utf-8'))
                    
                    # Handle message
                    await handler(message)
                    
                    # Acknowledge message (remove from queue)
                    await channel.basic_ack(delivery_tag=method.delivery_tag)
                    
                    print(f"Processed message from {queue}")
                except Exception as e:
                    print(f"Error processing message: {e}")
                    # Negative acknowledge (requeue message)
                    await channel.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=True
                    )
            
            # Start consuming
            await self.channel.basic_consume(
                queue=queue,
                on_message_callback=on_message
            )
            
            print(f"Subscribed to {exchange}:{routing_key} via queue {queue}")
        except Exception as e:
            print(f"Failed to subscribe: {e}")
            raise
```

### Step 3: Domain Events

**`src/domain/events/user_created_event.py`**

```python
"""
Domain Event: User Created

Domain events represent something important that happened in the domain.
Other services can subscribe to these events.
"""
from dataclasses import dataclass


@dataclass
class UserCreatedEvent:
    """
    User Created Event
    
    This event is published when a new user is created.
    """
    user_id: str
    email: str
    name: str
    created_at: str
    
    def to_dict(self) -> dict:
        """
        Convert event to dictionary for serialization
        
        Returns:
            Event as dictionary
        """
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at
        }
```

### Step 4: Update Use Case to Publish Events

**`src/application/use_cases/create_user_use_case.py`** (Updated)

```python
import uuid
from datetime import datetime
from typing import Optional
from ...domain.entities.user import User
from ...domain.repositories.user_repository import IUserRepository
from ...domain.services.message_bus import IMessageBus
from ...domain.events.user_created_event import UserCreatedEvent


class CreateUserUseCase:
    """
    Create User Use Case
    
    This use case handles the business logic for creating a new user.
    """
    
    def __init__(
        self,
        user_repository: IUserRepository,
        message_bus: Optional[IMessageBus] = None
    ):
        """
        Initialize use case with repository and optional message bus
        
        Args:
            user_repository: User repository implementation
            message_bus: Optional message bus for publishing events
        """
        self.user_repository = user_repository
        self.message_bus = message_bus
    
    async def execute(self, email: str, name: str) -> User:
        """
        Execute the use case
        
        Args:
            email: User email
            name: User name
            
        Returns:
            Created User entity
        """
        existing_user = await self.user_repository.find_by_email(email)
        if existing_user:
            raise ValueError('User with this email already exists')
        
        user = User(
            user_id=self._generate_id(),
            email=email,
            name=name,
            created_at=datetime.now()
        )
        
        saved_user = await self.user_repository.save(user)
        
        # Publish domain event if message bus is available
        if self.message_bus:
            event = UserCreatedEvent(
                user_id=saved_user.id,
                email=saved_user.email,
                name=saved_user.name,
                created_at=saved_user.created_at.isoformat()
            )
            
            await self.message_bus.publish(
                exchange='user.events',
                routing_key='user.created',
                message=event.to_dict()
            )
        
        return saved_user
    
    def _generate_id(self) -> str:
        return f"user_{uuid.uuid4().hex[:12]}"
```

### Step 5: Event Handler (Consumer)

**`src/application/handlers/user_created_event_handler.py`**

```python
"""
Event Handler: User Created

This handles the UserCreatedEvent.
In a microservices architecture, this could be:
- Sending welcome email
- Creating user profile
- Updating analytics
- etc.
"""
from typing import Dict, Any
from ...domain.events.user_created_event import UserCreatedEvent


class UserCreatedEventHandler:
    """
    User Created Event Handler
    
    Processes UserCreatedEvent messages.
    """
    
    async def handle(self, event_data: Dict[str, Any]) -> None:
        """
        Handle UserCreatedEvent
        
        Args:
            event_data: Event data dictionary
        """
        # Parse event
        event = UserCreatedEvent(
            user_id=event_data["user_id"],
            email=event_data["email"],
            name=event_data["name"],
            created_at=event_data["created_at"]
        )
        
        print(f"User Created Event Received: {event}")
        
        # Example: Send welcome email
        print(f"Sending welcome email to {event.email}")
        
        # Example: Create user profile
        print(f"Creating profile for user {event.user_id}")
        
        # Example: Update analytics
        print("Updating user analytics")
```

### Step 6: Setup Event Subscription

**`src/infrastructure/messaging/event_subscriptions.py`**

```python
"""
Event Subscriptions Setup

This sets up all event subscriptions.
Similar to MassTransit's consumer configuration.
"""
from ...domain.services.message_bus import IMessageBus
from ...application.handlers.user_created_event_handler import UserCreatedEventHandler


async def setup_event_subscriptions(message_bus: IMessageBus) -> None:
    """
    Setup event subscriptions
    
    Args:
        message_bus: Message bus implementation
    """
    user_created_handler = UserCreatedEventHandler()
    
    # Subscribe to user.created events
    await message_bus.subscribe(
        exchange='user.events',
        queue='user-service-queue',
        routing_key='user.created',
        handler=user_created_handler.handle
    )
    
    print("Event subscriptions configured")
```

### Step 7: Update Main App

**`main.py`** (Final Version)

```python
"""
Application Entry Point

This is where FastAPI app is configured and started.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.presentation.routes.user_routes import create_user_router
from src.infrastructure.cache.redis_cache_service import RedisCacheService
from src.infrastructure.messaging.rabbitmq_message_bus import RabbitMQMessageBus
from src.infrastructure.messaging.event_subscriptions import setup_event_subscriptions
import os
from dotenv import load_dotenv

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager
    
    Handles startup and shutdown events.
    """
    # Startup
    print("Starting up...")
    
    # Initialize cache service
    cache_service = RedisCacheService(os.getenv("REDIS_URL"))
    await cache_service.connect()
    
    # Initialize message bus
    message_bus = RabbitMQMessageBus(os.getenv("RABBITMQ_URL"))
    await message_bus.connect()
    
    # Setup event subscriptions
    await setup_event_subscriptions(message_bus)
    
    # Store in app state
    app.state.cache_service = cache_service
    app.state.message_bus = message_bus
    
    yield
    
    # Shutdown
    print("Shutting down...")
    await cache_service.disconnect()
    await message_bus.disconnect()


# Create FastAPI app
app = FastAPI(
    title="Microservices API",
    description="Microservices architecture with Clean Architecture",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
@app.on_event("startup")
async def startup_event():
    """Setup routes after app state is initialized"""
    cache_service = app.state.cache_service
    message_bus = app.state.message_bus
    
    # Create router with dependencies
    user_router = create_user_router(cache_service)
    
    # Update create_user_use_case to include message_bus
    from src.application.use_cases.create_user_use_case import CreateUserUseCase
    from src.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
    from src.infrastructure.repositories.cached_user_repository import CachedUserRepository
    
    # This is a simplified approach - in production, use dependency injection
    app.include_router(user_router)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Updated `src/presentation/routes/user_routes.py`** (Final Version)

```python
from fastapi import APIRouter
from ..controllers.user_controller import UserController
from ..dtos.user_dto import CreateUserRequest, UserResponse
from ...application.use_cases.create_user_use_case import CreateUserUseCase
from ...application.use_cases.get_user_use_case import GetUserUseCase
from ...infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from ...infrastructure.repositories.cached_user_repository import CachedUserRepository
from ...domain.services.cache_service import ICacheService
from ...domain.services.message_bus import IMessageBus


def create_user_router(
    cache_service: ICacheService,
    message_bus: IMessageBus
) -> APIRouter:
    """
    Create user router with dependencies
    
    Args:
        cache_service: Cache service implementation
        message_bus: Message bus implementation
        
    Returns:
        Configured FastAPI router
    """
    router = APIRouter(prefix="/users", tags=["users"])
    
    # Setup caching
    base_repository = UserRepositoryImpl()
    cached_repository = CachedUserRepository(base_repository, cache_service)
    
    # Use cases with dependencies
    create_user_use_case = CreateUserUseCase(cached_repository, message_bus)
    get_user_use_case = GetUserUseCase(cached_repository)
    user_controller = UserController(create_user_use_case, get_user_use_case)
    
    @router.post("", response_model=UserResponse, status_code=201)
    async def create_user(request: CreateUserRequest):
        """Create a new user"""
        return await user_controller.create_user(request)
    
    @router.get("/{user_id}", response_model=UserResponse)
    async def get_user(user_id: str):
        """Get user by ID"""
        return await user_controller.get_user(user_id)
    
    return router
```

---

## Complete Example: User Service

### Requirements File

**`requirements.txt`**

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0
redis==5.0.1
pika==1.3.2
```

### Environment Variables

**`.env`**

```env
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

### Docker Compose for Infrastructure

**`docker-compose.yml`**

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports:
      - "5672:5672"
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

### Running the Application

1. **Start infrastructure:**
   ```bash
   docker-compose up -d
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the application:**
   ```bash
   python main.py
   ```

4. **Test the API:**
   ```bash
   # Create user
   curl -X POST http://localhost:8000/users \
     -H "Content-Type: application/json" \
     -d '{"email":"john@example.com","name":"John Doe"}'

   # Get user
   curl http://localhost:8000/users/user_abc123
   ```

---

## Key Concepts Explained

### Clean Architecture Benefits

1. **Testability**: Each layer can be tested independently
2. **Maintainability**: Changes in one layer don't affect others
3. **Flexibility**: Easy to swap implementations (e.g., Redis → Memcached)
4. **Independence**: Business logic doesn't depend on frameworks

### Distributed Caching Benefits

1. **Performance**: Reduces database load
2. **Scalability**: Multiple instances share cache
3. **Availability**: Cache survives service restarts

### Message Queue Benefits

1. **Decoupling**: Services don't need to know about each other
2. **Reliability**: Messages are persisted
3. **Scalability**: Handle high message volumes
4. **Event-Driven**: React to domain events

---

## Next Steps

1. Add database persistence (PostgreSQL, MongoDB)
2. Add authentication/authorization (JWT)
3. Add API validation (Pydantic validators)
4. Add logging (structlog, loguru)
5. Add monitoring (Prometheus, Grafana)
6. Add unit and integration tests (pytest)
7. Add Docker containerization
8. Add CI/CD pipeline

---

## Summary

This tutorial demonstrated:
- ✅ Clean Architecture with clear layer separation
- ✅ Distributed caching with Redis (similar to FusionCache)
- ✅ Message queuing with RabbitMQ (similar to MassTransit)
- ✅ Domain-driven design principles
- ✅ Dependency injection
- ✅ Event-driven architecture

The code follows best practices and is beginner-friendly with clear explanations at each step.
