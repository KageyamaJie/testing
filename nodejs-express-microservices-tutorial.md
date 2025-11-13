# Microservices Architecture Tutorial: Node.js + TypeScript + Express.js

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

This tutorial will guide you through building a microservices architecture using Node.js, TypeScript, and Express.js. We'll implement:

- **Clean Architecture**: Separation of concerns with clear layer boundaries
- **Distributed Caching**: Using Redis (similar to FusionCache in .NET)
- **Message Queue**: Using RabbitMQ (similar to MassTransit in .NET)

### Prerequisites
- Node.js 18+ installed
- Basic knowledge of TypeScript and Express.js
- Docker installed (for Redis and RabbitMQ)

---

## Project Setup

### Step 1: Initialize the Project

```bash
mkdir microservices-tutorial
cd microservices-tutorial
npm init -y
```

### Step 2: Install Dependencies

```bash
# Core dependencies
npm install express
npm install ioredis          # Redis client for distributed caching
npm install amqplib          # RabbitMQ client
npm install dotenv           # Environment variables

# TypeScript dependencies
npm install -D typescript @types/node @types/express @types/amqplib
npm install -D ts-node nodemon @typescript-eslint/eslint-plugin @typescript-eslint/parser

# Development tools
npm install -D eslint prettier
```

### Step 3: TypeScript Configuration

Create `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "moduleResolution": "node",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
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
├── package.json
└── tsconfig.json
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

Create `src/domain/entities/User.ts`:

```typescript
/**
 * Domain Entity: User
 * 
 * This represents the core business entity. It contains only business logic
 * and has no dependencies on external frameworks or libraries.
 */
export class User {
  constructor(
    public readonly id: string,
    public readonly email: string,
    public readonly name: string,
    public readonly createdAt: Date
  ) {}

  /**
   * Business logic: Validate user email format
   */
  isValidEmail(): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(this.email);
  }

  /**
   * Business logic: Check if user is recently created
   */
  isRecentlyCreated(days: number = 7): boolean {
    const daysSinceCreation = 
      (Date.now() - this.createdAt.getTime()) / (1000 * 60 * 60 * 24);
    return daysSinceCreation <= days;
  }
}
```

### Step 2: Domain Layer - Repository Interfaces

Create `src/domain/interfaces/IUserRepository.ts`:

```typescript
import { User } from '../entities/User';

/**
 * Repository Interface (Domain Layer)
 * 
 * This interface defines what operations we need, not how they're implemented.
 * The implementation will be in the Infrastructure layer.
 */
export interface IUserRepository {
  findById(id: string): Promise<User | null>;
  findByEmail(email: string): Promise<User | null>;
  save(user: User): Promise<User>;
  delete(id: string): Promise<void>;
}
```

### Step 3: Application Layer - Use Cases

Create `src/application/usecases/GetUserUseCase.ts`:

```typescript
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/interfaces/IUserRepository';
import { ICacheService } from '../../domain/interfaces/ICacheService';

/**
 * Use Case: Get User by ID
 * 
 * This orchestrates the business logic:
 * 1. Check cache first
 * 2. If not in cache, fetch from repository
 * 3. Store in cache for future requests
 */
export class GetUserUseCase {
  constructor(
    private userRepository: IUserRepository,
    private cacheService: ICacheService
  ) {}

  async execute(userId: string): Promise<User | null> {
    // Check cache first (distributed caching)
    const cacheKey = `user:${userId}`;
    const cachedUser = await this.cacheService.get<User>(cacheKey);
    
    if (cachedUser) {
      console.log(`Cache hit for user ${userId}`);
      return cachedUser;
    }

    // Cache miss - fetch from repository
    console.log(`Cache miss for user ${userId}`);
    const user = await this.userRepository.findById(userId);

    if (user) {
      // Store in cache for 1 hour (3600 seconds)
      await this.cacheService.set(cacheKey, user, 3600);
    }

    return user;
  }
}
```

Create `src/application/usecases/CreateUserUseCase.ts`:

```typescript
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/interfaces/IUserRepository';
import { IMessagePublisher } from '../../domain/interfaces/IMessagePublisher';

/**
 * Use Case: Create User
 * 
 * This demonstrates:
 * 1. Business logic validation
 * 2. Repository interaction
 * 3. Event publishing (message queue)
 */
export class CreateUserUseCase {
  constructor(
    private userRepository: IUserRepository,
    private messagePublisher: IMessagePublisher
  ) {}

  async execute(email: string, name: string): Promise<User> {
    // Business logic validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      throw new Error('Invalid email format');
    }

    if (!name || name.trim().length === 0) {
      throw new Error('Name is required');
    }

    // Check if user already exists
    const existingUser = await this.userRepository.findByEmail(email);
    if (existingUser) {
      throw new Error('User with this email already exists');
    }

    // Create new user
    const user = new User(
      this.generateId(),
      email,
      name,
      new Date()
    );

    // Save to repository
    const savedUser = await this.userRepository.save(user);

    // Publish event to message queue (asynchronous processing)
    await this.messagePublisher.publish('user.created', {
      userId: savedUser.id,
      email: savedUser.email,
      name: savedUser.name,
      timestamp: savedUser.createdAt.toISOString()
    });

    return savedUser;
  }

  private generateId(): string {
    return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

### Step 4: Infrastructure Layer - Cache Service

Create `src/infrastructure/cache/RedisCacheService.ts`:

```typescript
import Redis from 'ioredis';
import { ICacheService } from '../../domain/interfaces/ICacheService';

/**
 * Redis Cache Service Implementation
 * 
 * This is similar to FusionCache in .NET:
 * - Distributed caching across multiple instances
 * - TTL (Time To Live) support
 * - Automatic serialization/deserialization
 */
export class RedisCacheService implements ICacheService {
  private redis: Redis;

  constructor(redisUrl: string) {
    this.redis = new Redis(redisUrl, {
      retryStrategy: (times) => {
        const delay = Math.min(times * 50, 2000);
        return delay;
      },
      maxRetriesPerRequest: 3
    });

    this.redis.on('error', (err) => {
      console.error('Redis connection error:', err);
    });

    this.redis.on('connect', () => {
      console.log('Connected to Redis');
    });
  }

  /**
   * Get value from cache
   */
  async get<T>(key: string): Promise<T | null> {
    try {
      const value = await this.redis.get(key);
      if (!value) {
        return null;
      }
      return JSON.parse(value) as T;
    } catch (error) {
      console.error(`Cache get error for key ${key}:`, error);
      return null; // Fail gracefully - return null instead of throwing
    }
  }

  /**
   * Set value in cache with optional TTL
   * @param key Cache key
   * @param value Value to cache
   * @param ttlSeconds Time to live in seconds (optional)
   */
  async set<T>(key: string, value: T, ttlSeconds?: number): Promise<void> {
    try {
      const serialized = JSON.stringify(value);
      if (ttlSeconds) {
        await this.redis.setex(key, ttlSeconds, serialized);
      } else {
        await this.redis.set(key, serialized);
      }
    } catch (error) {
      console.error(`Cache set error for key ${key}:`, error);
      // Fail gracefully - don't throw, just log
    }
  }

  /**
   * Delete value from cache
   */
  async delete(key: string): Promise<void> {
    try {
      await this.redis.del(key);
    } catch (error) {
      console.error(`Cache delete error for key ${key}:`, error);
    }
  }

  /**
   * Check if key exists in cache
   */
  async exists(key: string): Promise<boolean> {
    try {
      const result = await this.redis.exists(key);
      return result === 1;
    } catch (error) {
      console.error(`Cache exists error for key ${key}:`, error);
      return false;
    }
  }

  /**
   * Clear all cache (use with caution!)
   */
  async clear(): Promise<void> {
    try {
      await this.redis.flushdb();
    } catch (error) {
      console.error('Cache clear error:', error);
    }
  }
}
```

### Step 5: Infrastructure Layer - Message Queue Service

Create `src/infrastructure/messaging/RabbitMQService.ts`:

```typescript
import amqp, { Connection, Channel } from 'amqplib';
import { IMessagePublisher, IMessageConsumer } from '../../domain/interfaces/IMessagePublisher';

/**
 * RabbitMQ Service Implementation
 * 
 * This is similar to MassTransit in .NET:
 * - Publish/subscribe pattern
 * - Queue management
 * - Message routing
 * - Consumer handling
 */
export class RabbitMQService implements IMessagePublisher, IMessageConsumer {
  private connection: Connection | null = null;
  private channel: Channel | null = null;
  private readonly exchangeName: string = 'microservices_exchange';
  private readonly exchangeType: string = 'topic';

  constructor(private connectionUrl: string) {}

  /**
   * Connect to RabbitMQ
   */
  async connect(): Promise<void> {
    try {
      this.connection = await amqp.connect(this.connectionUrl);
      this.channel = await this.connection.createChannel();

      // Declare exchange (similar to MassTransit's exchange)
      await this.channel.assertExchange(
        this.exchangeName,
        this.exchangeType,
        { durable: true } // Survive broker restarts
      );

      console.log('Connected to RabbitMQ');
    } catch (error) {
      console.error('RabbitMQ connection error:', error);
      throw error;
    }
  }

  /**
   * Publish message to exchange
   * Similar to MassTransit's Publish method
   */
  async publish(routingKey: string, message: any): Promise<void> {
    if (!this.channel) {
      throw new Error('RabbitMQ channel not initialized. Call connect() first.');
    }

    try {
      const messageBuffer = Buffer.from(JSON.stringify(message));
      
      this.channel.publish(
        this.exchangeName,
        routingKey,
        messageBuffer,
        {
          persistent: true, // Message survives broker restarts
          timestamp: Date.now()
        }
      );

      console.log(`Published message to ${routingKey}:`, message);
    } catch (error) {
      console.error(`Error publishing message to ${routingKey}:`, error);
      throw error;
    }
  }

  /**
   * Subscribe to messages
   * Similar to MassTransit's Consumer
   */
  async subscribe(
    queueName: string,
    routingKey: string,
    handler: (message: any) => Promise<void>
  ): Promise<void> {
    if (!this.channel) {
      throw new Error('RabbitMQ channel not initialized. Call connect() first.');
    }

    try {
      // Declare queue
      await this.channel.assertQueue(queueName, {
        durable: true // Queue survives broker restarts
      });

      // Bind queue to exchange with routing key
      await this.channel.bindQueue(
        queueName,
        this.exchangeName,
        routingKey
      );

      // Consume messages
      await this.channel.consume(
        queueName,
        async (msg) => {
          if (!msg) {
            return;
          }

          try {
            const content = JSON.parse(msg.content.toString());
            console.log(`Received message on ${queueName}:`, content);

            // Process message
            await handler(content);

            // Acknowledge message (remove from queue)
            this.channel!.ack(msg);
          } catch (error) {
            console.error(`Error processing message on ${queueName}:`, error);
            // Reject message and requeue
            this.channel!.nack(msg, false, true);
          }
        },
        { noAck: false } // Manual acknowledgment
      );

      console.log(`Subscribed to queue ${queueName} with routing key ${routingKey}`);
    } catch (error) {
      console.error(`Error subscribing to ${queueName}:`, error);
      throw error;
    }
  }

  /**
   * Close connections
   */
  async disconnect(): Promise<void> {
    try {
      if (this.channel) {
        await this.channel.close();
      }
      if (this.connection) {
        await this.connection.close();
      }
      console.log('Disconnected from RabbitMQ');
    } catch (error) {
      console.error('Error disconnecting from RabbitMQ:', error);
    }
  }
}
```

### Step 6: Domain Interfaces for Infrastructure

Create `src/domain/interfaces/ICacheService.ts`:

```typescript
/**
 * Cache Service Interface
 * 
 * This abstraction allows us to swap cache implementations
 * without changing business logic.
 */
export interface ICacheService {
  get<T>(key: string): Promise<T | null>;
  set<T>(key: string, value: T, ttlSeconds?: number): Promise<void>;
  delete(key: string): Promise<void>;
  exists(key: string): Promise<boolean>;
  clear(): Promise<void>;
}
```

Create `src/domain/interfaces/IMessagePublisher.ts`:

```typescript
/**
 * Message Publisher/Consumer Interfaces
 * 
 * These abstractions allow us to swap messaging implementations
 * without changing business logic.
 */
export interface IMessagePublisher {
  publish(routingKey: string, message: any): Promise<void>;
}

export interface IMessageConsumer {
  subscribe(
    queueName: string,
    routingKey: string,
    handler: (message: any) => Promise<void>
  ): Promise<void>;
}
```

### Step 7: Infrastructure Layer - Repository Implementation

Create `src/infrastructure/repositories/InMemoryUserRepository.ts`:

```typescript
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/interfaces/IUserRepository';

/**
 * In-Memory User Repository
 * 
 * For simplicity, we're using in-memory storage.
 * In production, this would connect to a database.
 */
export class InMemoryUserRepository implements IUserRepository {
  private users: Map<string, User> = new Map();

  async findById(id: string): Promise<User | null> {
    return this.users.get(id) || null;
  }

  async findByEmail(email: string): Promise<User | null> {
    for (const user of this.users.values()) {
      if (user.email === email) {
        return user;
      }
    }
    return null;
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

### Step 8: Presentation Layer - Controllers

Create `src/presentation/controllers/UserController.ts`:

```typescript
import { Request, Response } from 'express';
import { GetUserUseCase } from '../../application/usecases/GetUserUseCase';
import { CreateUserUseCase } from '../../application/usecases/CreateUserUseCase';

/**
 * User Controller
 * 
 * This handles HTTP requests and delegates to use cases.
 * It's part of the Presentation layer.
 */
export class UserController {
  constructor(
    private getUserUseCase: GetUserUseCase,
    private createUserUseCase: CreateUserUseCase
  ) {}

  /**
   * GET /users/:id
   */
  async getUser(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const user = await this.getUserUseCase.execute(id);

      if (!user) {
        res.status(404).json({ error: 'User not found' });
        return;
      }

      res.json({
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt
      });
    } catch (error) {
      console.error('Error getting user:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  /**
   * POST /users
   */
  async createUser(req: Request, res: Response): Promise<void> {
    try {
      const { email, name } = req.body;

      if (!email || !name) {
        res.status(400).json({ error: 'Email and name are required' });
        return;
      }

      const user = await this.createUserUseCase.execute(email, name);

      res.status(201).json({
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt
      });
    } catch (error: any) {
      console.error('Error creating user:', error);
      
      if (error.message.includes('already exists') || 
          error.message.includes('Invalid')) {
        res.status(400).json({ error: error.message });
      } else {
        res.status(500).json({ error: 'Internal server error' });
      }
    }
  }
}
```

### Step 9: Presentation Layer - Routes

Create `src/presentation/routes/userRoutes.ts`:

```typescript
import { Router } from 'express';
import { UserController } from '../controllers/UserController';

export function createUserRoutes(userController: UserController): Router {
  const router = Router();

  router.get('/:id', (req, res) => userController.getUser(req, res));
  router.post('/', (req, res) => userController.createUser(req, res));

  return router;
}
```

### Step 10: Application Entry Point

Create `src/app.ts`:

```typescript
import express from 'express';
import dotenv from 'dotenv';
import { InMemoryUserRepository } from './infrastructure/repositories/InMemoryUserRepository';
import { RedisCacheService } from './infrastructure/cache/RedisCacheService';
import { RabbitMQService } from './infrastructure/messaging/RabbitMQService';
import { GetUserUseCase } from './application/usecases/GetUserUseCase';
import { CreateUserUseCase } from './application/usecases/CreateUserUseCase';
import { UserController } from './presentation/controllers/UserController';
import { createUserRoutes } from './presentation/routes/userRoutes';

dotenv.config();

async function bootstrap() {
  const app = express();
  app.use(express.json());

  // Initialize infrastructure services
  const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
  const rabbitmqUrl = process.env.RABBITMQ_URL || 'amqp://localhost:5672';

  const cacheService = new RedisCacheService(redisUrl);
  const messageService = new RabbitMQService(rabbitmqUrl);
  
  // Connect to RabbitMQ
  await messageService.connect();

  // Initialize repositories
  const userRepository = new InMemoryUserRepository();

  // Initialize use cases
  const getUserUseCase = new GetUserUseCase(userRepository, cacheService);
  const createUserUseCase = new CreateUserUseCase(
    userRepository,
    messageService
  );

  // Initialize controllers
  const userController = new UserController(
    getUserUseCase,
    createUserUseCase
  );

  // Setup routes
  app.use('/users', createUserRoutes(userController));

  // Health check endpoint
  app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  // Setup message consumers
  await messageService.subscribe(
    'user_created_queue',
    'user.created',
    async (message) => {
      console.log('Processing user.created event:', message);
      // Here you could:
      // - Send welcome email
      // - Update analytics
      // - Notify other services
      // - etc.
    }
  );

  const port = process.env.PORT || 3000;
  app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });
}

bootstrap().catch(console.error);
```

### Step 11: Environment Configuration

Create `.env`:

```env
PORT=3000
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://guest:guest@localhost:5672
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

### Step 13: Package.json Scripts

Update `package.json`:

```json
{
  "scripts": {
    "build": "tsc",
    "start": "node dist/app.js",
    "dev": "nodemon --exec ts-node src/app.ts",
    "lint": "eslint src/**/*.ts"
  }
}
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
npm run dev
```

3. **Test the API:**

Create a user:
```bash
curl -X POST http://localhost:3000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "name": "John Doe"}'
```

Get a user (with caching):
```bash
curl http://localhost:3000/users/{userId}
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
- Always handle errors gracefully
- Don't expose internal errors to clients
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

---

## Summary

This tutorial demonstrated:

✅ **Clean Architecture**: Clear separation of concerns across layers  
✅ **Distributed Caching**: Redis implementation similar to FusionCache  
✅ **Message Queue**: RabbitMQ implementation similar to MassTransit  
✅ **TypeScript**: Type-safe code throughout  
✅ **Express.js**: RESTful API endpoints  

The architecture is scalable, maintainable, and follows industry best practices for microservices.
