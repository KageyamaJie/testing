# Microservices Architecture Tutorials

This repository contains two comprehensive tutorials for building microservices architectures:

1. **Node.js + TypeScript + Express.js** - [`nodejs-express-microservices-tutorial.md`](./nodejs-express-microservices-tutorial.md)
2. **Python + FastAPI** - [`python-fastapi-microservices-tutorial.md`](./python-fastapi-microservices-tutorial.md)

## What You'll Learn

Both tutorials cover:

### 🏗️ Clean Architecture
- Layer separation (Domain, Application, Infrastructure, Presentation)
- Dependency inversion principle
- Testable and maintainable code structure

### 💾 Distributed Caching
- Redis implementation (similar to FusionCache in .NET)
- Cache-aside pattern
- TTL (Time To Live) management
- Cross-instance caching

### 📨 Message Queue
- RabbitMQ implementation (similar to MassTransit in .NET)
- Publish/Subscribe pattern
- Event-driven architecture
- Asynchronous processing

## Tutorial Features

✅ **Beginner-friendly**: Clear explanations and step-by-step instructions  
✅ **Code examples**: Complete, working code with comments  
✅ **Best practices**: Industry-standard patterns and conventions  
✅ **Real-world**: Practical examples you can use in production  

## Quick Start

### Node.js Tutorial
```bash
# Navigate to the tutorial
cat nodejs-express-microservices-tutorial.md

# Follow the setup instructions in the tutorial
```

### Python Tutorial
```bash
# Navigate to the tutorial
cat python-fastapi-microservices-tutorial.md

# Follow the setup instructions in the tutorial
```

## Prerequisites

- Docker installed (for Redis and RabbitMQ)
- Node.js 18+ (for Node.js tutorial)
- Python 3.10+ (for Python tutorial)

## Architecture Comparison

Both tutorials implement the same architecture patterns, making it easy to:

- Compare implementations across languages
- Understand concepts regardless of your preferred stack
- Port code between Node.js and Python if needed

## Key Concepts Explained

### Clean Architecture Layers

```
Presentation Layer  → HTTP requests/responses, routing
Application Layer   → Use cases, business workflows
Domain Layer        → Entities, business rules, interfaces
Infrastructure      → Database, cache, messaging implementations
```

### Distributed Caching Flow

```
Request → Check Cache → Cache Hit? → Return cached data
                    ↓ Cache Miss
                    → Fetch from Repository → Store in Cache → Return data
```

### Message Queue Flow

```
Event Occurs → Publish to Exchange → Queue → Consumer → Process Event
```

## Next Steps

1. Read through your preferred tutorial
2. Set up the project structure
3. Implement each layer step by step
4. Test the complete microservice
5. Explore the best practices section

## Additional Resources

- [Redis Documentation](https://redis.io/docs/)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

Happy coding! 🚀
