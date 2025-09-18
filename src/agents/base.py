"""Base agent class with Claude SDK integration"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseAgent(ABC):
    """Base class for all DAB agents"""
    
    def __init__(self, name: str):
        self.name = name
        self._client = None
    
    @property
    def client(self):
        """Lazy-loaded Claude SDK client"""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    @abstractmethod
    def _create_client(self):
        """Create Claude SDK client - implemented by subclasses"""
        pass
    
    @abstractmethod
    async def handle_request(self, request: str) -> str:
        """Handle incoming request - implemented by subclasses"""
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"