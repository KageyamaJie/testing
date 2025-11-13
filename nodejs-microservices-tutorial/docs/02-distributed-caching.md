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

## Architecture

```
┌─────────────┐
│   Express   │
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

```typescript
// src/domain/repositories/ICacheRepository.ts

export interface ICacheRepository {
  get<T>(key: string): Promise<T | null>;
  set(key: string, value: any, ttlSeconds?: number): Promise<void>;
  delete(key: string): Promise<void>;
  exists(key: string): Promise<boolean>;
}
```

**Why in domain layer?** The domain layer defines contracts. The infrastructure layer implements them.

## Step 2: Redis Implementation (Infrastructure Layer)

```typescript
// src/infrastructure/cache/RedisCacheRepository.ts

import Redis from 'ioredis';
import { ICacheRepository } from '../../domain/repositories/ICacheRepository';

export class RedisCacheRepository implements ICacheRepository {
  private client: Redis;

  constructor() {
    this.client = new Redis({
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
      retryStrategy: (times) => {
        const delay = Math.min(times * 50, 2000);
        return delay;
      },
    });

    this.client.on('error', (err) => {
      console.error('Redis Client Error:', err);
    });
  }

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

  async set(
    key: string,
    value: any,
    ttlSeconds?: number
  ): Promise<void> {
    try {
      const serialized = JSON.stringify(value);
      if (ttlSeconds) {
        await this.client.setex(key, ttlSeconds, serialized);
      } else {
        await this.client.set(key, serialized);
      }
    } catch (error) {
      console.error(`Cache set error for key ${key}:`, error);
      // Don't throw - cache failures shouldn't break the app
    }
  }

  async delete(key: string): Promise<void> {
    try {
      await this.client.del(key);
    } catch (error) {
      console.error(`Cache delete error for key ${key}:`, error);
    }
  }

  async exists(key: string): Promise<boolean> {
    try {
      const result = await this.client.exists(key);
      return result === 1;
    } catch (error) {
      console.error(`Cache exists error for key ${key}:`, error);
      return false;
    }
  }

  async disconnect(): Promise<void> {
    await this.client.quit();
  }
}
```

**Explanation:**
- Uses `ioredis` library (popular Redis client for Node.js)
- Handles errors gracefully (cache failures shouldn't crash the app)
- Supports TTL (Time To Live) for automatic expiration
- Serializes/deserializes JSON automatically

## Step 3: Cached User Repository

Now, let's create a cached version of the user repository:

```typescript
// src/infrastructure/repositories/CachedUserRepository.ts

import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/repositories/IUserRepository';
import { ICacheRepository } from '../../domain/repositories/ICacheRepository';

export class CachedUserRepository implements IUserRepository {
  constructor(
    private baseRepository: IUserRepository,
    private cache: ICacheRepository,
    private cacheTTL: number = 3600 // 1 hour default
  ) {}

  async findById(id: string): Promise<User | null> {
    const cacheKey = `user:${id}`;

    // Try cache first
    const cached = await this.cache.get<User>(cacheKey);
    if (cached) {
      console.log(`Cache HIT for user:${id}`);
      return new User(
        cached.id,
        cached.email,
        cached.name,
        new Date(cached.createdAt)
      );
    }

    // Cache miss - get from base repository
    console.log(`Cache MISS for user:${id}`);
    const user = await this.baseRepository.findById(id);

    // Store in cache if found
    if (user) {
      await this.cache.set(cacheKey, {
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt.toISOString(),
      }, this.cacheTTL);
    }

    return user;
  }

  async findByEmail(email: string): Promise<User | null> {
    const cacheKey = `user:email:${email}`;

    // Try cache first
    const cached = await this.cache.get<User>(cacheKey);
    if (cached) {
      console.log(`Cache HIT for email:${email}`);
      return new User(
        cached.id,
        cached.email,
        cached.name,
        new Date(cached.createdAt)
      );
    }

    // Cache miss
    console.log(`Cache MISS for email:${email}`);
    const user = await this.baseRepository.findByEmail(email);

    if (user) {
      await this.cache.set(cacheKey, {
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt.toISOString(),
      }, this.cacheTTL);
    }

    return user;
  }

  async save(user: User): Promise<User> {
    // Save to base repository
    const savedUser = await this.baseRepository.save(user);

    // Invalidate cache (or update it)
    await this.cache.delete(`user:${savedUser.id}`);
    await this.cache.delete(`user:email:${savedUser.email}`);

    // Optionally, update cache with new value
    await this.cache.set(`user:${savedUser.id}`, {
      id: savedUser.id,
      email: savedUser.email,
      name: savedUser.name,
      createdAt: savedUser.createdAt.toISOString(),
    }, this.cacheTTL);

    return savedUser;
  }

  async delete(id: string): Promise<void> {
    // Delete from base repository
    await this.baseRepository.delete(id);

    // Invalidate cache
    await this.cache.delete(`user:${id}`);
  }
}
```

**Key Concepts:**
- **Cache-Aside Pattern**: Check cache first, then database
- **Cache Invalidation**: Delete cache when data changes
- **Decorator Pattern**: Wraps the base repository without modifying it

## Step 4: Update Use Case to Use Cached Repository

```typescript
// src/application/use-cases/GetUserUseCase.ts

import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/repositories/IUserRepository';

export class GetUserUseCase {
  constructor(private userRepository: IUserRepository) {}

  async execute(userId: string): Promise<User | null> {
    if (!userId) {
      throw new Error('User ID is required');
    }

    return await this.userRepository.findById(userId);
  }
}
```

The use case doesn't know about caching! It just uses the repository interface.

## Step 5: Update Routes with Caching

```typescript
// src/presentation/routes/userRoutes.ts

import { Router } from 'express';
import { UserController } from '../controllers/UserController';
import { CreateUserUseCase } from '../../application/use-cases/CreateUserUseCase';
import { GetUserUseCase } from '../../application/use-cases/GetUserUseCase';
import { InMemoryUserRepository } from '../../infrastructure/repositories/InMemoryUserRepository';
import { CachedUserRepository } from '../../infrastructure/repositories/CachedUserRepository';
import { RedisCacheRepository } from '../../infrastructure/cache/RedisCacheRepository';

const router = Router();

// Setup dependencies
const baseRepository = new InMemoryUserRepository();
const cache = new RedisCacheRepository();
const cachedRepository = new CachedUserRepository(baseRepository, cache);

const createUserUseCase = new CreateUserUseCase(cachedRepository);
const getUserUseCase = new GetUserUseCase(cachedRepository);
const userController = new UserController(createUserUseCase, getUserUseCase);

router.post('/users', (req, res) => userController.createUser(req, res));
router.get('/users/:id', (req, res) => userController.getUser(req, res));

export default router;
```

## Step 6: Update Controller

```typescript
// src/presentation/controllers/UserController.ts

import { Request, Response } from 'express';
import { CreateUserUseCase } from '../../application/use-cases/CreateUserUseCase';
import { GetUserUseCase } from '../../application/use-cases/GetUserUseCase';

export class UserController {
  constructor(
    private createUserUseCase: CreateUserUseCase,
    private getUserUseCase: GetUserUseCase
  ) {}

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
    } catch (error) {
      res.status(400).json({
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }

  async getUser(req: Request, res: Response): Promise<void> {
    try {
      const user = await this.getUserUseCase.execute(req.params.id);

      if (!user) {
        res.status(404).json({ error: 'User not found' });
        return;
      }

      res.json({
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt,
      });
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  }
}
```

## Testing Distributed Caching

```bash
# Start Redis
docker-compose up -d redis

# Start the server
npm run dev

# First request (cache miss - slower)
curl http://localhost:3000/api/users/123

# Second request (cache hit - faster!)
curl http://localhost:3000/api/users/123
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

## Next Steps

- [Message Queue with RabbitMQ](./03-message-queue.md)
