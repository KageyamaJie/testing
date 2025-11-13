from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.presentation.api.user_router import router as user_router
from app.infrastructure.messaging.setup_consumers import setup_consumers
from app.presentation.dependencies import init_message_publisher
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Background task for consumers
consumer_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global consumer_task
    
    # Startup
    print("🚀 Starting microservices application...")
    print("📨 Setting up message consumers...")
    
    # Initialize message publisher
    await init_message_publisher()
    
    # Start consumer in background
    consumer_task = asyncio.create_task(setup_consumers())
    
    yield
    
    # Shutdown
    print("Shutting down...")
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="Microservices Tutorial",
    description="FastAPI microservices with Clean Architecture, Redis Cache, and RabbitMQ",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(user_router, prefix="/api")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to FastAPI Microservices Tutorial",
        "docs": "/docs",
        "health": "/health"
    }
