# Microservices Architecture Tutorials

This repository contains comprehensive tutorials for building microservices using two different technology stacks, both following Clean Architecture principles.

## 📚 Tutorials

### 1. [Node.js + TypeScript + Express.js Tutorial](./nodejs-microservices-tutorial.md)
A complete guide to building microservices with:
- **Node.js** runtime
- **TypeScript** for type safety
- **Express.js** web framework
- **Clean Architecture** implementation
- **Redis** for distributed caching (similar to FusionCache)
- **RabbitMQ** for message queuing (similar to MassTransit)

### 2. [Python + FastAPI Tutorial](./python-microservices-tutorial.md)
A complete guide to building microservices with:
- **Python** programming language
- **FastAPI** modern web framework
- **Clean Architecture** implementation
- **Redis** for distributed caching (similar to FusionCache)
- **RabbitMQ** for message queuing (similar to MassTransit)

## 🎯 What You'll Learn

Both tutorials cover:

### Clean Architecture
- **Domain Layer**: Business entities and logic (framework-independent)
- **Application Layer**: Use cases and application services
- **Infrastructure Layer**: External concerns (databases, caches, message queues)
- **Presentation Layer**: Controllers and API routes

### Distributed Caching
- Redis integration for high-performance caching
- Cache-aside pattern implementation
- TTL (Time To Live) management
- Cache invalidation strategies
- Similar capabilities to .NET's FusionCache

### Message Queue Architecture
- RabbitMQ pub/sub pattern
- Event-driven architecture
- Domain events
- Message handlers/consumers
- Similar capabilities to .NET's MassTransit

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────┐
│   Presentation Layer                │
│   (Controllers, Routes, DTOs)      │
├─────────────────────────────────────┤
│   Application Layer                 │
│   (Use Cases, Event Handlers)      │
├─────────────────────────────────────┤
│   Domain Layer                      │
│   (Entities, Repository Interfaces) │
├─────────────────────────────────────┤
│   Infrastructure Layer              │
│   (Repositories, Cache, MessageBus) │
└─────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ (for Node.js tutorial)
- Python 3.10+ (for Python tutorial)
- Docker and Docker Compose
- Basic knowledge of the respective language and framework

### Infrastructure Setup

Both tutorials use Docker Compose for infrastructure:

```bash
# Start Redis and RabbitMQ
docker-compose up -d
```

This starts:
- **Redis** on port 6379 (for caching)
- **RabbitMQ** on port 5672 (for messaging)
- **RabbitMQ Management UI** on port 15672

## 📖 Tutorial Structure

Each tutorial includes:

1. **Introduction**: Overview and prerequisites
2. **Project Setup**: Initial configuration and dependencies
3. **Clean Architecture Implementation**: Step-by-step layer construction
4. **Distributed Caching**: Redis integration with examples
5. **Message Queue**: RabbitMQ integration with pub/sub pattern
6. **Complete Example**: Full working User Service
7. **Key Concepts**: Explanations of architectural decisions

## 🎓 Learning Path

### For Beginners
1. Start with the tutorial matching your preferred language
2. Follow along with code examples
3. Understand each layer before moving to the next
4. Run the complete example to see it in action

### For Experienced Developers
1. Review the architecture patterns
2. Compare implementations between Node.js and Python
3. Adapt patterns to your specific needs
4. Extend with additional features (database, auth, etc.)

## 🔑 Key Features

### Clean Architecture Benefits
- ✅ **Testability**: Each layer can be tested independently
- ✅ **Maintainability**: Changes don't cascade across layers
- ✅ **Flexibility**: Easy to swap implementations
- ✅ **Framework Independence**: Business logic doesn't depend on frameworks

### Distributed Caching Benefits
- ✅ **Performance**: Reduces database load significantly
- ✅ **Scalability**: Multiple service instances share cache
- ✅ **Availability**: Cache survives service restarts

### Message Queue Benefits
- ✅ **Decoupling**: Services communicate via events
- ✅ **Reliability**: Messages are persisted
- ✅ **Scalability**: Handle high message volumes
- ✅ **Event-Driven**: React to domain events asynchronously

## 🔄 Comparison with .NET Ecosystem

| Feature | .NET | Node.js/Express | Python/FastAPI |
|---------|------|-----------------|----------------|
| **Distributed Cache** | FusionCache | Redis + Custom Wrapper | Redis + Custom Wrapper |
| **Message Queue** | MassTransit | RabbitMQ + Custom Wrapper | RabbitMQ + Custom Wrapper |
| **Architecture** | Clean Architecture | Clean Architecture | Clean Architecture |
| **Type Safety** | C# | TypeScript | Python + Pydantic |

Both implementations provide similar capabilities to the .NET ecosystem:
- **FusionCache-like** functionality with Redis
- **MassTransit-like** messaging patterns with RabbitMQ
- **Clean Architecture** principles throughout

## 📝 Code Examples

Both tutorials include:
- ✅ Complete, runnable code examples
- ✅ Clear explanations for each component
- ✅ Beginner-friendly comments
- ✅ Best practices and patterns
- ✅ Error handling examples

## 🛠️ Next Steps

After completing a tutorial, consider:

1. **Database Integration**: Add PostgreSQL or MongoDB
2. **Authentication**: Implement JWT-based auth
3. **API Validation**: Add request validation
4. **Logging**: Integrate structured logging
5. **Monitoring**: Add Prometheus and Grafana
6. **Testing**: Write unit and integration tests
7. **Containerization**: Dockerize your services
8. **CI/CD**: Set up deployment pipelines

## 📚 Additional Resources

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Redis Documentation](https://redis.io/docs/)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)

## 🤝 Contributing

Feel free to:
- Report issues
- Suggest improvements
- Add more examples
- Extend the tutorials

## 📄 License

These tutorials are provided as educational resources. Feel free to use and adapt the code for your projects.

---

**Happy Learning! 🚀**
