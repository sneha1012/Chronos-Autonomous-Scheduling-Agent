"""Llama 3 model implementation with optimizations."""

import time
import torch
from typing import List, Dict, Any, Optional, AsyncIterator
from datetime import datetime
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TextIteratorStreamer,
)
from threading import Thread
import asyncio

from src.chronos.models.base import BaseModel, ModelResponse
from src.chronos.config import config
from src.chronos.utils.logger import get_logger

logger = get_logger(__name__)


class LlamaModel(BaseModel):
    """Llama 3 model with 4-bit quantization and optimizations."""
    
    def __init__(self, model_config: Optional[Dict[str, Any]] = None):
        """
        Initialize Llama 3 model.
        
        Args:
            model_config: Model configuration (defaults to global config)
        """
        if model_config is None:
            model_config = config.model.__dict__
        
        super().__init__(model_config)
        
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Initializing Llama 3 model: {self.model_name}")
        logger.info(f"Device: {self.device}")
    
    async def initialize(self) -> None:
        """Load and initialize the Llama 3 model."""
        if self.is_initialized:
            logger.warning("Model already initialized")
            return
        
        try:
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                token=config.hf_token,
                trust_remote_code=True,
            )
            
            # Set padding token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Configure quantization for efficient inference
            quantization_config = None
            if self.config.get("load_in_4bit", True):
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
                logger.info("Using 4-bit quantization")
            
            logger.info("Loading model (this may take a minute)...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.float16,
                token=config.hf_token,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )
            
            # Enable gradient checkpointing for memory efficiency
            if hasattr(self.model, "gradient_checkpointing_enable"):
                self.model.gradient_checkpointing_enable()
            
            self.is_initialized = True
            logger.info("Model loaded successfully!")
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise
    
    def _format_chat_prompt(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Format messages into Llama 3 chat format.
        
        Args:
            messages: List of message dictionaries
            system_prompt: Optional system prompt
            
        Returns:
            Formatted prompt string
        """
        formatted = ""
        
        # Add system prompt if provided
        if system_prompt:
            formatted += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|>"
        
        # Add conversation messages
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
        
        # Add assistant prompt
        formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        
        return formatted
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> ModelResponse:
        """
        Generate a response from Llama 3.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters
            
        Returns:
            ModelResponse object
        """
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Format prompt for chat
            messages = [{"role": "user", "content": prompt}]
            formatted_prompt = self._format_chat_prompt(messages, system_prompt)
            
            # Tokenize
            inputs = self.tokenizer(
                formatted_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048,
            ).to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=kwargs.get("top_p", 0.9),
                    top_k=kwargs.get("top_k", 50),
                    do_sample=temperature > 0,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            
            # Decode response
            response_text = self.tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )
            
            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000
            tokens_used = outputs.shape[1]
            
            return ModelResponse(
                content=response_text.strip(),
                model=self.model_name,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                finish_reason="stop",
                metadata={
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timestamp=datetime.now(),
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate streaming response from Llama 3.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters
            
        Yields:
            Generated token strings
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Format prompt
            messages = [{"role": "user", "content": prompt}]
            formatted_prompt = self._format_chat_prompt(messages, system_prompt)
            
            # Tokenize
            inputs = self.tokenizer(
                formatted_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048,
            ).to(self.device)
            
            # Create streamer
            streamer = TextIteratorStreamer(
                self.tokenizer,
                skip_prompt=True,
                skip_special_tokens=True,
            )
            
            # Generation parameters
            generation_kwargs = dict(
                **inputs,
                streamer=streamer,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=kwargs.get("top_p", 0.9),
                top_k=kwargs.get("top_k", 50),
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
            
            # Start generation in separate thread
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()
            
            # Stream tokens
            for text in streamer:
                yield text
                await asyncio.sleep(0)  # Allow other tasks to run
            
            thread.join()
            
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs
    ) -> ModelResponse:
        """
        Generate chat-based response.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            ModelResponse object
        """
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Format chat prompt
            formatted_prompt = self._format_chat_prompt(messages)
            
            # Tokenize
            inputs = self.tokenizer(
                formatted_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048,
            ).to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=kwargs.get("top_p", 0.9),
                    top_k=kwargs.get("top_k", 50),
                    do_sample=temperature > 0,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            
            # Decode
            response_text = self.tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )
            
            latency_ms = (time.time() - start_time) * 1000
            tokens_used = outputs.shape[1]
            
            return ModelResponse(
                content=response_text.strip(),
                model=self.model_name,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                finish_reason="stop",
                metadata={
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "num_messages": len(messages),
                },
                timestamp=datetime.now(),
            )
            
        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            raise
    
    async def embed(self, text: str) -> List[float]:
        """
        Generate embeddings (using mean pooling of last hidden state).
        
        Args:
            text: Input text
            
        Returns:
            List of embedding values
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs, output_hidden_states=True)
                # Mean pooling on last hidden state
                hidden_states = outputs.hidden_states[-1]
                embeddings = hidden_states.mean(dim=1).squeeze()
            
            return embeddings.cpu().tolist()
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Cleanup model resources."""
        if self.model is not None:
            del self.model
            self.model = None
        
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.is_initialized = False
        logger.info("Model cleanup completed")

