export interface IMessageConsumer {
  consume(
    queue: string,
    handler: (message: any) => Promise<void>
  ): Promise<void>;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
}
