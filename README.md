# Microservices Architecture Tutorials

Welcome! This repository contains **two comprehensive tutorials** for building microservices with Clean Architecture, Distributed Caching, and Message Queue patterns.

## 🎯 Tutorials Overview

### 1. Node.js + TypeScript + Express.js Tutorial
**Location:** [`nodejs-microservices-tutorial/`](./nodejs-microservices-tutorial/)

Learn to build microservices using:
- **Node.js** with **TypeScript**
- **Express.js** framework
- **Redis** for distributed caching (similar to FusionCache in .NET)
- **RabbitMQ** for message queuing (similar to MassTransit in .NET)
- **Clean Architecture** principles

[👉 Get Started with Node.js Tutorial](./nodejs-microservices-tutorial/README.md)

### 2. Python + FastAPI Tutorial
**Location:** [`fastapi-microservices-tutorial/`](./fastapi-microservices-tutorial/)

Learn to build microservices using:
- **Python 3.10+**
- **FastAPI** framework
- **Redis** for distributed caching (similar to FusionCache in .NET)
- **RabbitMQ** for message queuing (similar to MassTransit in .NET)
- **Clean Architecture** principles

[👉 Get Started with FastAPI Tutorial](./fastapi-microservices-tutorial/README.md)

## 📚 What You'll Learn

Both tutorials cover the same concepts but with different technology stacks:

### ✅ Clean Architecture
- **Domain Layer**: Business entities and rules (framework-independent)
- **Application Layer**: Use cases and business logic orchestration
- **Infrastructure Layer**: External concerns (database, cache, messaging)
- **Presentation Layer**: API endpoints and HTTP handling

### ✅ Distributed Caching with Redis
- Cache-aside pattern
- Cache invalidation strategies
- TTL (Time To Live) management
- Error handling and resilience
- Performance optimization

### ✅ Message Queue with RabbitMQ
- Publish-Subscribe pattern
- Topic-based routing
- Message persistence and reliability
- Consumer patterns
- Error handling and retry logic

## 🏗️ Architecture Comparison

### .NET Ecosystem → JavaScript/TypeScript Ecosystem
| .NET | Node.js/TypeScript |
|------|-------------------|
| FusionCache | Redis + Custom Cache Repository |
| MassTransit | RabbitMQ + amqplib/aio-pika |
| Clean Architecture | Same principles, TypeScript interfaces |

### .NET Ecosystem → Python Ecosystem
| .NET | Python/FastAPI |
|------|----------------|
| FusionCache | Redis + Custom Cache Repository |
| MassTransit | RabbitMQ + aio-pika |
| Clean Architecture | Same principles, ABC interfaces |

## 🚀 Quick Start

### Prerequisites
- **Docker** and **Docker Compose** (for Redis and RabbitMQ)
- Choose your path:
  - **Node.js Tutorial**: Node.js 18+, npm/yarn
  - **FastAPI Tutorial**: Python 3.10+, pip

### Infrastructure Setup (Same for Both)

```bash
# Start Redis and RabbitMQ
docker-compose up -d

# Verify services are running
docker ps
```

**Services:**
- Redis: `localhost:6379`
- RabbitMQ: `localhost:5672` (AMQP)
- RabbitMQ Management UI: `http://localhost:15672` (admin/admin123)

## 📖 Tutorial Structure

Each tutorial follows the same structure:

1. **[Clean Architecture](./nodejs-microservices-tutorial/docs/01-clean-architecture.md)** - Learn to structure your code in layers
2. **[Distributed Caching](./nodejs-microservices-tutorial/docs/02-distributed-caching.md)** - Implement Redis caching
3. **[Message Queue](./nodejs-microservices-tutorial/docs/03-message-queue.md)** - Set up RabbitMQ messaging
4. **[Complete Example](./nodejs-microservices-tutorial/docs/04-complete-example.md)** - Put it all together

## 🎓 Learning Path

### For Beginners
1. Start with **Clean Architecture** - understand the foundation
2. Add **Distributed Caching** - improve performance
3. Implement **Message Queue** - enable async communication
4. Review **Complete Example** - see everything working together

### For Experienced Developers
- Jump to specific sections you need
- Compare implementations between Node.js and Python
- Use as reference for your own projects

## 🔍 Key Concepts Explained

### Clean Architecture Benefits
- **Testability**: Test business logic without HTTP or database
- **Maintainability**: Changes isolated to specific layers
- **Flexibility**: Swap implementations without changing business logic
- **Independence**: Business logic doesn't depend on frameworks

### Distributed Caching Benefits
- **Performance**: Sub-millisecond access vs. database queries
- **Scalability**: Shared cache across multiple servers
- **Reduced Load**: Fewer database queries
- **Resilience**: App continues working if cache fails

### Message Queue Benefits
- **Decoupling**: Services don't need to know about each other
- **Reliability**: Messages persisted until processed
- **Scalability**: Add more workers to process messages faster
- **Resilience**: Failed messages can be retried

## 🛠️ Technology Stack Comparison

| Feature | Node.js/TypeScript | Python/FastAPI |
|---------|-------------------|----------------|
| **Language** | TypeScript (typed JavaScript) | Python 3.10+ |
| **Framework** | Express.js | FastAPI |
| **Cache Client** | ioredis | redis / redis.asyncio |
| **MQ Client** | amqplib / amqp-connection-manager | aio-pika |
| **Type Safety** | TypeScript types | Python type hints + Pydantic |
| **Async Model** | Promises/async-await | async/await |
| **API Docs** | Manual (Swagger) | Automatic (OpenAPI/Swagger) |
| **Validation** | Manual or class-validator | Pydantic (automatic) |

## 📝 Code Examples

Both tutorials include:
- ✅ Complete, runnable code examples
- ✅ Clear explanations for each concept
- ✅ Step-by-step implementation guides
- ✅ Best practices and patterns
- ✅ Error handling examples
- ✅ Production considerations

## 🎯 Use Cases

These tutorials are perfect for:
- **Learning microservices architecture**
- **Understanding Clean Architecture**
- **Implementing distributed caching**
- **Setting up message queues**
- **Building scalable backend systems**
- **Comparing Node.js vs Python approaches**

## 🔗 Additional Resources

- [Redis Documentation](https://redis.io/docs/)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Express.js Documentation](https://expressjs.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🤝 Contributing

Feel free to:
- Report issues
- Suggest improvements
- Add more examples
- Improve documentation

## 📄 License

MIT License - feel free to use these tutorials for learning and projects!

---

**Happy Learning! 🚀**

Choose your path and start building microservices with Clean Architecture!
