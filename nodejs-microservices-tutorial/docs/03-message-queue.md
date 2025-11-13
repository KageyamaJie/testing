# Message Queue with RabbitMQ

## What is a Message Queue?

A message queue allows services to communicate **asynchronously** by sending messages. This is similar to **MassTransit** in .NET, providing:
- **Decoupling** - Services don't need to know about each other
- **Reliability** - Messages are persisted until processed
- **Scalability** - Multiple workers can process messages

## Why RabbitMQ?

RabbitMQ is a robust message broker that:
- Supports multiple messaging patterns (pub/sub, work queues, routing)
- Guarantees message delivery
- Has excellent management UI
- Is widely used in production

## Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   User API  │────────▶│  RabbitMQ   │────────▶│ Notification│
│  (Publisher)│         │  (Exchange) │         │   Service   │
└─────────────┘         └─────────────┘         └─────────────┘
```

## Step 1: Create Messaging Interface (Domain Layer)

```typescript
// src/domain/services/IMessagePublisher.ts

export interface IMessagePublisher {
  publish(exchange: string, routingKey: string, message: any): Promise<void>;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
}
```

```typescript
// src/domain/services/IMessageConsumer.ts

export interface IMessageConsumer {
  consume(
    queue: string,
    handler: (message: any) => Promise<void>
  ): Promise<void>;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
}
```

**Why interfaces?** Domain layer defines contracts. Infrastructure implements them.

## Step 2: RabbitMQ Publisher Implementation

```typescript
// src/infrastructure/messaging/RabbitMQPublisher.ts

import * as amqp from 'amqplib';
import { IMessagePublisher } from '../../domain/services/IMessagePublisher';

export class RabbitMQPublisher implements IMessagePublisher {
  private connection: amqp.Connection | null = null;
  private channel: amqp.Channel | null = null;

  async connect(): Promise<void> {
    try {
      const url = process.env.RABBITMQ_URL || 'amqp://admin:admin123@localhost:5672';
      this.connection = await amqp.connect(url);
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

  async publish(
    exchange: string,
    routingKey: string,
    message: any
  ): Promise<void> {
    if (!this.channel) {
      throw new Error('Not connected to RabbitMQ');
    }

    try {
      // Assert exchange exists (create if it doesn't)
      await this.channel.assertExchange(exchange, 'topic', {
        durable: true, // Survive broker restarts
      });

      // Publish message
      const messageBuffer = Buffer.from(JSON.stringify(message));
      const published = this.channel.publish(
        exchange,
        routingKey,
        messageBuffer,
        {
          persistent: true, // Message survives broker restarts
        }
      );

      if (!published) {
        throw new Error('Failed to publish message - channel buffer full');
      }

      console.log(`Published message to ${exchange} with key ${routingKey}`);
    } catch (error) {
      console.error('Error publishing message:', error);
      throw error;
    }
  }

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

**Explanation:**
- **Exchange**: Routes messages to queues (like a post office)
- **Routing Key**: Determines which queue receives the message
- **Topic Exchange**: Flexible routing based on patterns
- **Persistent**: Messages survive broker restarts

## Step 3: RabbitMQ Consumer Implementation

```typescript
// src/infrastructure/messaging/RabbitMQConsumer.ts

import * as amqp from 'amqplib';
import { IMessageConsumer } from '../../domain/services/IMessageConsumer';

export class RabbitMQConsumer implements IMessageConsumer {
  private connection: amqp.Connection | null = null;
  private channel: amqp.Channel | null = null;

  async connect(): Promise<void> {
    try {
      const url = process.env.RABBITMQ_URL || 'amqp://admin:admin123@localhost:5672';
      this.connection = await amqp.connect(url);
      this.channel = await this.connection.createChannel();

      this.connection.on('error', (err) => {
        console.error('RabbitMQ Connection Error:', err);
      });

      console.log('Connected to RabbitMQ (Consumer)');
    } catch (error) {
      console.error('Failed to connect to RabbitMQ:', error);
      throw error;
    }
  }

  async consume(
    queue: string,
    handler: (message: any) => Promise<void>
  ): Promise<void> {
    if (!this.channel) {
      throw new Error('Not connected to RabbitMQ');
    }

    try {
      // Assert queue exists (create if it doesn't)
      await this.channel.assertQueue(queue, {
        durable: true, // Survive broker restarts
      });

      // Set prefetch to process one message at a time
      await this.channel.prefetch(1);

      console.log(`Waiting for messages in queue: ${queue}`);

      await this.channel.consume(
        queue,
        async (msg) => {
          if (!msg) {
            return;
          }

          try {
            // Parse message
            const content = JSON.parse(msg.content.toString());
            console.log(`Received message:`, content);

            // Process message
            await handler(content);

            // Acknowledge message (remove from queue)
            this.channel!.ack(msg);
            console.log('Message processed successfully');
          } catch (error) {
            console.error('Error processing message:', error);
            // Reject message and requeue it
            this.channel!.nack(msg, false, true);
          }
        },
        {
          noAck: false, // Manual acknowledgment
        }
      );
    } catch (error) {
      console.error('Error setting up consumer:', error);
      throw error;
    }
  }

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

**Key Concepts:**
- **Queue**: Stores messages until consumed
- **Acknowledgment**: Message is removed only after successful processing
- **Prefetch**: Limits unacknowledged messages (prevents overload)
- **Requeue**: Failed messages can be retried

## Step 4: Update Use Case to Publish Events

```typescript
// src/application/use-cases/CreateUserUseCase.ts

import { User } from '../../domain/entities/User';
import { IUserRepository } from '../../domain/repositories/IUserRepository';
import { IMessagePublisher } from '../../domain/services/IMessagePublisher';
import { CreateUserDTO } from '../dto/CreateUserDTO';

export class CreateUserUseCase {
  constructor(
    private userRepository: IUserRepository,
    private messagePublisher?: IMessagePublisher
  ) {}

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
    const savedUser = await this.userRepository.save(user);

    // Publish event (if publisher is available)
    if (this.messagePublisher) {
      await this.messagePublisher.publish(
        process.env.RABBITMQ_EXCHANGE || 'user_events',
        'user.created',
        {
          userId: savedUser.id,
          email: savedUser.email,
          name: savedUser.name,
          timestamp: new Date().toISOString(),
        }
      );
    }

    return savedUser;
  }

  private generateId(): string {
    return require('uuid').v4();
  }
}
```

**Explanation:**
- After creating a user, we publish an event
- Other services can listen to this event
- The use case doesn't know about RabbitMQ - it uses the interface

## Step 5: Create Event Handler Service

```typescript
// src/application/services/UserEventHandler.ts

export class UserEventHandler {
  async handleUserCreated(event: any): Promise<void> {
    console.log('📧 Sending welcome email to:', event.email);
    console.log('📱 Sending SMS notification to:', event.email);
    // In a real app, you'd call email/SMS services here
  }
}
```

## Step 6: Setup Consumer in Application

```typescript
// src/infrastructure/messaging/setupConsumers.ts

import { RabbitMQConsumer } from './RabbitMQConsumer';
import { UserEventHandler } from '../../application/services/UserEventHandler';

export async function setupConsumers(): Promise<void> {
  const consumer = new RabbitMQConsumer();
  await consumer.connect();

  const eventHandler = new UserEventHandler();

  // Consume user.created events
  await consumer.consume(
    process.env.RABBITMQ_QUEUE || 'user_notifications',
    async (message) => {
      if (message.routingKey === 'user.created') {
        await eventHandler.handleUserCreated(message);
      }
    }
  );

  console.log('Consumers setup complete');
}
```

## Step 7: Update Main Application

```typescript
// src/index.ts

import express from 'express';
import userRoutes from './presentation/routes/userRoutes';
import { setupConsumers } from './infrastructure/messaging/setupConsumers';

const app = express();
app.use(express.json());

app.use('/api', userRoutes);

const PORT = process.env.PORT || 3000;

async function start() {
  try {
    // Setup message consumers
    await setupConsumers();

    // Start HTTP server
    app.listen(PORT, () => {
      console.log(`Server running on port ${PORT}`);
    });
  } catch (error) {
    console.error('Failed to start application:', error);
    process.exit(1);
  }
}

start();
```

## Step 8: Update Routes with Message Publisher

```typescript
// src/presentation/routes/userRoutes.ts

import { Router } from 'express';
import { UserController } from '../controllers/UserController';
import { CreateUserUseCase } from '../../application/use-cases/CreateUserUseCase';
import { GetUserUseCase } from '../../application/use-cases/GetUserUseCase';
import { InMemoryUserRepository } from '../../infrastructure/repositories/InMemoryUserRepository';
import { CachedUserRepository } from '../../infrastructure/repositories/CachedUserRepository';
import { RedisCacheRepository } from '../../infrastructure/cache/RedisCacheRepository';
import { RabbitMQPublisher } from '../../infrastructure/messaging/RabbitMQPublisher';

const router = Router();

// Setup dependencies
const baseRepository = new InMemoryUserRepository();
const cache = new RedisCacheRepository();
const cachedRepository = new CachedUserRepository(baseRepository, cache);

const messagePublisher = new RabbitMQPublisher();
messagePublisher.connect().catch(console.error);

const createUserUseCase = new CreateUserUseCase(
  cachedRepository,
  messagePublisher
);
const getUserUseCase = new GetUserUseCase(cachedRepository);
const userController = new UserController(createUserUseCase, getUserUseCase);

router.post('/users', (req, res) => userController.createUser(req, res));
router.get('/users/:id', (req, res) => userController.getUser(req, res));

export default router;
```

## Testing Message Queue

```bash
# Start RabbitMQ
docker-compose up -d rabbitmq

# Start the server
npm run dev

# Create a user (this will publish a message)
curl -X POST http://localhost:3000/api/users \
  -H "Content-Type: application/json" \
  -d '{"email":"jane@example.com","name":"Jane Doe"}'

# Check RabbitMQ Management UI
# Open http://localhost:15672 (admin/admin123)
# You'll see messages in the queue!
```

## Message Queue Patterns

1. **Publish-Subscribe**: One message to many consumers
2. **Work Queue**: Distribute work among multiple workers
3. **Routing**: Route messages based on routing keys
4. **Topics**: Pattern-based routing (what we're using)

## Benefits

- **Decoupling**: Services don't need to know about each other
- **Reliability**: Messages are persisted until processed
- **Scalability**: Add more workers to process messages faster
- **Resilience**: Failed messages can be retried

## Advanced: Connection Manager (Production Ready)

For production, use `amqp-connection-manager` for automatic reconnection:

```typescript
// src/infrastructure/messaging/RabbitMQPublisher.ts (Improved)

import * as amqp from 'amqp-connection-manager';
import { IMessagePublisher } from '../../domain/services/IMessagePublisher';

export class RabbitMQPublisher implements IMessagePublisher {
  private connection: amqp.AmqpConnectionManager | null = null;
  private channelWrapper: amqp.ChannelWrapper | null = null;

  async connect(): Promise<void> {
    const url = process.env.RABBITMQ_URL || 'amqp://admin:admin123@localhost:5672';
    
    this.connection = amqp.connect([url]);
    
    this.channelWrapper = this.connection.createChannel({
      setup: async (channel: amqp.ConfirmChannel) => {
        // Setup exchange when channel is created
        await channel.assertExchange('user_events', 'topic', {
          durable: true,
        });
      },
    });

    this.connection.on('connect', () => {
      console.log('Connected to RabbitMQ');
    });

    this.connection.on('disconnect', (err) => {
      console.log('Disconnected from RabbitMQ:', err);
    });
  }

  async publish(
    exchange: string,
    routingKey: string,
    message: any
  ): Promise<void> {
    if (!this.channelWrapper) {
      throw new Error('Not connected to RabbitMQ');
    }

    const messageBuffer = Buffer.from(JSON.stringify(message));
    
    await this.channelWrapper.publish(exchange, routingKey, messageBuffer, {
      persistent: true,
    });

    console.log(`Published message to ${exchange} with key ${routingKey}`);
  }

  async disconnect(): Promise<void> {
    if (this.channelWrapper) {
      await this.channelWrapper.close();
    }
    if (this.connection) {
      await this.connection.close();
    }
  }
}
```

## Next Steps

- [Complete Example](./04-complete-example.md)
