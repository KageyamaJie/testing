from abc import ABC, abstractmethod
from typing import Any

class IMessagePublisher(ABC):
    @abstractmethod
    async def publish(
        self,
        exchange: str,
        routing_key: str,
        message: Any
    ) -> None:
        """Publish message to exchange"""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Connect to message broker"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from message broker"""
        pass
