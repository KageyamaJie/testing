# Distributed Caching with Redis

## What is Distributed Caching?

Distributed caching stores frequently accessed data in memory across multiple servers. This is similar to **FusionCache** in .NET, providing:
- **Fast access** - Data stored in memory (much faster than database)
- **Shared state** - Multiple servers can access the same cache
- **Reduced load** - Fewer database queries

## Why Redis?

Redis is an in-memory data store that's perfect for caching:
- **Fast** - Sub-millisecond response times
- **Distributed** - Can be shared across multiple servers
- **Reliable** - Supports persistence and replication
- **Python Support** - Excellent libraries (redis, aioredis)

## Architecture

```
┌─────────────┐
│   FastAPI   │
│   Server    │
└──────┬──────┘
       │
       │ Check Cache
       ▼
┌─────────────┐     Cache Miss    ┌─────────────┐
│    Redis    │◄───────────────────│  Database   │
│   (Cache)   │                    └─────────────┘
└─────────────┘
```

## Step 1: Create Cache Interface (Domain Layer)

First, define what caching operations we need in the domain layer:

```python
# app/domain/repositories/cache_repository.py
from abc import ABC, abstractmethod
from typing import Optional, Any

class ICacheRepository(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Set value in cache with optional TTL"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass
```

**Why in domain layer?** The domain layer defines contracts. The infrastructure layer implements them.

## Step 2: Redis Implementation (Infrastructure Layer)

```python
# app/infrastructure/cache/redis_cache_repository.py
import json
import os
from typing import Optional, Any
from redis import Redis
from app.domain.repositories.cache_repository import ICacheRepository

class RedisCacheRepository(ICacheRepository):
    def __init__(self):
        self.client = Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=False,  # We'll handle encoding ourselves
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.client.get(key)
            if value is None:
                return None
            return json.loads(value.decode('utf-8'))
        except Exception as e:
            print(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Set value in cache with optional TTL"""
        try:
            serialized = json.dumps(value).encode('utf-8')
            if ttl_seconds:
                self.client.setex(key, ttl_seconds, serialized)
            else:
                self.client.set(key, serialized)
        except Exception as e:
            print(f"Cache set error for key {key}: {e}")
            # Don't throw - cache failures shouldn't break the app

    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        try:
            self.client.delete(key)
        except Exception as e:
            print(f"Cache delete error for key {key}: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return self.client.exists(key) == 1
        except Exception as e:
            print(f"Cache exists error for key {key}: {e}")
            return False

    def close(self):
        """Close Redis connection"""
        self.client.close()
```

**For Async Operations (Better Performance):**

```python
# app/infrastructure/cache/redis_cache_repository_async.py
import json
import os
from typing import Optional, Any
import redis.asyncio as aioredis
from app.domain.repositories.cache_repository import ICacheRepository

class AsyncRedisCacheRepository(ICacheRepository):
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        self.client = await aioredis.from_url(
            f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}",
            decode_responses=False
        )

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.client:
            await self.connect()
        
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            return json.loads(value.decode('utf-8'))
        except Exception as e:
            print(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Set value in cache with optional TTL"""
        if not self.client:
            await self.connect()
        
        try:
            serialized = json.dumps(value).encode('utf-8')
            if ttl_seconds:
                await self.client.setex(key, ttl_seconds, serialized)
            else:
                await self.client.set(key, serialized)
        except Exception as e:
            print(f"Cache set error for key {key}: {e}")

    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        if not self.client:
            await self.connect()
        
        try:
            await self.client.delete(key)
        except Exception as e:
            print(f"Cache delete error for key {key}: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.client:
            await self.connect()
        
        try:
            result = await self.client.exists(key)
            return result == 1
        except Exception as e:
            print(f"Cache exists error for key {key}: {e}")
            return False

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
```

**Explanation:**
- Uses `redis` library (synchronous) or `redis.asyncio` (asynchronous)
- Handles errors gracefully (cache failures shouldn't crash the app)
- Supports TTL (Time To Live) for automatic expiration
- Serializes/deserializes JSON automatically

## Step 3: Cached User Repository

Now, let's create a cached version of the user repository:

```python
# app/infrastructure/repositories/cached_user_repository.py
from typing import Optional
from app.domain.entities.user import User
from app.domain.repositories.user_repository import IUserRepository
from app.domain.repositories.cache_repository import ICacheRepository

class CachedUserRepository(IUserRepository):
    def __init__(
        self,
        base_repository: IUserRepository,
        cache: ICacheRepository,
        cache_ttl: int = 3600  # 1 hour default
    ):
        self.base_repository = base_repository
        self.cache = cache
        self.cache_ttl = cache_ttl

    async def find_by_id(self, user_id: str) -> Optional[User]:
        """Find user by ID with caching"""
        cache_key = f"user:{user_id}"

        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            print(f"Cache HIT for user:{user_id}")
            return User(
                id=cached["id"],
                email=cached["email"],
                name=cached["name"],
                created_at=cached["created_at"]
            )

        # Cache miss - get from base repository
        print(f"Cache MISS for user:{user_id}")
        user = await self.base_repository.find_by_id(user_id)

        # Store in cache if found
        if user:
            await self.cache.set(
                cache_key,
                {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "created_at": user.created_at.isoformat()
                },
                self.cache_ttl
            )

        return user

    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email with caching"""
        cache_key = f"user:email:{email}"

        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            print(f"Cache HIT for email:{email}")
            return User(
                id=cached["id"],
                email=cached["email"],
                name=cached["name"],
                created_at=cached["created_at"]
            )

        # Cache miss
        print(f"Cache MISS for email:{email}")
        user = await self.base_repository.find_by_email(email)

        if user:
            await self.cache.set(
                cache_key,
                {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "created_at": user.created_at.isoformat()
                },
                self.cache_ttl
            )

        return user

    async def save(self, user: User) -> User:
        """Save user and invalidate cache"""
        # Save to base repository
        saved_user = await self.base_repository.save(user)

        # Invalidate cache (or update it)
        await self.cache.delete(f"user:{saved_user.id}")
        await self.cache.delete(f"user:email:{saved_user.email}")

        # Optionally, update cache with new value
        await self.cache.set(
            f"user:{saved_user.id}",
            {
                "id": saved_user.id,
                "email": saved_user.email,
                "name": saved_user.name,
                "created_at": saved_user.created_at.isoformat()
            },
            self.cache_ttl
        )

        return saved_user

    async def delete(self, user_id: str) -> None:
        """Delete user and invalidate cache"""
        # Delete from base repository
        await self.base_repository.delete(user_id)

        # Invalidate cache
        await self.cache.delete(f"user:{user_id}")
```

**Key Concepts:**
- **Cache-Aside Pattern**: Check cache first, then database
- **Cache Invalidation**: Delete cache when data changes
- **Decorator Pattern**: Wraps the base repository without modifying it

## Step 4: Update Use Case to Use Cached Repository

```python
# app/application/use_cases/get_user_use_case.py
from typing import Optional
from app.domain.entities.user import User
from app.domain.repositories.user_repository import IUserRepository

class GetUserUseCase:
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    async def execute(self, user_id: str) -> Optional[User]:
        """Execute the get user use case"""
        if not user_id:
            raise ValueError("User ID is required")

        return await self.user_repository.find_by_id(user_id)
```

The use case doesn't know about caching! It just uses the repository interface.

## Step 5: Update Dependencies with Caching

```python
# app/presentation/dependencies.py
from app.application.use_cases.create_user_use_case import CreateUserUseCase
from app.application.use_cases.get_user_use_case import GetUserUseCase
from app.infrastructure.repositories.in_memory_user_repository import InMemoryUserRepository
from app.infrastructure.repositories.cached_user_repository import CachedUserRepository
from app.infrastructure.cache.redis_cache_repository import RedisCacheRepository

# Create singleton instances
_base_repository = InMemoryUserRepository()
_cache = RedisCacheRepository()
_cached_repository = CachedUserRepository(_base_repository, _cache)

def get_create_user_use_case() -> CreateUserUseCase:
    """Dependency: Create user use case"""
    return CreateUserUseCase(_cached_repository)

def get_user_use_case() -> GetUserUseCase:
    """Dependency: Get user use case"""
    return GetUserUseCase(_cached_repository)
```

## Step 6: Update Router

```python
# app/presentation/api/user_router.py
from fastapi import APIRouter, HTTPException, Depends
from app.application.use_cases.create_user_use_case import CreateUserUseCase
from app.application.use_cases.get_user_use_case import GetUserUseCase
from app.application.dto.create_user_dto import CreateUserDTO
from app.presentation.dependencies import (
    get_create_user_use_case,
    get_user_use_case
)

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", status_code=201)
async def create_user(
    dto: CreateUserDTO,
    use_case: CreateUserUseCase = Depends(get_create_user_use_case)
):
    """Create a new user"""
    try:
        user = await use_case.execute(dto)
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    use_case: GetUserUseCase = Depends(get_user_use_case)
):
    """Get user by ID"""
    try:
        user = await use_case.execute(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Testing Distributed Caching

```bash
# Start Redis
docker-compose up -d redis

# Start the server
uvicorn main:app --reload

# First request (cache miss - slower)
curl http://localhost:8000/api/users/{USER_ID}

# Second request (cache hit - faster!)
curl http://localhost:8000/api/users/{USER_ID}
```

Check the console logs - you'll see "Cache MISS" on the first request and "Cache HIT" on the second!

## Cache Patterns Used

1. **Cache-Aside**: Application checks cache, then database
2. **Write-Through**: Could be added - write to cache and database simultaneously
3. **Cache Invalidation**: Delete cache when data changes

## Benefits

- **Performance**: Sub-millisecond cache access vs. database queries
- **Scalability**: Multiple servers share the same cache
- **Reduced Load**: Fewer database queries
- **Resilience**: App continues working if cache fails

## Python-Specific Considerations

- **Async Support**: Use `redis.asyncio` for async operations
- **Connection Pooling**: Redis client handles connection pooling automatically
- **Error Handling**: Python's exception handling makes error management clean

## Next Steps

- [Message Queue with RabbitMQ](./03-message-queue.md)
