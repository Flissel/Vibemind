import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
import openai
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class LLMInterface(ABC):
    """Abstract base class for LLM interfaces"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream a response from the LLM"""
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        pass

class LocalLLM(LLMInterface):
    """Local LLM using llama.cpp"""
    
    def __init__(self, model_path: Path, **kwargs):
        try:
            from llama_cpp import Llama
            self.llm = Llama(
                model_path=str(model_path),
                n_ctx=kwargs.get('context_size', 4096),
                n_threads=kwargs.get('threads', 8),
                n_gpu_layers=kwargs.get('gpu_layers', 0)
            )
        except ImportError:
            raise ImportError("llama-cpp-python not installed")
        
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 2048)
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using local LLM"""
        loop = asyncio.get_event_loop()
        
        def _generate():
            response = self.llm(
                prompt,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                stop=kwargs.get('stop', [])
            )
            return response['choices'][0]['text']
        
        return await loop.run_in_executor(None, _generate)
    
    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream response from local LLM"""
        loop = asyncio.get_event_loop()
        
        def _stream():
            stream = self.llm(
                prompt,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                stop=kwargs.get('stop', []),
                stream=True
            )
            for output in stream:
                yield output['choices'][0]['text']
        
        for chunk in await loop.run_in_executor(None, lambda: list(_stream())):
            yield chunk
    
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings using local model"""
        loop = asyncio.get_event_loop()
        
        def _embed():
            return self.llm.embed(text)
        
        return await loop.run_in_executor(None, _embed)

class OpenAILLM(LLMInterface):
    """OpenAI API interface"""
    
    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 2048)
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get('temperature', self.temperature),
                max_tokens=kwargs.get('max_tokens', self.max_tokens)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise
    
    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI"""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get('temperature', self.temperature),
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            raise
    
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI"""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise

class LLMFactory:
    """Factory for creating LLM interfaces"""
    
    @staticmethod
    def create(config: 'Config') -> LLMInterface:
        """Create LLM interface based on configuration"""
        if config.llm_provider == "local":
            model_path = config.models_dir / f"{config.model_name}.gguf"
            if not model_path.exists():
                raise FileNotFoundError(f"Model not found: {model_path}")
            return LocalLLM(
                model_path=model_path,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
        elif config.llm_provider == "openai":
            if not config.api_key:
                raise ValueError("OpenAI API key not provided")
            return OpenAILLM(
                api_key=config.api_key,
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
        else:
            raise ValueError(f"Unknown LLM provider: {config.llm_provider}")