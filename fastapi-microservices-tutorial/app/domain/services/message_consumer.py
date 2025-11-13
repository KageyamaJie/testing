from abc import ABC, abstractmethod
from typing import Callable, Any

class IMessageConsumer(ABC):
    @abstractmethod
    async def consume(
        self,
        queue: str,
        handler: Callable[[Any], None]
    ) -> None:
        """Consume messages from queue"""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Connect to message broker"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from message broker"""
        pass
