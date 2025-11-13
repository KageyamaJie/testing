# Microservices Architecture Tutorial: Node.js + TypeScript + Express.js

## Table of Contents
1. [Introduction](#introduction)
2. [Project Setup](#project-setup)
3. [Clean Architecture Implementation](#clean-architecture-implementation)
4. [Distributed Caching with Redis](#distributed-caching-with-redis)
5. [Message Queue with RabbitMQ](#message-queue-with-rabbitmq)
6. [Complete Example: User Service](#complete-example-user-service)

---

## Introduction

This tutorial guides you through building microservices using **Node.js**, **TypeScript**, and **Express.js** following **Clean Architecture** principles. We'll implement:
- **Clean Architecture** for maintainable, testable code
- **Distributed Caching** using Redis (similar to FusionCache in .NET)
- **Message Queue** using RabbitMQ (similar to MassTransit in .NET)

### Prerequisites
- Node.js 18+ installed
- Basic knowledge of TypeScript and Express.js
- Docker installed (for Redis and RabbitMQ)

---

## Project Setup

### Step 1: Initialize Project

```bash
mkdir microservices-nodejs
cd microservices-nodejs
npm init -y
npm install express cors dotenv
npm install -D typescript @types/node @types/express @types/cors ts-node nodemon
```

### Step 2: TypeScript Configuration

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
    "moduleResolution": "node"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules"]
}
```

### Step 3: Project Structure

```
microservices-nodejs/
├── src/
│   ├── domain/           # Business logic (entities, use cases)
│   ├── application/      # Application services
│   ├── infrastructure/   # External concerns (DB, cache, message queue)
│   ├── presentation/     # Controllers, routes
│   └── shared/           # Shared utilities
├── tsconfig.json
└── package.json
```

---

## Clean Architecture Implementation

Clean Architecture separates code into layers with clear dependencies:

```
┌─────────────────────────────────────┐
│   Presentation Layer (Controllers) │
├─────────────────────────────────────┤
│   Application Layer (Use Cases)    │
├─────────────────────────────────────┤
│   Domain Layer (Entities, Logic)   │
├─────────────────────────────────────┤
│   Infrastructure (DB, Cache, MQ)    │
└─────────────────────────────────────┘
```

### Domain Layer: Entities

**`src/domain/entities/User.ts`**

```typescript
/**
 * Domain Entity: User
 * 
 * This is the core business entity. It contains:
 * - Business rules and validation
 * - No dependencies on external frameworks
 * - Pure business logic
 */
export class User {
  constructor(
    public readonly id: string,
    public readonly email: string,
    public readonly name: string,
    public readonly createdAt: Date
  ) {
    // Business rule: Email must be valid
    if (!this.isValidEmail(email)) {
      throw new Error('Invalid email format');
    }
  }

  /**
   * Business logic: Validate email format
   * This is domain logic, not infrastructure concern
   */
  private isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  /**
   * Business logic: Check if user is active
   */
  isActive(): boolean {
    // Business rule: User is active if created within last 30 days
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    return this.createdAt >= thirtyDaysAgo;
  }
}
```

### Domain Layer: Repository Interface

**`src/domain/repositories/IUserRepository.ts`**

```typescript
import { User } from '../entities/User';

/**
 * Repository Interface (Port)
 * 
 * This defines WHAT we need, not HOW it's implemented.
 * Infrastructure layer will implement this interface.
 * This follows Dependency Inversion Principle.
 */
export interface IUserRepository {
  findById(id: string): Promise<User | null>;
  findByEmail(email: string): Promise<User | null>;
  save(user: User): Promise<User>;
  delete(id: string): Promise<void>;
}
```

### Application Layer: Use Cases

**`src/application/use-cases/CreateUserUseCase.ts`**

```typescript
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/repositories/IUserRepository';

/**
 * Use Case: Create User
 * 
 * This contains application-specific business logic:
 * - Orchestrates domain entities
 * - Coordinates with repositories
 * - Handles application-level concerns
 */
export class CreateUserUseCase {
  constructor(private userRepository: IUserRepository) {}

  /**
   * Execute the use case
   * 
   * This method:
   * 1. Creates domain entity (User)
   * 2. Validates business rules (handled by User entity)
   * 3. Persists via repository
   * 4. Returns result
   */
  async execute(email: string, name: string): Promise<User> {
    // Check if user already exists
    const existingUser = await this.userRepository.findByEmail(email);
    if (existingUser) {
      throw new Error('User with this email already exists');
    }

    // Create domain entity
    const user = new User(
      this.generateId(),
      email,
      name,
      new Date()
    );

    // Persist via repository
    return await this.userRepository.save(user);
  }

  private generateId(): string {
    return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

**`src/application/use-cases/GetUserUseCase.ts`**

```typescript
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/repositories/IUserRepository';

/**
 * Use Case: Get User by ID
 * 
 * This use case demonstrates:
 * - Simple data retrieval
 * - Error handling
 * - Application-level logic
 */
export class GetUserUseCase {
  constructor(private userRepository: IUserRepository) {}

  async execute(id: string): Promise<User> {
    const user = await this.userRepository.findById(id);
    
    if (!user) {
      throw new Error('User not found');
    }

    return user;
  }
}
```

### Infrastructure Layer: Repository Implementation

**`src/infrastructure/repositories/UserRepository.ts`**

```typescript
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/repositories/IUserRepository';

/**
 * Repository Implementation (Adapter)
 * 
 * This implements the repository interface using:
 * - In-memory storage (for simplicity)
 * - In production, this would use MongoDB, PostgreSQL, etc.
 * 
 * Key point: Domain layer doesn't know about this implementation!
 */
export class UserRepository implements IUserRepository {
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

### Presentation Layer: Controller

**`src/presentation/controllers/UserController.ts`**

```typescript
import { Request, Response } from 'express';
import { CreateUserUseCase } from '../../application/use-cases/CreateUserUseCase';
import { GetUserUseCase } from '../../application/use-cases/GetUserUseCase';

/**
 * Controller (Presentation Layer)
 * 
 * Responsibilities:
 * - Handle HTTP requests/responses
 * - Parse input data
 * - Call use cases
 * - Format responses
 * 
 * This layer knows about Express.js, but use cases don't!
 */
export class UserController {
  constructor(
    private createUserUseCase: CreateUserUseCase,
    private getUserUseCase: GetUserUseCase
  ) {}

  /**
   * POST /users
   * Create a new user
   */
  async createUser(req: Request, res: Response): Promise<void> {
    try {
      const { email, name } = req.body;

      // Validate input
      if (!email || !name) {
        res.status(400).json({ error: 'Email and name are required' });
        return;
      }

      // Execute use case
      const user = await this.createUserUseCase.execute(email, name);

      // Format response
      res.status(201).json({
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt
      });
    } catch (error: any) {
      res.status(400).json({ error: error.message });
    }
  }

  /**
   * GET /users/:id
   * Get user by ID
   */
  async getUser(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const user = await this.getUserUseCase.execute(id);

      res.json({
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt
      });
    } catch (error: any) {
      res.status(404).json({ error: error.message });
    }
  }
}
```

### Presentation Layer: Routes

**`src/presentation/routes/userRoutes.ts`**

```typescript
import { Router } from 'express';
import { UserController } from '../controllers/UserController';
import { CreateUserUseCase } from '../../application/use-cases/CreateUserUseCase';
import { GetUserUseCase } from '../../application/use-cases/GetUserUseCase';
import { UserRepository } from '../../infrastructure/repositories/UserRepository';

/**
 * Routes Configuration
 * 
 * This sets up:
 * - Dependency injection
 * - Route handlers
 * - Express middleware
 */
const router = Router();

// Dependency Injection Setup
// This is where we wire everything together
const userRepository = new UserRepository();
const createUserUseCase = new CreateUserUseCase(userRepository);
const getUserUseCase = new GetUserUseCase(userRepository);
const userController = new UserController(createUserUseCase, getUserUseCase);

// Define routes
router.post('/users', (req, res) => userController.createUser(req, res));
router.get('/users/:id', (req, res) => userController.getUser(req, res));

export default router;
```

### Main Application Entry Point

**`src/app.ts`**

```typescript
import express from 'express';
import cors from 'cors';
import userRoutes from './presentation/routes/userRoutes';

/**
 * Application Entry Point
 * 
 * This is where Express.js app is configured and started.
 */
const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api', userRoutes);

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

---

## Distributed Caching with Redis

Redis provides distributed caching similar to FusionCache in .NET. Let's implement a caching layer.

### Step 1: Install Dependencies

```bash
npm install redis ioredis
npm install -D @types/ioredis
```

### Step 2: Cache Service Interface

**`src/domain/services/ICacheService.ts`**

```typescript
/**
 * Cache Service Interface (Port)
 * 
 * Defines caching operations without knowing implementation details.
 */
export interface ICacheService {
  get<T>(key: string): Promise<T | null>;
  set(key: string, value: any, ttlSeconds?: number): Promise<void>;
  delete(key: string): Promise<void>;
  exists(key: string): Promise<boolean>;
}
```

### Step 3: Redis Cache Implementation

**`src/infrastructure/cache/RedisCacheService.ts`**

```typescript
import Redis from 'ioredis';
import { ICacheService } from '../../domain/services/ICacheService';

/**
 * Redis Cache Service Implementation
 * 
 * This implements distributed caching using Redis.
 * Similar to FusionCache in .NET, it provides:
 * - Get/Set operations
 * - TTL (Time To Live) support
 * - Distributed caching across multiple instances
 */
export class RedisCacheService implements ICacheService {
  private client: Redis;

  constructor(redisUrl?: string) {
    // Connect to Redis
    // In production, use connection pooling and error handling
    this.client = new Redis(redisUrl || 'redis://localhost:6379');
    
    this.client.on('error', (err) => {
      console.error('Redis Client Error:', err);
    });
  }

  /**
   * Get value from cache
   * 
   * @param key Cache key
   * @returns Cached value or null if not found
   */
  async get<T>(key: string): Promise<T | null> {
    try {
      const value = await this.client.get(key);
      if (!value) {
        return null;
      }
      return JSON.parse(value) as T;
    } catch (error) {
      console.error('Cache get error:', error);
      return null; // Fail gracefully
    }
  }

  /**
   * Set value in cache
   * 
   * @param key Cache key
   * @param value Value to cache
   * @param ttlSeconds Optional TTL in seconds
   */
  async set(key: string, value: any, ttlSeconds?: number): Promise<void> {
    try {
      const serialized = JSON.stringify(value);
      
      if (ttlSeconds) {
        // Set with expiration
        await this.client.setex(key, ttlSeconds, serialized);
      } else {
        // Set without expiration
        await this.client.set(key, serialized);
      }
    } catch (error) {
      console.error('Cache set error:', error);
      // Fail silently - cache is not critical
    }
  }

  /**
   * Delete value from cache
   */
  async delete(key: string): Promise<void> {
    try {
      await this.client.del(key);
    } catch (error) {
      console.error('Cache delete error:', error);
    }
  }

  /**
   * Check if key exists
   */
  async exists(key: string): Promise<boolean> {
    try {
      const result = await this.client.exists(key);
      return result === 1;
    } catch (error) {
      console.error('Cache exists error:', error);
      return false;
    }
  }

  /**
   * Close Redis connection
   */
  async disconnect(): Promise<void> {
    await this.client.quit();
  }
}
```

### Step 4: Cached Repository Decorator

**`src/infrastructure/repositories/CachedUserRepository.ts`**

```typescript
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/repositories/IUserRepository';
import { ICacheService } from '../../domain/services/ICacheService';

/**
 * Cached Repository Decorator
 * 
 * This is a decorator pattern implementation:
 * - Wraps the original repository
 * - Adds caching layer
 * - Transparent to the use cases
 * 
 * Similar to FusionCache's decorator pattern in .NET
 */
export class CachedUserRepository implements IUserRepository {
  private readonly CACHE_TTL = 300; // 5 minutes

  constructor(
    private repository: IUserRepository,
    private cache: ICacheService
  ) {}

  /**
   * Get user by ID with caching
   * 
   * Flow:
   * 1. Check cache first
   * 2. If cache hit, return cached value
   * 3. If cache miss, fetch from repository
   * 4. Store in cache for next time
   */
  async findById(id: string): Promise<User | null> {
    const cacheKey = `user:${id}`;

    // Try cache first
    const cached = await this.cache.get<User>(cacheKey);
    if (cached) {
      console.log(`Cache HIT for user:${id}`);
      // Reconstruct User entity from cached data
      return new User(
        cached.id,
        cached.email,
        cached.name,
        new Date(cached.createdAt)
      );
    }

    // Cache miss - fetch from repository
    console.log(`Cache MISS for user:${id}`);
    const user = await this.repository.findById(id);

    // Store in cache if found
    if (user) {
      await this.cache.set(cacheKey, {
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt.toISOString()
      }, this.CACHE_TTL);
    }

    return user;
  }

  async findByEmail(email: string): Promise<User | null> {
    const cacheKey = `user:email:${email}`;

    // Try cache first
    const cached = await this.cache.get<User>(cacheKey);
    if (cached) {
      return new User(
        cached.id,
        cached.email,
        cached.name,
        new Date(cached.createdAt)
      );
    }

    // Cache miss
    const user = await this.repository.findByEmail(email);

    if (user) {
      await this.cache.set(cacheKey, {
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt.toISOString()
      }, this.CACHE_TTL);
    }

    return user;
  }

  async save(user: User): Promise<User> {
    // Save to repository
    const savedUser = await this.repository.save(user);

    // Invalidate cache
    await this.cache.delete(`user:${savedUser.id}`);
    await this.cache.delete(`user:email:${savedUser.email}`);

    return savedUser;
  }

  async delete(id: string): Promise<void> {
    // Get user first to invalidate email cache
    const user = await this.repository.findById(id);

    // Delete from repository
    await this.repository.delete(id);

    // Invalidate cache
    await this.cache.delete(`user:${id}`);
    if (user) {
      await this.cache.delete(`user:email:${user.email}`);
    }
  }
}
```

### Step 5: Update Routes to Use Cached Repository

**`src/presentation/routes/userRoutes.ts`** (Updated)

```typescript
import { Router } from 'express';
import { UserController } from '../controllers/UserController';
import { CreateUserUseCase } from '../../application/use-cases/CreateUserUseCase';
import { GetUserUseCase } from '../../application/use-cases/GetUserUseCase';
import { UserRepository } from '../../infrastructure/repositories/UserRepository';
import { CachedUserRepository } from '../../infrastructure/repositories/CachedUserRepository';
import { RedisCacheService } from '../../infrastructure/cache/RedisCacheService';

const router = Router();

// Setup caching
const cacheService = new RedisCacheService(process.env.REDIS_URL);
const baseRepository = new UserRepository();
const cachedRepository = new CachedUserRepository(baseRepository, cacheService);

// Use cases with cached repository
const createUserUseCase = new CreateUserUseCase(cachedRepository);
const getUserUseCase = new GetUserUseCase(cachedRepository);
const userController = new UserController(createUserUseCase, getUserUseCase);

router.post('/users', (req, res) => userController.createUser(req, res));
router.get('/users/:id', (req, res) => userController.getUser(req, res));

export default router;
```

---

## Message Queue with RabbitMQ

RabbitMQ provides message queuing similar to MassTransit in .NET. Let's implement pub/sub pattern.

### Step 1: Install Dependencies

```bash
npm install amqplib
npm install -D @types/amqplib
```

### Step 2: Message Bus Interface

**`src/domain/services/IMessageBus.ts`**

```typescript
/**
 * Message Bus Interface (Port)
 * 
 * Defines messaging operations:
 * - Publish messages
 * - Subscribe to messages
 * 
 * Similar to MassTransit's IBus in .NET
 */
export interface IMessageBus {
  publish<T>(exchange: string, routingKey: string, message: T): Promise<void>;
  subscribe<T>(
    exchange: string,
    queue: string,
    routingKey: string,
    handler: (message: T) => Promise<void>
  ): Promise<void>;
}
```

### Step 3: RabbitMQ Message Bus Implementation

**`src/infrastructure/messaging/RabbitMQMessageBus.ts`**

```typescript
import amqp, { Connection, Channel } from 'amqplib';
import { IMessageBus } from '../../domain/services/IMessageBus';

/**
 * RabbitMQ Message Bus Implementation
 * 
 * This implements message queuing using RabbitMQ.
 * Similar to MassTransit in .NET, it provides:
 * - Publish/Subscribe pattern
 * - Exchange and queue management
 * - Message routing
 */
export class RabbitMQMessageBus implements IMessageBus {
  private connection: Connection | null = null;
  private channel: Channel | null = null;
  private readonly url: string;

  constructor(rabbitmqUrl?: string) {
    this.url = rabbitmqUrl || 'amqp://localhost:5672';
  }

  /**
   * Connect to RabbitMQ
   * 
   * This establishes connection and creates a channel.
   * In production, implement reconnection logic.
   */
  async connect(): Promise<void> {
    try {
      this.connection = await amqp.connect(this.url);
      this.channel = await this.connection.createChannel();

      this.connection.on('error', (err) => {
        console.error('RabbitMQ Connection Error:', err);
      });

      this.connection.on('close', () => {
        console.log('RabbitMQ Connection Closed');
      });

      console.log('Connected to RabbitMQ');
    } catch (error) {
      console.error('Failed to connect to RabbitMQ:', error);
      throw error;
    }
  }

  /**
   * Publish a message
   * 
   * @param exchange Exchange name (e.g., 'user.events')
   * @param routingKey Routing key (e.g., 'user.created')
   * @param message Message payload
   * 
   * Similar to MassTransit's Publish method
   */
  async publish<T>(exchange: string, routingKey: string, message: T): Promise<void> {
    if (!this.channel) {
      throw new Error('Not connected to RabbitMQ');
    }

    try {
      // Assert exchange exists (create if not)
      await this.channel.assertExchange(exchange, 'topic', {
        durable: true // Survive broker restart
      });

      // Publish message
      const messageBuffer = Buffer.from(JSON.stringify(message));
      const published = this.channel.publish(
        exchange,
        routingKey,
        messageBuffer,
        {
          persistent: true // Message survives broker restart
        }
      );

      if (!published) {
        throw new Error('Failed to publish message');
      }

      console.log(`Published message to ${exchange}:${routingKey}`);
    } catch (error) {
      console.error('Failed to publish message:', error);
      throw error;
    }
  }

  /**
   * Subscribe to messages
   * 
   * @param exchange Exchange name
   * @param queue Queue name
   * @param routingKey Routing key pattern (supports wildcards: *, #)
   * @param handler Message handler function
   * 
   * Similar to MassTransit's Consumer pattern
   */
  async subscribe<T>(
    exchange: string,
    queue: string,
    routingKey: string,
    handler: (message: T) => Promise<void>
  ): Promise<void> {
    if (!this.channel) {
      throw new Error('Not connected to RabbitMQ');
    }

    try {
      // Assert exchange
      await this.channel.assertExchange(exchange, 'topic', {
        durable: true
      });

      // Assert queue
      await this.channel.assertQueue(queue, {
        durable: true // Queue survives broker restart
      });

      // Bind queue to exchange with routing key
      await this.channel.bindQueue(queue, exchange, routingKey);

      // Consume messages
      await this.channel.consume(queue, async (msg) => {
        if (!msg) {
          return;
        }

        try {
          // Parse message
          const content = JSON.parse(msg.content.toString()) as T;
          
          // Handle message
          await handler(content);

          // Acknowledge message (remove from queue)
          this.channel!.ack(msg);
          
          console.log(`Processed message from ${queue}`);
        } catch (error) {
          console.error('Error processing message:', error);
          
          // Negative acknowledge (requeue message)
          this.channel!.nack(msg, false, true);
        }
      });

      console.log(`Subscribed to ${exchange}:${routingKey} via queue ${queue}`);
    } catch (error) {
      console.error('Failed to subscribe:', error);
      throw error;
    }
  }

  /**
   * Close connection
   */
  async disconnect(): Promise<void> {
    if (this.channel) {
      await this.channel.close();
    }
    if (this.connection) {
      await this.connection.close();
    }
  }
}
```

### Step 4: Domain Events

**`src/domain/events/UserCreatedEvent.ts`**

```typescript
/**
 * Domain Event: User Created
 * 
 * Domain events represent something important that happened in the domain.
 * Other services can subscribe to these events.
 */
export interface UserCreatedEvent {
  userId: string;
  email: string;
  name: string;
  createdAt: string;
}
```

### Step 5: Update Use Case to Publish Events

**`src/application/use-cases/CreateUserUseCase.ts`** (Updated)

```typescript
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/repositories/IUserRepository';
import { IMessageBus } from '../../domain/services/IMessageBus';
import { UserCreatedEvent } from '../../domain/events/UserCreatedEvent';

export class CreateUserUseCase {
  constructor(
    private userRepository: IUserRepository,
    private messageBus: IMessageBus
  ) {}

  async execute(email: string, name: string): Promise<User> {
    const existingUser = await this.userRepository.findByEmail(email);
    if (existingUser) {
      throw new Error('User with this email already exists');
    }

    const user = new User(
      this.generateId(),
      email,
      name,
      new Date()
    );

    const savedUser = await this.userRepository.save(user);

    // Publish domain event
    const event: UserCreatedEvent = {
      userId: savedUser.id,
      email: savedUser.email,
      name: savedUser.name,
      createdAt: savedUser.createdAt.toISOString()
    };

    await this.messageBus.publish(
      'user.events',
      'user.created',
      event
    );

    return savedUser;
  }

  private generateId(): string {
    return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

### Step 6: Event Handler (Consumer)

**`src/application/handlers/UserCreatedEventHandler.ts`**

```typescript
import { UserCreatedEvent } from '../../domain/events/UserCreatedEvent';

/**
 * Event Handler: User Created
 * 
 * This handles the UserCreatedEvent.
 * In a microservices architecture, this could be:
 * - Sending welcome email
 * - Creating user profile
 * - Updating analytics
 * - etc.
 */
export class UserCreatedEventHandler {
  async handle(event: UserCreatedEvent): Promise<void> {
    console.log('User Created Event Received:', event);
    
    // Example: Send welcome email
    console.log(`Sending welcome email to ${event.email}`);
    
    // Example: Create user profile
    console.log(`Creating profile for user ${event.userId}`);
    
    // Example: Update analytics
    console.log(`Updating user analytics`);
  }
}
```

### Step 7: Setup Event Subscription

**`src/infrastructure/messaging/eventSubscriptions.ts`**

```typescript
import { RabbitMQMessageBus } from './RabbitMQMessageBus';
import { UserCreatedEventHandler } from '../../application/handlers/UserCreatedEventHandler';
import { UserCreatedEvent } from '../../domain/events/UserCreatedEvent';

/**
 * Event Subscriptions Setup
 * 
 * This sets up all event subscriptions.
 * Similar to MassTransit's consumer configuration.
 */
export async function setupEventSubscriptions(messageBus: RabbitMQMessageBus): Promise<void> {
  const userCreatedHandler = new UserCreatedEventHandler();

  // Subscribe to user.created events
  await messageBus.subscribe<UserCreatedEvent>(
    'user.events',           // Exchange
    'user-service-queue',    // Queue name
    'user.created',          // Routing key
    async (event) => {
      await userCreatedHandler.handle(event);
    }
  );

  console.log('Event subscriptions configured');
}
```

### Step 8: Update App to Initialize Message Bus

**`src/app.ts`** (Updated)

```typescript
import express from 'express';
import cors from 'cors';
import userRoutes from './presentation/routes/userRoutes';
import { RabbitMQMessageBus } from './infrastructure/messaging/RabbitMQMessageBus';
import { setupEventSubscriptions } from './infrastructure/messaging/eventSubscriptions';

const app = express();

app.use(cors());
app.use(express.json());

app.use('/api', userRoutes);

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

const PORT = process.env.PORT || 3000;

// Initialize message bus
async function start() {
  try {
    // Connect to RabbitMQ
    const messageBus = new RabbitMQMessageBus(process.env.RABBITMQ_URL);
    await messageBus.connect();
    
    // Setup event subscriptions
    await setupEventSubscriptions(messageBus);

    // Start server
    app.listen(PORT, () => {
      console.log(`Server running on port ${PORT}`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

start();
```

### Step 9: Update Routes to Inject Message Bus

**`src/presentation/routes/userRoutes.ts`** (Final Version)

```typescript
import { Router } from 'express';
import { UserController } from '../controllers/UserController';
import { CreateUserUseCase } from '../../application/use-cases/CreateUserUseCase';
import { GetUserUseCase } from '../../application/use-cases/GetUserUseCase';
import { UserRepository } from '../../infrastructure/repositories/UserRepository';
import { CachedUserRepository } from '../../infrastructure/repositories/CachedUserRepository';
import { RedisCacheService } from '../../infrastructure/cache/RedisCacheService';
import { IMessageBus } from '../../domain/services/IMessageBus';

/**
 * Create routes with dependencies
 */
export function createUserRoutes(messageBus: IMessageBus) {
  const router = Router();

  // Setup caching
  const cacheService = new RedisCacheService(process.env.REDIS_URL);
  const baseRepository = new UserRepository();
  const cachedRepository = new CachedUserRepository(baseRepository, cacheService);

  // Use cases with dependencies
  const createUserUseCase = new CreateUserUseCase(cachedRepository, messageBus);
  const getUserUseCase = new GetUserUseCase(cachedRepository);
  const userController = new UserController(createUserUseCase, getUserUseCase);

  router.post('/users', (req, res) => userController.createUser(req, res));
  router.get('/users/:id', (req, res) => userController.getUser(req, res));

  return router;
}
```

**`src/app.ts`** (Final Version)

```typescript
import express from 'express';
import cors from 'cors';
import { createUserRoutes } from './presentation/routes/userRoutes';
import { RabbitMQMessageBus } from './infrastructure/messaging/RabbitMQMessageBus';
import { setupEventSubscriptions } from './infrastructure/messaging/eventSubscriptions';

const app = express();

app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

const PORT = process.env.PORT || 3000;

async function start() {
  try {
    // Initialize message bus
    const messageBus = new RabbitMQMessageBus(process.env.RABBITMQ_URL);
    await messageBus.connect();
    
    // Setup event subscriptions
    await setupEventSubscriptions(messageBus);

    // Setup routes with message bus
    app.use('/api', createUserRoutes(messageBus));

    // Start server
    app.listen(PORT, () => {
      console.log(`Server running on port ${PORT}`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

start();
```

---

## Complete Example: User Service

### Environment Variables

**`.env`**

```env
PORT=3000
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://localhost:5672
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

### Package.json Scripts

**`package.json`** (scripts section)

```json
{
  "scripts": {
    "build": "tsc",
    "start": "node dist/app.js",
    "dev": "nodemon --exec ts-node src/app.ts",
    "docker:up": "docker-compose up -d",
    "docker:down": "docker-compose down"
  }
}
```

### Running the Application

1. **Start infrastructure:**
   ```bash
   npm run docker:up
   ```

2. **Start the application:**
   ```bash
   npm run dev
   ```

3. **Test the API:**
   ```bash
   # Create user
   curl -X POST http://localhost:3000/api/users \
     -H "Content-Type: application/json" \
     -d '{"email":"john@example.com","name":"John Doe"}'

   # Get user
   curl http://localhost:3000/api/users/user_1234567890_abc123
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

1. Add database persistence (MongoDB, PostgreSQL)
2. Add authentication/authorization
3. Add API validation (Joi, Zod)
4. Add logging (Winston, Pino)
5. Add monitoring (Prometheus, Grafana)
6. Add unit and integration tests
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
