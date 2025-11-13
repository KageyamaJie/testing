# Complete Microservices Example

This guide shows how all pieces work together: Clean Architecture, Distributed Caching, and Message Queue.

## Complete Project Structure

```
nodejs-microservices-tutorial/
├── src/
│   ├── domain/
│   │   ├── entities/
│   │   │   └── User.ts
│   │   ├── repositories/
│   │   │   ├── IUserRepository.ts
│   │   │   └── ICacheRepository.ts
│   │   └── services/
│   │       ├── IMessagePublisher.ts
│   │       └── IMessageConsumer.ts
│   ├── application/
│   │   ├── use-cases/
│   │   │   ├── CreateUserUseCase.ts
│   │   │   └── GetUserUseCase.ts
│   │   ├── services/
│   │   │   └── UserEventHandler.ts
│   │   └── dto/
│   │       └── CreateUserDTO.ts
│   ├── infrastructure/
│   │   ├── cache/
│   │   │   └── RedisCacheRepository.ts
│   │   ├── messaging/
│   │   │   ├── RabbitMQPublisher.ts
│   │   │   ├── RabbitMQConsumer.ts
│   │   │   └── setupConsumers.ts
│   │   └── repositories/
│   │       ├── InMemoryUserRepository.ts
│   │       └── CachedUserRepository.ts
│   ├── presentation/
│   │   ├── controllers/
│   │   │   └── UserController.ts
│   │   ├── routes/
│   │   │   └── userRoutes.ts
│   │   └── middleware/
│   │       └── errorHandler.ts
│   └── index.ts
├── docker-compose.yml
├── package.json
└── tsconfig.json
```

## Complete Implementation Files

### 1. Domain Entity

```typescript
// src/domain/entities/User.ts
export class User {
  constructor(
    public readonly id: string,
    public readonly email: string,
    public readonly name: string,
    public readonly createdAt: Date
  ) {}

  isActive(): boolean {
    return this.email.includes('@');
  }
}
```

### 2. Repository Interfaces

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

```typescript
// src/domain/repositories/ICacheRepository.ts
export interface ICacheRepository {
  get<T>(key: string): Promise<T | null>;
  set(key: string, value: any, ttlSeconds?: number): Promise<void>;
  delete(key: string): Promise<void>;
}
```

### 3. Message Service Interfaces

```typescript
// src/domain/services/IMessagePublisher.ts
export interface IMessagePublisher {
  publish(exchange: string, routingKey: string, message: any): Promise<void>;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
}
```

### 4. Infrastructure Implementations

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
    return Array.from(this.users.values()).find(u => u.email === email) || null;
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

### 5. Complete Main Application

```typescript
// src/index.ts
import express from 'express';
import dotenv from 'dotenv';
import userRoutes from './presentation/routes/userRoutes';
import { setupConsumers } from './infrastructure/messaging/setupConsumers';

dotenv.config();

const app = express();
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.use('/api', userRoutes);

const PORT = process.env.PORT || 3000;

async function start() {
  try {
    console.log('🚀 Starting microservices application...');
    
    // Setup message consumers
    console.log('📨 Setting up message consumers...');
    await setupConsumers();

    // Start HTTP server
    app.listen(PORT, () => {
      console.log(`✅ Server running on port ${PORT}`);
      console.log(`📚 API Documentation: http://localhost:${PORT}/api`);
      console.log(`🏥 Health Check: http://localhost:${PORT}/health`);
    });
  } catch (error) {
    console.error('❌ Failed to start application:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully...');
  process.exit(0);
});

start();
```

## Running the Complete Example

### Step 1: Install Dependencies

```bash
cd nodejs-microservices-tutorial
npm install
```

### Step 2: Start Infrastructure

```bash
docker-compose up -d
```

This starts:
- Redis on port 6379
- RabbitMQ on port 5672 (Management UI on 15672)

### Step 3: Start Application

```bash
npm run dev
```

### Step 4: Test the API

```bash
# Create a user (triggers cache write and message publish)
curl -X POST http://localhost:3000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "name": "John Doe"
  }'

# Get user (first time - cache miss, second time - cache hit)
curl http://localhost:3000/api/users/{USER_ID}

# Check RabbitMQ Management UI
open http://localhost:15672
# Login: admin / admin123
```

## Flow Diagram

```
1. HTTP Request → Controller
   ↓
2. Controller → Use Case
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

## Production Considerations

1. **Error Handling**: Add retry logic and dead letter queues
2. **Monitoring**: Add logging and metrics (Prometheus, Grafana)
3. **Security**: Add authentication and authorization
4. **Database**: Replace in-memory repository with real database
5. **Connection Pooling**: Use connection managers for Redis and RabbitMQ
6. **Configuration**: Use environment variables and config files
7. **Testing**: Add unit and integration tests

## Next Steps

- Add more microservices (Notification Service, Email Service)
- Implement API Gateway
- Add service discovery
- Implement distributed tracing
- Add monitoring and alerting
