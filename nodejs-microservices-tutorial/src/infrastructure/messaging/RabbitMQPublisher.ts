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
