# Complete Microservices Example

This guide shows how all pieces work together: Clean Architecture, Distributed Caching, and Message Queue.

## Complete Project Structure

```
fastapi-microservices-tutorial/
├── app/
│   ├── domain/
│   │   ├── entities/
│   │   │   └── user.py
│   │   ├── repositories/
│   │   │   ├── user_repository.py
│   │   │   └── cache_repository.py
│   │   └── services/
│   │       ├── message_publisher.py
│   │       └── message_consumer.py
│   ├── application/
│   │   ├── use_cases/
│   │   │   ├── create_user_use_case.py
│   │   │   └── get_user_use_case.py
│   │   ├── services/
│   │   │   └── user_event_handler.py
│   │   └── dto/
│   │       └── create_user_dto.py
│   ├── infrastructure/
│   │   ├── cache/
│   │   │   └── redis_cache_repository.py
│   │   ├── messaging/
│   │   │   ├── rabbitmq_publisher.py
│   │   │   ├── rabbitmq_consumer.py
│   │   │   └── setup_consumers.py
│   │   └── repositories/
│   │       ├── in_memory_user_repository.py
│   │       └── cached_user_repository.py
│   └── presentation/
│       ├── api/
│       │   └── user_router.py
│       └── dependencies.py
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── main.py
```

## Complete Implementation Files

### 1. Main Application

```python
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.presentation.api.user_router import router as user_router
from app.infrastructure.messaging.setup_consumers import setup_consumers
from app.presentation.dependencies import init_message_publisher
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Background task for consumers
consumer_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global consumer_task
    
    # Startup
    print("🚀 Starting microservices application...")
    print("📨 Setting up message consumers...")
    
    # Initialize message publisher
    await init_message_publisher()
    
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
    description="FastAPI microservices with Clean Architecture, Redis Cache, and RabbitMQ",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(user_router, prefix="/api")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to FastAPI Microservices Tutorial",
        "docs": "/docs",
        "health": "/health"
    }
```

### 2. Complete Dependencies

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

async def init_message_publisher():
    """Initialize message publisher"""
    await _message_publisher.connect()

def get_create_user_use_case() -> CreateUserUseCase:
    """Dependency: Create user use case"""
    return CreateUserUseCase(_cached_repository, _message_publisher)

def get_user_use_case() -> GetUserUseCase:
    """Dependency: Get user use case"""
    return GetUserUseCase(_cached_repository)
```

### 3. Complete Router

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
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

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
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Running the Complete Example

### Step 1: Setup Python Environment

```bash
cd fastapi-microservices-tutorial
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Setup Environment Variables

```bash
cp .env.example .env
# Edit .env if needed
```

### Step 4: Start Infrastructure

```bash
docker-compose up -d
```

This starts:
- Redis on port 6379
- RabbitMQ on port 5672 (Management UI on 15672)

### Step 5: Start Application

```bash
uvicorn main:app --reload
```

### Step 6: Test the API

```bash
# Create a user (triggers cache write and message publish)
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "name": "John Doe"
  }'

# Get user (first time - cache miss, second time - cache hit)
curl http://localhost:8000/api/users/{USER_ID}

# View API documentation
open http://localhost:8000/docs

# Check RabbitMQ Management UI
open http://localhost:15672
# Login: admin / admin123
```

## Flow Diagram

```
1. HTTP Request → FastAPI Router
   ↓
2. Router → Use Case (via Dependency Injection)
   ↓
3. Use Case → Cached Repository
   ↓
4. Cached Repository → Redis Cache (check)
   ↓
5. Cache Miss → Base Repository → Database
   ↓
6. Save to Cache
   ↓
7. Use Case → Message Publisher
   ↓
8. Message Publisher → RabbitMQ
   ↓
9. RabbitMQ → Consumer → Event Handler
```

## Key Takeaways

1. **Clean Architecture**: Business logic is independent of frameworks
2. **Distributed Caching**: Redis provides fast, shared cache
3. **Message Queue**: RabbitMQ enables async, decoupled communication
4. **Separation of Concerns**: Each layer has a single responsibility
5. **Testability**: Easy to mock interfaces for testing
6. **Type Safety**: Python type hints + Pydantic provide validation
7. **Async Support**: Full async/await support throughout

## Production Considerations

1. **Error Handling**: Add retry logic and dead letter queues
2. **Monitoring**: Add logging and metrics (Prometheus, Grafana)
3. **Security**: Add authentication and authorization
4. **Database**: Replace in-memory repository with real database (PostgreSQL, MongoDB)
5. **Connection Pooling**: Use connection pools for Redis and RabbitMQ
6. **Configuration**: Use environment variables and config files
7. **Testing**: Add unit and integration tests (pytest)
8. **Documentation**: Use FastAPI's automatic OpenAPI documentation
9. **Deployment**: Use Docker containers and orchestration (Kubernetes)

## Python-Specific Best Practices

1. **Type Hints**: Use type hints everywhere for better IDE support
2. **Async/Await**: Use async for I/O operations (database, cache, messaging)
3. **Dependency Injection**: Leverage FastAPI's dependency system
4. **Pydantic Models**: Use Pydantic for data validation
5. **Context Managers**: Use context managers for resource cleanup
6. **Exception Handling**: Use specific exceptions, not generic ones

## Next Steps

- Add more microservices (Notification Service, Email Service)
- Implement API Gateway
- Add service discovery
- Implement distributed tracing (OpenTelemetry)
- Add monitoring and alerting
- Implement database migrations (Alembic)
- Add authentication (JWT, OAuth2)
- Implement rate limiting
- Add request/response logging middleware
