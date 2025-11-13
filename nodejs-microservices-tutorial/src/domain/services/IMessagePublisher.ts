export interface IMessagePublisher {
  publish(exchange: string, routingKey: string, message: any): Promise<void>;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
}
