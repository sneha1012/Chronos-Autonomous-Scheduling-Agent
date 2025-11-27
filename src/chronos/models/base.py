"""Base model interface for LLM implementations."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ModelResponse:
    """Standard response format from LLM models."""
    
    content: str
    model: str
    tokens_used: int
    latency_ms: float
    finish_reason: str
    metadata: Dict[str, Any]
    timestamp: datetime
    
    @property
    def cost(self) -> float:
        """Calculate approximate cost based on tokens used."""
        # For Llama 3 (self-hosted), cost is minimal
        # For API-based models, calculate based on pricing
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "finish_reason": self.finish_reason,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "cost": self.cost,
        }


class BaseModel(ABC):
    """Abstract base class for LLM models."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the model.
        
        Args:
            config: Model configuration dictionary
        """
        self.config = config
        self.model_name = config.get("name", "unknown")
        self.is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize and load the model."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> ModelResponse:
        """
        Generate a response from the model.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters
            
        Returns:
            ModelResponse object
        """
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the model.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters
            
        Yields:
            Token strings as they are generated
        """
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> ModelResponse:
        """
        Generate a chat-based response.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters
            
        Returns:
            ModelResponse object
        """
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        Generate embeddings for text.
        
        Args:
            text: Input text
            
        Returns:
            List of embedding values
        """
        pass
    
    async def cleanup(self) -> None:
        """Cleanup model resources."""
        self.is_initialized = False
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        if self.is_initialized:
            # Sync cleanup
            pass

