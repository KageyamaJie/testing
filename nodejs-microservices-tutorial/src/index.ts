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
