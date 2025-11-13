# FastAPI Microservices Tutorial

## Overview

This tutorial guides you through building microservices using **Python** and **FastAPI** with a focus on:
- **Clean Architecture** - Separation of concerns and maintainable code structure
- **Distributed Caching** - Using Redis for high-performance caching (similar to FusionCache in .NET)
- **Message Queue** - Using RabbitMQ for asynchronous communication (similar to MassTransit in .NET)

## Prerequisites

- Python 3.10+ installed
- pip (Python package manager)
- Docker and Docker Compose (for Redis and RabbitMQ)
- Basic understanding of Python and REST APIs

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User API  │────▶│   Redis     │     │  RabbitMQ   │
│   (FastAPI) │     │  (Cache)    │     │  (Message   │
└─────────────┘     └─────────────┘     │   Queue)    │
                                        └─────────────┘
```

## Project Structure

```
fastapi-microservices-tutorial/
├── app/
│   ├── domain/           # Business logic (Clean Architecture)
│   │   ├── entities/     # Domain entities
│   │   ├── repositories/ # Repository interfaces
│   │   └── services/     # Domain services
│   ├── application/      # Application layer
│   │   ├── use_cases/    # Use case implementations
│   │   └── dto/          # Data Transfer Objects
│   ├── infrastructure/   # External concerns
│   │   ├── cache/        # Redis cache implementation
│   │   ├── messaging/    # RabbitMQ implementation
│   │   └── database/     # Database implementations
│   └── presentation/     # API layer
│       ├── api/          # FastAPI routers
│       └── dependencies/ # Dependency injection
├── docker-compose.yml    # Redis & RabbitMQ setup
├── requirements.txt
└── main.py
```

## Getting Started

1. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Infrastructure Services**
   ```bash
   docker-compose up -d
   ```

4. **Run the Application**
   ```bash
   uvicorn main:app --reload
   ```

## Tutorial Sections

1. [Clean Architecture Setup](./docs/01-clean-architecture.md)
2. [Distributed Caching with Redis](./docs/02-distributed-caching.md)
3. [Message Queue with RabbitMQ](./docs/03-message-queue.md)
4. [Complete Example](./docs/04-complete-example.md)
