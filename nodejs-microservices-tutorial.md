# Microservices Architecture Tutorial: Node.js + TypeScript with Express.js

## Table of Contents
1. [Introduction](#introduction)
2. [Clean Architecture Setup](#clean-architecture-setup)
3. [Distributed Caching Implementation](#distributed-caching-implementation)
4. [Message Queue with RabbitMQ](#message-queue-with-rabbitmq)
5. [Complete Example: User Service](#complete-example-user-service)

---

## Introduction

This tutorial will guide you through building a microservices architecture using Node.js, TypeScript, and Express.js. We'll implement:

- **Clean Architecture**: Separation of concerns with layers (Domain, Application, Infrastructure, Presentation)
- **Distributed Caching**: A FusionCache-like solution using Redis
- **Message Queue**: MassTransit-like abstraction using RabbitMQ

### Prerequisites
- Node.js 18+ and npm/yarn
- TypeScript knowledge (basic)
- Docker (for Redis and RabbitMQ)
- Understanding of REST APIs

---

## Clean Architecture Setup

Clean Architecture organizes code into layers, ensuring business logic is independent of frameworks and external concerns.

### Project Structure

```
user-service/
├── src/
│   ├── domain/           # Business entities and rules
│   │   ├── entities/
│   │   └── interfaces/
│   ├── application/      # Use cases and business logic
│   │   ├── use-cases/
│   │   └── dto/
│   ├── infrastructure/   # External concerns (DB, Cache, MQ)
│   │   ├── database/
│   │   ├── cache/
│   │   └── messaging/
│   └── presentation/     # API layer (Express routes)
│       ├── controllers/
│       ├── routes/
│       └── middleware/
├── package.json
└── tsconfig.json
```

### Step 1: Initialize Project

```bash
mkdir user-service && cd user-service
npm init -y
npm install express cors dotenv
npm install -D typescript @types/node @types/express @types/cors ts-node nodemon
```

### Step 2: Domain Layer - Entities

**File: `src/domain/entities/User.ts`**

```typescript
/**
 * Domain Entity: User
 * 
 * This represents the core business entity.
 * It contains only business logic and validation rules.
 * No framework dependencies here!
 */
export class User {
  constructor(
    public readonly id: string,
    public readonly email: string,
    public readonly name: string,
    public readonly createdAt: Date
  ) {
    this.validate();
  }

  /**
   * Business rule: Email must be valid
   */
  private validate(): void {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(this.email)) {
      throw new Error('Invalid email format');
    }
    if (!this.name || this.name.trim().length === 0) {
      throw new Error('Name is required');
    }
  }

  /**
   * Business logic: Check if user is active
   */
  public isActive(): boolean {
    // Business rule: Users created more than 30 days ago are considered active
    const daysSinceCreation = (Date.now() - this.createdAt.getTime()) / (1000 * 60 * 60 * 24);
    return daysSinceCreation > 30;
  }
}
```

**File: `src/domain/interfaces/IUserRepository.ts`**

```typescript
/**
 * Repository Interface (Domain Layer)
 * 
 * Defines what operations we need, not how they're implemented.
 * This keeps our domain independent of database technology.
 */
import { User } from '../entities/User';

export interface IUserRepository {
  findById(id: string): Promise<User | null>;
  findByEmail(email: string): Promise<User | null>;
  save(user: User): Promise<User>;
  delete(id: string): Promise<void>;
}
```

### Step 3: Application Layer - Use Cases

**File: `src/application/use-cases/CreateUserUseCase.ts`**

```typescript
/**
 * Use Case: Create User
 * 
 * This contains the application-specific business logic.
 * It orchestrates domain entities and repositories.
 */
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/interfaces/IUserRepository';

export interface CreateUserDto {
  email: string;
  name: string;
}

export class CreateUserUseCase {
  constructor(private userRepository: IUserRepository) {}

  /**
   * Execute the use case
   * 
   * This method:
   * 1. Validates business rules (via User entity)
   * 2. Checks for duplicates
   * 3. Saves the user
   * 4. Returns the result
   */
  async execute(dto: CreateUserDto): Promise<User> {
    // Check if user already exists
    const existingUser = await this.userRepository.findByEmail(dto.email);
    if (existingUser) {
      throw new Error('User with this email already exists');
    }

    // Create domain entity (this validates the data)
    const user = new User(
      this.generateId(),
      dto.email,
      dto.name,
      new Date()
    );

    // Save via repository
    return await this.userRepository.save(user);
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

**File: `src/application/use-cases/GetUserUseCase.ts`**

```typescript
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/interfaces/IUserRepository';

export class GetUserUseCase {
  constructor(private userRepository: IUserRepository) {}

  async execute(userId: string): Promise<User> {
    const user = await this.userRepository.findById(userId);
    if (!user) {
      throw new Error('User not found');
    }
    return user;
  }
}
```

### Step 4: Infrastructure Layer - Database Implementation

**File: `src/infrastructure/database/InMemoryUserRepository.ts`**

```typescript
/**
 * Infrastructure: In-Memory Repository Implementation
 * 
 * This implements the repository interface using in-memory storage.
 * In production, you'd use MongoDB, PostgreSQL, etc.
 * The domain layer doesn't care about this implementation!
 */
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/interfaces/IUserRepository';

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

### Step 5: Presentation Layer - Express Controllers

**File: `src/presentation/controllers/UserController.ts`**

```typescript
/**
 * Presentation Layer: User Controller
 * 
 * Handles HTTP requests/responses.
 * Delegates business logic to use cases.
 */
import { Request, Response } from 'express';
import { CreateUserUseCase } from '../../application/use-cases/CreateUserUseCase';
import { GetUserUseCase } from '../../application/use-cases/GetUserUseCase';

export class UserController {
  constructor(
    private createUserUseCase: CreateUserUseCase,
    private getUserUseCase: GetUserUseCase
  ) {}

  /**
   * POST /users
   * Creates a new user
   */
  async createUser(req: Request, res: Response): Promise<void> {
    try {
      const user = await this.createUserUseCase.execute({
        email: req.body.email,
        name: req.body.name,
      });

      res.status(201).json({
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt,
      });
    } catch (error: any) {
      res.status(400).json({ error: error.message });
    }
  }

  /**
   * GET /users/:id
   * Gets a user by ID
   */
  async getUser(req: Request, res: Response): Promise<void> {
    try {
      const user = await this.getUserUseCase.execute(req.params.id);
      res.json({
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt,
      });
    } catch (error: any) {
      res.status(404).json({ error: error.message });
    }
  }
}
```

**File: `src/presentation/routes/userRoutes.ts`**

```typescript
import { Router } from 'express';
import { UserController } from '../controllers/UserController';

export function createUserRoutes(userController: UserController): Router {
  const router = Router();

  router.post('/', (req, res) => userController.createUser(req, res));
  router.get('/:id', (req, res) => userController.getUser(req, res));

  return router;
}
```

---

## Distributed Caching Implementation

Now let's implement a FusionCache-like distributed caching solution using Redis.

### Step 1: Install Dependencies

```bash
npm install redis ioredis
npm install -D @types/ioredis
```

### Step 2: Create Cache Interface (Domain Layer)

**File: `src/domain/interfaces/ICacheService.ts`**

```typescript
/**
 * Cache Service Interface
 * 
 * Similar to FusionCache, provides a unified caching interface.
 * The implementation can be Redis, Memcached, or in-memory.
 */
export interface ICacheService {
  /**
   * Get value from cache
   * @param key Cache key
   * @returns Cached value or null if not found
   */
  get<T>(key: string): Promise<T | null>;

  /**
   * Set value in cache with expiration
   * @param key Cache key
   * @param value Value to cache
   * @param ttlSeconds Time to live in seconds (optional)
   */
  set<T>(key: string, value: T, ttlSeconds?: number): Promise<void>;

  /**
   * Delete value from cache
   * @param key Cache key
   */
  delete(key: string): Promise<void>;

  /**
   * Check if key exists in cache
   * @param key Cache key
   */
  exists(key: string): Promise<boolean>;

  /**
   * Get or set pattern (like FusionCache's GetOrSet)
   * If key exists, return cached value
   * If not, execute factory function, cache result, and return it
   */
  getOrSet<T>(
    key: string,
    factory: () => Promise<T>,
    ttlSeconds?: number
  ): Promise<T>;
}
```

### Step 3: Redis Implementation (Infrastructure Layer)

**File: `src/infrastructure/cache/RedisCacheService.ts`**

```typescript
/**
 * Infrastructure: Redis Cache Implementation
 * 
 * Implements distributed caching using Redis.
 * This is similar to FusionCache in .NET.
 */
import Redis from 'ioredis';
import { ICacheService } from '../../domain/interfaces/ICacheService';

export class RedisCacheService implements ICacheService {
  private client: Redis;

  constructor(redisUrl?: string) {
    // Connect to Redis
    // In production, use connection pooling and error handling
    this.client = new Redis(redisUrl || process.env.REDIS_URL || 'redis://localhost:6379');
    
    this.client.on('error', (err) => {
      console.error('Redis Client Error:', err);
    });
  }

  /**
   * Get value from Redis cache
   */
  async get<T>(key: string): Promise<T | null> {
    try {
      const value = await this.client.get(key);
      if (!value) return null;
      return JSON.parse(value) as T;
    } catch (error) {
      console.error(`Cache get error for key ${key}:`, error);
      return null;
    }
  }

  /**
   * Set value in Redis cache with optional TTL
   */
  async set<T>(key: string, value: T, ttlSeconds?: number): Promise<void> {
    try {
      const serialized = JSON.stringify(value);
      if (ttlSeconds) {
        await this.client.setex(key, ttlSeconds, serialized);
      } else {
        await this.client.set(key, serialized);
      }
    } catch (error) {
      console.error(`Cache set error for key ${key}:`, error);
      throw error;
    }
  }

  /**
   * Delete value from cache
   */
  async delete(key: string): Promise<void> {
    await this.client.del(key);
  }

  /**
   * Check if key exists
   */
  async exists(key: string): Promise<boolean> {
    const result = await this.client.exists(key);
    return result === 1;
  }

  /**
   * Get or Set pattern (FusionCache-like)
   * 
   * This is a powerful pattern:
   * 1. Try to get from cache
   * 2. If not found, execute factory function
   * 3. Cache the result
   * 4. Return the value
   * 
   * This prevents cache stampede and reduces code duplication.
   */
  async getOrSet<T>(
    key: string,
    factory: () => Promise<T>,
    ttlSeconds?: number
  ): Promise<T> {
    // Try to get from cache first
    const cached = await this.get<T>(key);
    if (cached !== null) {
      return cached;
    }

    // Cache miss - execute factory function
    const value = await factory();

    // Cache the result
    await this.set(key, value, ttlSeconds);

    return value;
  }

  /**
   * Close Redis connection
   */
  async disconnect(): Promise<void> {
    await this.client.quit();
  }
}
```

### Step 4: Use Cache in Use Cases

**File: `src/application/use-cases/GetUserUseCase.ts` (Updated)**

```typescript
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/interfaces/IUserRepository';
import { ICacheService } from '../../domain/interfaces/ICacheService';

export class GetUserUseCase {
  constructor(
    private userRepository: IUserRepository,
    private cacheService: ICacheService
  ) {}

  /**
   * Get user with caching
   * 
   * This demonstrates the getOrSet pattern:
   * - First checks cache
   * - If cache miss, fetches from repository
   * - Caches the result for 5 minutes
   * - Returns the user
   */
  async execute(userId: string): Promise<User> {
    const cacheKey = `user:${userId}`;
    const ttlSeconds = 300; // 5 minutes

    const user = await this.cacheService.getOrSet(
      cacheKey,
      async () => {
        // Factory function: executed only on cache miss
        const dbUser = await this.userRepository.findById(userId);
        if (!dbUser) {
          throw new Error('User not found');
        }
        return dbUser;
      },
      ttlSeconds
    );

    return user;
  }
}
```

---

## Message Queue with RabbitMQ

Now let's implement a MassTransit-like message queue abstraction using RabbitMQ.

### Step 1: Install Dependencies

```bash
npm install amqplib amqp-connection-manager
npm install -D @types/amqplib
```

### Step 2: Create Message Bus Interface (Domain Layer)

**File: `src/domain/interfaces/IMessageBus.ts`**

```typescript
/**
 * Message Bus Interface
 * 
 * Similar to MassTransit, provides abstraction over message queue.
 * Allows publishing and consuming messages without knowing RabbitMQ details.
 */

export interface IMessage {
  type: string;
  payload: any;
  timestamp: Date;
  correlationId?: string;
}

export interface IMessageBus {
  /**
   * Publish a message to an exchange
   * @param exchange Exchange name
   * @param routingKey Routing key (for topic exchanges)
   * @param message Message to publish
   */
  publish(exchange: string, routingKey: string, message: IMessage): Promise<void>;

  /**
   * Subscribe to messages from a queue
   * @param queue Queue name
   * @param handler Function to handle messages
   */
  subscribe<T extends IMessage>(
    queue: string,
    handler: (message: T) => Promise<void>
  ): Promise<void>;

  /**
   * Create a queue and bind it to an exchange
   * @param queue Queue name
   * @param exchange Exchange name
   * @param routingKey Routing key pattern
   */
  bindQueue(queue: string, exchange: string, routingKey: string): Promise<void>;
}
```

### Step 3: RabbitMQ Implementation (Infrastructure Layer)

**File: `src/infrastructure/messaging/RabbitMQMessageBus.ts`**

```typescript
/**
 * Infrastructure: RabbitMQ Message Bus Implementation
 * 
 * Implements message queue using RabbitMQ.
 * Similar to MassTransit in .NET.
 */
import amqp, { Connection, Channel } from 'amqplib';
import { connect } from 'amqp-connection-manager';
import { IMessageBus, IMessage } from '../../domain/interfaces/IMessageBus';

export class RabbitMQMessageBus implements IMessageBus {
  private connection: Connection | null = null;
  private channel: Channel | null = null;
  private connectionManager: any;

  constructor(private connectionUrl?: string) {
    const url = connectionUrl || process.env.RABBITMQ_URL || 'amqp://localhost:5672';
    
    // Use connection manager for automatic reconnection
    this.connectionManager = connect([url]);
    
    this.connectionManager.on('connect', () => {
      console.log('RabbitMQ connected');
    });

    this.connectionManager.on('disconnect', (err: Error) => {
      console.error('RabbitMQ disconnected:', err);
    });
  }

  /**
   * Initialize connection and channel
   */
  private async ensureChannel(): Promise<Channel> {
    if (!this.channel) {
      this.channel = await this.connectionManager.createChannel();
    }
    return this.channel;
  }

  /**
   * Publish a message to an exchange
   * 
   * This is similar to MassTransit's Publish method.
   * Messages are published to an exchange with a routing key.
   */
  async publish(exchange: string, routingKey: string, message: IMessage): Promise<void> {
    const channel = await this.ensureChannel();
    
    // Assert exchange exists (create if not)
    await channel.assertExchange(exchange, 'topic', {
      durable: true, // Survive broker restart
    });

    // Publish message
    const published = channel.publish(
      exchange,
      routingKey,
      Buffer.from(JSON.stringify(message)),
      {
        persistent: true, // Message survives broker restart
        timestamp: Date.now(),
        messageId: message.correlationId || this.generateId(),
      }
    );

    if (!published) {
      throw new Error('Failed to publish message - channel buffer full');
    }

    console.log(`Published message to ${exchange} with routing key ${routingKey}`);
  }

  /**
   * Subscribe to messages from a queue
   * 
   * This is similar to MassTransit's Consumer.
   * Messages are consumed from a queue and processed by the handler.
   */
  async subscribe<T extends IMessage>(
    queue: string,
    handler: (message: T) => Promise<void>
  ): Promise<void> {
    const channel = await this.ensureChannel();

    // Assert queue exists
    await channel.assertQueue(queue, {
      durable: true, // Queue survives broker restart
    });

    // Set prefetch to process one message at a time
    await channel.prefetch(1);

    // Consume messages
    await channel.consume(queue, async (msg) => {
      if (!msg) return;

      try {
        // Parse message
        const message: T = JSON.parse(msg.content.toString());

        // Process message
        await handler(message);

        // Acknowledge message (remove from queue)
        channel.ack(msg);
        console.log(`Processed message from queue ${queue}`);
      } catch (error) {
        console.error(`Error processing message from queue ${queue}:`, error);
        
        // Reject message and requeue (or send to dead letter queue)
        channel.nack(msg, false, true);
      }
    });

    console.log(`Subscribed to queue ${queue}`);
  }

  /**
   * Bind queue to exchange
   */
  async bindQueue(queue: string, exchange: string, routingKey: string): Promise<void> {
    const channel = await this.ensureChannel();
    await channel.bindQueue(queue, exchange, routingKey);
  }

  /**
   * Close connections
   */
  async close(): Promise<void> {
    if (this.channel) {
      await this.channel.close();
    }
    if (this.connection) {
      await this.connection.close();
    }
    await this.connectionManager.close();
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

### Step 4: Use Message Bus in Use Cases

**File: `src/application/use-cases/CreateUserUseCase.ts` (Updated)**

```typescript
import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/interfaces/IUserRepository';
import { IMessageBus, IMessage } from '../../domain/interfaces/IMessageBus';

export interface CreateUserDto {
  email: string;
  name: string;
}

export class CreateUserUseCase {
  constructor(
    private userRepository: IUserRepository,
    private messageBus: IMessageBus
  ) {}

  async execute(dto: CreateUserDto): Promise<User> {
    const existingUser = await this.userRepository.findByEmail(dto.email);
    if (existingUser) {
      throw new Error('User with this email already exists');
    }

    const user = new User(
      this.generateId(),
      dto.email,
      dto.name,
      new Date()
    );

    const savedUser = await this.userRepository.save(user);

    // Publish event: UserCreated
    // This allows other services to react to user creation
    const event: IMessage = {
      type: 'UserCreated',
      payload: {
        userId: savedUser.id,
        email: savedUser.email,
        name: savedUser.name,
      },
      timestamp: new Date(),
      correlationId: savedUser.id,
    };

    await this.messageBus.publish('user-events', 'user.created', event);

    return savedUser;
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

### Step 5: Create Event Handler (Consumer)

**File: `src/application/handlers/UserCreatedHandler.ts`**

```typescript
/**
 * Event Handler: User Created
 * 
 * This handles UserCreated events from the message queue.
 * Similar to MassTransit consumers.
 */
import { IMessage } from '../../domain/interfaces/IMessageBus';

export class UserCreatedHandler {
  /**
   * Handle UserCreated event
   * 
   * This could:
   * - Send welcome email
   * - Create user profile
   * - Update analytics
   * - etc.
   */
  async handle(message: IMessage): Promise<void> {
    console.log('UserCreated event received:', message.payload);

    // Example: Send welcome email (simulated)
    await this.sendWelcomeEmail(message.payload.email);

    // Example: Update analytics
    await this.updateAnalytics(message.payload.userId);
  }

  private async sendWelcomeEmail(email: string): Promise<void> {
    console.log(`Sending welcome email to ${email}`);
    // In production, integrate with email service
  }

  private async updateAnalytics(userId: string): Promise<void> {
    console.log(`Updating analytics for user ${userId}`);
    // In production, send to analytics service
  }
}
```

---

## Complete Example: User Service

### Step 1: Dependency Injection Setup

**File: `src/infrastructure/di/container.ts`**

```typescript
/**
 * Dependency Injection Container
 * 
 * This wires up all dependencies.
 * In production, use a DI library like InversifyJS or TSyringe.
 */
import { InMemoryUserRepository } from '../database/InMemoryUserRepository';
import { RedisCacheService } from '../cache/RedisCacheService';
import { RabbitMQMessageBus } from '../messaging/RabbitMQMessageBus';
import { CreateUserUseCase } from '../../application/use-cases/CreateUserUseCase';
import { GetUserUseCase } from '../../application/use-cases/GetUserUseCase';
import { UserController } from '../../presentation/controllers/UserController';
import { UserCreatedHandler } from '../../application/handlers/UserCreatedHandler';

export class Container {
  // Infrastructure
  private userRepository = new InMemoryUserRepository();
  private cacheService = new RedisCacheService();
  private messageBus = new RabbitMQMessageBus();

  // Use Cases
  private createUserUseCase = new CreateUserUseCase(
    this.userRepository,
    this.messageBus
  );
  private getUserUseCase = new GetUserUseCase(
    this.userRepository,
    this.cacheService
  );

  // Handlers
  private userCreatedHandler = new UserCreatedHandler();

  // Controllers
  public userController = new UserController(
    this.createUserUseCase,
    this.getUserUseCase
  );

  /**
   * Initialize message queue subscriptions
   */
  async initialize(): Promise<void> {
    // Subscribe to user events
    await this.messageBus.bindQueue('user-created-queue', 'user-events', 'user.created');
    await this.messageBus.subscribe('user-created-queue', async (message) => {
      await this.userCreatedHandler.handle(message);
    });
  }

  /**
   * Cleanup resources
   */
  async cleanup(): Promise<void> {
    await this.cacheService.disconnect();
    await this.messageBus.close();
  }
}
```

### Step 2: Application Entry Point

**File: `src/app.ts`**

```typescript
/**
 * Application Entry Point
 * 
 * Sets up Express server and initializes all components.
 */
import express, { Express } from 'express';
import cors from 'cors';
import { Container } from './infrastructure/di/container';
import { createUserRoutes } from './presentation/routes/userRoutes';

const app: Express = express();
const container = new Container();

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/users', createUserRoutes(container.userController));

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Initialize message queue
container.initialize().catch(console.error);

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  await container.cleanup();
  process.exit(0);
});
```

### Step 3: Configuration Files

**File: `tsconfig.json`**

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

**File: `package.json` (scripts section)**

```json
{
  "scripts": {
    "dev": "nodemon --exec ts-node src/app.ts",
    "build": "tsc",
    "start": "node dist/app.js"
  }
}
```

**File: `.env.example`**

```env
PORT=3000
REDIS_URL=redis://localhost:6379
RABBITMQ_URL=amqp://localhost:5672
```

### Step 4: Docker Compose for Dependencies

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
npm install

# Run in development
npm run dev

# Build for production
npm run build
npm start
```

---

## Key Concepts Explained

### Clean Architecture Benefits

1. **Independence**: Business logic doesn't depend on Express, Redis, or RabbitMQ
2. **Testability**: Easy to mock interfaces and test use cases
3. **Flexibility**: Swap Redis for Memcached without changing business logic
4. **Maintainability**: Clear separation makes code easier to understand

### Distributed Caching Pattern

The `getOrSet` pattern (like FusionCache) provides:
- **Cache-aside**: Check cache first, fallback to database
- **Automatic caching**: Factory function only runs on cache miss
- **TTL support**: Automatic expiration

### Message Queue Pattern

The message bus abstraction (like MassTransit) provides:
- **Decoupling**: Services communicate via events, not direct calls
- **Reliability**: Messages are persisted and retried on failure
- **Scalability**: Multiple consumers can process messages in parallel

---

## Next Steps

1. Add error handling middleware
2. Implement request validation (use class-validator)
3. Add logging (Winston or Pino)
4. Add unit tests (Jest)
5. Add integration tests
6. Implement database persistence (MongoDB, PostgreSQL)
7. Add API documentation (Swagger/OpenAPI)

---

## Summary

You've learned:
- ✅ Clean Architecture with TypeScript
- ✅ Distributed caching with Redis (FusionCache-like)
- ✅ Message queue with RabbitMQ (MassTransit-like)
- ✅ How to structure a microservice

This architecture is production-ready and can scale horizontally!
