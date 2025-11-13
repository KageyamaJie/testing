# Clean Architecture in FastAPI

## What is Clean Architecture?

Clean Architecture is a design pattern that separates your code into layers, making it:
- **Testable** - Easy to write unit tests
- **Maintainable** - Changes in one layer don't affect others
- **Independent** - Business logic doesn't depend on frameworks or databases

## The Layers

```
┌─────────────────────────────────────┐
│      Presentation Layer             │  ← FastAPI Routers, Dependencies
├─────────────────────────────────────┤
│      Application Layer              │  ← Use Cases, DTOs
├─────────────────────────────────────┤
│      Domain Layer                   │  ← Entities, Business Logic
├─────────────────────────────────────┤
│      Infrastructure Layer           │  ← Database, Cache, Messaging
└─────────────────────────────────────┘
```

## Step 1: Domain Layer (Core Business Logic)

The domain layer contains your business entities and rules. It has **NO dependencies** on external libraries.

### User Entity

```python
# app/domain/entities/user.py
from datetime import datetime
from typing import Optional

class User:
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

    def is_active(self) -> bool:
        """Business logic: Check if user is active"""
        return '@' in self.email

    def get_display_name(self) -> str:
        """Business logic: Get formatted display name"""
        return f"{self.name} ({self.email})"
```

**Why this matters:** The User entity contains business rules. It doesn't know about databases or HTTP requests.

### Repository Interface (ABC - Abstract Base Class)

```python
# app/domain/repositories/user_repository.py
from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities.user import User

class IUserRepository(ABC):
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

**Why this matters:** We define an abstract interface (contract) in the domain layer. The actual implementation will be in the infrastructure layer.

## Step 2: Application Layer (Use Cases)

The application layer contains use cases - specific actions your application can perform.

### Create User Use Case

```python
# app/application/use_cases/create_user_use_case.py
import uuid
from datetime import datetime
from app.domain.entities.user import User
from app.domain.repositories.user_repository import IUserRepository
from app.application.dto.create_user_dto import CreateUserDTO

class CreateUserUseCase:
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

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
        return await self.user_repository.save(user)
```

**Explanation:**
- The use case orchestrates the business logic
- It uses the repository interface (not the implementation)
- It validates business rules before creating the user

### DTO (Data Transfer Object)

```python
# app/application/dto/create_user_dto.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class CreateUserDTO(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    name: str

    class Config:
        from_attributes = True
```

**Why Pydantic?** FastAPI uses Pydantic for data validation. It automatically validates request data.

## Step 3: Infrastructure Layer (External Concerns)

This layer implements the interfaces defined in the domain layer.

### In-Memory User Repository (for simplicity)

```python
# app/infrastructure/repositories/in_memory_user_repository.py
from typing import Optional, Dict
from app.domain.entities.user import User
from app.domain.repositories.user_repository import IUserRepository

class InMemoryUserRepository(IUserRepository):
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

**Why this matters:** The domain layer doesn't care HOW users are stored. We can swap this with a database implementation later without changing domain or application code.

## Step 4: Presentation Layer (API)

The presentation layer handles HTTP requests and responses using FastAPI.

### User Router

```python
# app/presentation/api/user_router.py
from fastapi import APIRouter, HTTPException, Depends
from app.application.use_cases.create_user_use_case import CreateUserUseCase
from app.application.dto.create_user_dto import CreateUserDTO
from app.presentation.dependencies import get_create_user_use_case

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
```

**Explanation:**
- Router handles HTTP concerns (request/response)
- FastAPI automatically validates request body using Pydantic
- Dependency injection provides the use case

### Dependencies (Dependency Injection)

```python
# app/presentation/dependencies.py
from app.application.use_cases.create_user_use_case import CreateUserUseCase
from app.infrastructure.repositories.in_memory_user_repository import InMemoryUserRepository

# Create singleton instances
_user_repository = InMemoryUserRepository()

def get_create_user_use_case() -> CreateUserUseCase:
    """Dependency: Create user use case"""
    return CreateUserUseCase(_user_repository)
```

**Why Dependency Injection?** FastAPI's dependency injection system makes it easy to:
- Swap implementations (e.g., replace in-memory with database)
- Test components in isolation
- Manage object lifecycle

## Step 5: Main Application Entry

```python
# main.py
from fastapi import FastAPI
from app.presentation.api.user_router import router as user_router

app = FastAPI(
    title="Microservices Tutorial",
    description="FastAPI microservices with Clean Architecture",
    version="1.0.0"
)

# Include routers
app.include_router(user_router, prefix="/api")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
```

## Testing the Clean Architecture

```bash
# Start the server
uvicorn main:app --reload

# Create a user
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"email":"john@example.com","name":"John Doe"}'

# View API documentation
open http://localhost:8000/docs
```

## Key Benefits

1. **Separation of Concerns**: Each layer has a single responsibility
2. **Testability**: You can test use cases without HTTP or database
3. **Flexibility**: Swap implementations without changing business logic
4. **Maintainability**: Changes are isolated to specific layers
5. **Type Safety**: Python type hints + Pydantic provide runtime validation

## FastAPI Advantages

- **Automatic API Documentation**: Swagger UI at `/docs`
- **Type Validation**: Pydantic validates request/response data
- **Async Support**: Built-in async/await support
- **Dependency Injection**: Clean dependency management
- **Performance**: One of the fastest Python frameworks

## Next Steps

- [Distributed Caching with Redis](./02-distributed-caching.md)
- [Message Queue with RabbitMQ](./03-message-queue.md)
