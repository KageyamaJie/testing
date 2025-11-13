class UserEventHandler:
    async def handle_user_created(self, event: dict) -> None:
        """Handle user created event"""
        print(f"📧 Sending welcome email to: {event['email']}")
        print(f"📱 Sending SMS notification to: {event['email']}")
        # In a real app, you'd call email/SMS services here
