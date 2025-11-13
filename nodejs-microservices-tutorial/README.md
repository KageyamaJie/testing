# Node.js + TypeScript Microservices Tutorial

## Overview

This tutorial guides you through building microservices using **Node.js**, **TypeScript**, and **Express.js** with a focus on:
- **Clean Architecture** - Separation of concerns and maintainable code structure
- **Distributed Caching** - Using Redis for high-performance caching (similar to FusionCache in .NET)
- **Message Queue** - Using RabbitMQ for asynchronous communication (similar to MassTransit in .NET)

## Prerequisites

- Node.js 18+ installed
- TypeScript knowledge (basic)
- Docker and Docker Compose (for Redis and RabbitMQ)
- Basic understanding of REST APIs

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User API  │────▶│   Redis     │     │  RabbitMQ   │
│  (Express)  │     │  (Cache)    │     │  (Message   │
└─────────────┘     └─────────────┘     │   Queue)    │
                                        └─────────────┘
```

## Project Structure

```
nodejs-microservices-tutorial/
├── src/
│   ├── domain/           # Business logic (Clean Architecture)
│   │   ├── entities/     # Domain entities
│   │   ├── repositories/ # Repository interfaces
│   │   └── services/     # Domain services
│   ├── application/      # Application layer
│   │   ├── use-cases/    # Use case implementations
│   │   └── dto/          # Data Transfer Objects
│   ├── infrastructure/   # External concerns
│   │   ├── cache/        # Redis cache implementation
│   │   ├── messaging/    # RabbitMQ implementation
│   │   └── database/     # Database implementations
│   └── presentation/     # API layer
│       ├── controllers/  # Express controllers
│       ├── routes/       # Route definitions
│       └── middleware/   # Express middleware
├── docker-compose.yml    # Redis & RabbitMQ setup
├── package.json
└── tsconfig.json
```

## Getting Started

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Start Infrastructure Services**
   ```bash
   docker-compose up -d
   ```

3. **Run the Application**
   ```bash
   npm run dev
   ```

## Tutorial Sections

1. [Clean Architecture Setup](./docs/01-clean-architecture.md)
2. [Distributed Caching with Redis](./docs/02-distributed-caching.md)
3. [Message Queue with RabbitMQ](./docs/03-message-queue.md)
4. [Complete Example](./docs/04-complete-example.md)
