export class UserEventHandler {
  async handleUserCreated(event: any): Promise<void> {
    console.log('📧 Sending welcome email to:', event.email);
    console.log('📱 Sending SMS notification to:', event.email);
    // In a real app, you'd call email/SMS services here
  }
}
