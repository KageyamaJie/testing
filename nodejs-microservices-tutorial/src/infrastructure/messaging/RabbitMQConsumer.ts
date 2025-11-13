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
