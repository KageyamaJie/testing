# Clean Architecture in Node.js + TypeScript

## What is Clean Architecture?

Clean Architecture is a design pattern that separates your code into layers, making it:
- **Testable** - Easy to write unit tests
- **Maintainable** - Changes in one layer don't affect others
- **Independent** - Business logic doesn't depend on frameworks or databases

## The Layers

```
┌─────────────────────────────────────┐
│      Presentation Layer             │  ← Controllers, Routes (Express)
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

```typescript
// src/domain/entities/User.ts

export class User {
  constructor(
    public readonly id: string,
    public readonly email: string,
    public readonly name: string,
    public readonly createdAt: Date
  ) {}

  // Business logic methods
  isActive(): boolean {
    return this.email.includes('@');
  }

  getDisplayName(): string {
    return `${this.name} (${this.email})`;
  }
}
```

**Why this matters:** The User entity contains business rules. It doesn't know about databases or HTTP requests.

### Repository Interface

```typescript
// src/domain/repositories/IUserRepository.ts

import { User } from '../entities/User';

export interface IUserRepository {
  findById(id: string): Promise<User | null>;
  findByEmail(email: string): Promise<User | null>;
  save(user: User): Promise<User>;
  delete(id: string): Promise<void>;
}
```

**Why this matters:** We define an interface (contract) in the domain layer. The actual implementation will be in the infrastructure layer.

## Step 2: Application Layer (Use Cases)

The application layer contains use cases - specific actions your application can perform.

### Create User Use Case

```typescript
// src/application/use-cases/CreateUserUseCase.ts

import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/repositories/IUserRepository';
import { CreateUserDTO } from '../dto/CreateUserDTO';

export class CreateUserUseCase {
  constructor(private userRepository: IUserRepository) {}

  async execute(dto: CreateUserDTO): Promise<User> {
    // Business validation
    if (!dto.email || !dto.email.includes('@')) {
      throw new Error('Invalid email address');
    }

    // Check if user already exists
    const existingUser = await this.userRepository.findByEmail(dto.email);
    if (existingUser) {
      throw new Error('User already exists');
    }

    // Create new user entity
    const user = new User(
      dto.id || this.generateId(),
      dto.email,
      dto.name,
      new Date()
    );

    // Save through repository
    return await this.userRepository.save(user);
  }

  private generateId(): string {
    return require('uuid').v4();
  }
}
```

**Explanation:**
- The use case orchestrates the business logic
- It uses the repository interface (not the implementation)
- It validates business rules before creating the user

### DTO (Data Transfer Object)

```typescript
// src/application/dto/CreateUserDTO.ts

export interface CreateUserDTO {
  id?: string;
  email: string;
  name: string;
}
```

## Step 3: Infrastructure Layer (External Concerns)

This layer implements the interfaces defined in the domain layer.

### In-Memory User Repository (for simplicity)

```typescript
// src/infrastructure/repositories/InMemoryUserRepository.ts

import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/repositories/IUserRepository';

export class InMemoryUserRepository implements IUserRepository {
  private users: Map<string, User> = new Map();

  async findById(id: string): Promise<User | null> {
    return this.users.get(id) || null;
  }

  async findByEmail(email: string): Promise<User | null> {
    const user = Array.from(this.users.values()).find(
      u => u.email === email
    );
    return user || null;
  }

  async save(user: User): Promise<User> {
    this.users.set(user.id, user);
    return user;
  }

  async delete(id: string): Promise<void> {
    this.users.delete(id);
  }
}
```

**Why this matters:** The domain layer doesn't care HOW users are stored. We can swap this with a database implementation later without changing domain or application code.

## Step 4: Presentation Layer (API)

The presentation layer handles HTTP requests and responses.

### User Controller

```typescript
// src/presentation/controllers/UserController.ts

import { Request, Response } from 'express';
import { CreateUserUseCase } from '../../application/use-cases/CreateUserUseCase';
import { CreateUserDTO } from '../../application/dto/CreateUserDTO';

export class UserController {
  constructor(private createUserUseCase: CreateUserUseCase) {}

  async createUser(req: Request, res: Response): Promise<void> {
    try {
      const dto: CreateUserDTO = {
        email: req.body.email,
        name: req.body.name,
      };

      const user = await this.createUserUseCase.execute(dto);

      res.status(201).json({
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt,
      });
    } catch (error) {
      res.status(400).json({
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }
}
```

**Explanation:**
- Controller handles HTTP concerns (request/response)
- It converts HTTP data to DTOs
- It calls use cases (not repositories directly)

### Routes

```typescript
// src/presentation/routes/userRoutes.ts

import { Router } from 'express';
import { UserController } from '../controllers/UserController';
import { CreateUserUseCase } from '../../application/use-cases/CreateUserUseCase';
import { InMemoryUserRepository } from '../../infrastructure/repositories/InMemoryUserRepository';

const router = Router();

// Dependency Injection (we'll improve this later)
const userRepository = new InMemoryUserRepository();
const createUserUseCase = new CreateUserUseCase(userRepository);
const userController = new UserController(createUserUseCase);

router.post('/users', (req, res) => userController.createUser(req, res));

export default router;
```

## Step 5: Main Application Entry

```typescript
// src/index.ts

import express from 'express';
import userRoutes from './presentation/routes/userRoutes';

const app = express();
app.use(express.json());

app.use('/api', userRoutes);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

## Testing the Clean Architecture

```bash
# Start the server
npm run dev

# Create a user
curl -X POST http://localhost:3000/api/users \
  -H "Content-Type: application/json" \
  -d '{"email":"john@example.com","name":"John Doe"}'
```

## Key Benefits

1. **Separation of Concerns**: Each layer has a single responsibility
2. **Testability**: You can test use cases without HTTP or database
3. **Flexibility**: Swap implementations without changing business logic
4. **Maintainability**: Changes are isolated to specific layers

## Next Steps

- [Distributed Caching with Redis](./02-distributed-caching.md)
- [Message Queue with RabbitMQ](./03-message-queue.md)
