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
