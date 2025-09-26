import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from pathlib import Path
import logging

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Optional providers (import lazily and guard by availability flags)
try:
    import anthropic  # Claude API
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai  # Gemini API
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

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
            # Create main model for generation
            self.llm = Llama(
                model_path=str(model_path),
                n_ctx=kwargs.get('context_size', 4096),
                n_threads=kwargs.get('threads', 8),
                n_gpu_layers=kwargs.get('gpu_layers', 0),
                embedding=False,  # Disable embeddings to avoid issues
                verbose=False  # Suppress llama_print_timings output
            )
            # Try to create separate embedding model, fall back to simple embeddings if fails
            try:
                self.embed_model = Llama(
                    model_path=str(model_path),
                    n_ctx=512,  # Smaller context for embeddings
                    embedding=True,
                    n_threads=kwargs.get('threads', 8),
                    verbose=False  # Suppress llama_print_timings output
                )
                self.use_model_embeddings = True
            except:
                logger.warning("Could not create embedding model, using fallback embeddings")
                self.use_model_embeddings = False
                
        except ImportError:
            raise ImportError("llama-cpp-python not installed")
        
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 2048)
        # Store model path for clearer logging
        self.model_path = str(model_path)
        # Log model configuration for debug visibility
        try:
            logger.info(
                f"Local LLM configured: model_path={self.model_path}, "
                f"temperature={self.temperature}, max_tokens={self.max_tokens}, "
                f"context_size={kwargs.get('context_size', 4096)}, "
                f"threads={kwargs.get('threads', 8)}, gpu_layers={kwargs.get('gpu_layers', 0)}"
            )
        except Exception:
            # Avoid any logging issues breaking initialization
            pass
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using local LLM"""
        loop = asyncio.get_event_loop()
        
        def _generate():
            try:
                logger.info(f"Generating with prompt length: {len(prompt)}")
                # Add proper stop tokens for Llama
                stop_tokens = kwargs.get('stop', [])
                if hasattr(self.llm, 'metadata') and 'tokenizer.ggml.eos_token_id' in self.llm.metadata:
                    stop_tokens.extend(["<|eot_id|>", "<|end_of_text|>"])
                
                response = self.llm(
                    prompt,
                    max_tokens=kwargs.get('max_tokens', self.max_tokens),
                    temperature=kwargs.get('temperature', self.temperature),
                    stop=stop_tokens,
                    echo=False  # Don't repeat the prompt
                )
                
                if not response or 'choices' not in response:
                    logger.error(f"Invalid response structure: {response}")
                    return "I apologize, but I'm having trouble generating a response. Please try again."
                
                text = response['choices'][0].get('text', '')
                logger.info(f"Generated response length: {len(text)}")
                
                if not text or text.isspace():
                    return "Hello! I'm Sakana, your self-learning desktop assistant. How can I help you today?"
                
                return text.strip()
                
            except Exception as e:
                logger.error(f"Generation error: {e}")
                return f"I encountered an error: {str(e)}. Please try again."
        
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
        if self.use_model_embeddings:
            loop = asyncio.get_event_loop()
            
            def _embed():
                return self.embed_model.embed(text)
            
            try:
                return await loop.run_in_executor(None, _embed)
            except Exception as e:
                logger.warning(f"Model embedding failed, using fallback: {e}")
                self.use_model_embeddings = False
        
        # Fallback: Simple hash-based embeddings
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to normalized floats
        embedding = []
        for i in range(0, min(len(hash_bytes), 96), 3):
            if i + 2 < len(hash_bytes):
                value = (hash_bytes[i] + hash_bytes[i+1] + hash_bytes[i+2]) / (255.0 * 3)
                embedding.append(value * 2 - 1)  # Normalize to [-1, 1]
        
        # Pad to 384 dimensions
        while len(embedding) < 384:
            embedding.append(0.0)
            
        return embedding[:384]

class OpenAILLM(LLMInterface):
    """OpenAI API interface"""
    
    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
        # Support OpenAI-compatible endpoints by allowing base_url override (e.g., Ollama, LocalAI)
        base_url = kwargs.get('base_url')
        if base_url:
            # Create client pointed at custom base URL
            self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            # Default OpenAI cloud
            self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 2048)
        # Log model configuration for debug visibility
        try:
            logger.info(
                f"OpenAI LLM configured: model={self.model}, "
                f"temperature={self.temperature}, max_tokens={self.max_tokens}" +
                (f", base_url={base_url}" if base_url else "")
            )
        except Exception:
            pass

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

# ---- Anthropic (Claude) ----
class AnthropicLLM(LLMInterface):
    """Anthropic Claude interface (async)"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620", **kwargs):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 2048)
        try:
            logger.info(
                f"Anthropic LLM configured: model={self.model}, temperature={self.temperature}, max_tokens={self.max_tokens}"
            )
        except Exception:
            pass

    async def generate(self, prompt: str, **kwargs) -> str:
        try:
            resp = await self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get('temperature', self.temperature),
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
            )
            # Collect text segments from content blocks
            parts = []
            for block in getattr(resp, 'content', []) or []:
                text = getattr(block, 'text', None)
                if text:
                    parts.append(text)
            return "".join(parts) if parts else ""
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get('temperature', self.temperature),
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                stream=True,
            )
            async for event in stream:
                # Emit deltas for text blocks
                if getattr(event, 'type', None) == 'content_block_delta':
                    delta = getattr(event, 'delta', None)
                    text = getattr(delta, 'text', None) if delta else None
                    if text:
                        yield text
        except Exception as e:
            logger.error(f"Anthropic streaming failed: {e}")
            raise

    async def embed(self, text: str) -> List[float]:
        # Anthropic may not provide embeddings; use simple hash fallback for compatibility
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        embedding = []
        for i in range(0, min(len(hash_bytes), 96), 3):
            if i + 2 < len(hash_bytes):
                value = (hash_bytes[i] + hash_bytes[i+1] + hash_bytes[i+2]) / (255.0 * 3)
                embedding.append(value * 2 - 1)
        while len(embedding) < 384:
            embedding.append(0.0)
        return embedding[:384]

# ---- Google Gemini ----
class GeminiLLM(LLMInterface):
    """Google Gemini interface (wrap sync SDK in executor to preserve async contract)"""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", **kwargs):
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai not installed. Install with: pip install google-generativeai")
        # Configure SDK (global); acceptable for single-process assistant usage
        genai.configure(api_key=api_key)
        self.model = model
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_tokens = kwargs.get('max_tokens', 2048)
        try:
            logger.info(
                f"Gemini LLM configured: model={self.model}, temperature={self.temperature}, max_tokens={self.max_tokens}"
            )
        except Exception:
            pass

    async def generate(self, prompt: str, **kwargs) -> str:
        loop = asyncio.get_event_loop()
        def _call():
            gm = genai.GenerativeModel(self.model)
            resp = gm.generate_content(prompt, generation_config={
                'temperature': kwargs.get('temperature', self.temperature),
                'max_output_tokens': kwargs.get('max_tokens', self.max_tokens),
            })
            # Response has .text combining candidates
            return getattr(resp, 'text', '') or ''
        try:
            return await loop.run_in_executor(None, _call)
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        loop = asyncio.get_event_loop()
        def _stream_text_chunks() -> List[str]:
            gm = genai.GenerativeModel(self.model)
            stream = gm.generate_content(prompt, generation_config={
                'temperature': kwargs.get('temperature', self.temperature),
                'max_output_tokens': kwargs.get('max_tokens', self.max_tokens),
            }, stream=True)
            chunks: List[str] = []
            for ev in stream:
                text = getattr(ev, 'text', None)
                if text:
                    chunks.append(text)
            return chunks
        try:
            for chunk in await loop.run_in_executor(None, _stream_text_chunks):
                yield chunk
        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            raise

    async def embed(self, text: str) -> List[float]:
        loop = asyncio.get_event_loop()
        def _embed_call():
            try:
                resp = genai.embed_content(model='text-embedding-004', content=text)
                if isinstance(resp, dict):
                    emb = resp.get('embedding')
                    if isinstance(emb, dict):
                        return emb.get('values') or emb.get('embedding') or []
                    return emb or []
                # Some SDK versions return an object with .embedding
                emb = getattr(resp, 'embedding', None)
                if isinstance(emb, dict):
                    return emb.get('values') or []
                return emb or []
            except Exception:
                return []
        try:
            vec = await loop.run_in_executor(None, _embed_call)
            if vec:
                return vec
        except Exception as e:
            logger.warning(f"Gemini embedding failed, using fallback: {e}")
        # Fallback simple embedding
        import hashlib
        hb = hashlib.sha256(text.encode()).digest()
        out: List[float] = []
        for i in range(0, min(len(hb), 96), 3):
            if i + 2 < len(hb):
                v = (hb[i] + hb[i+1] + hb[i+2]) / (255.0 * 3)
                out.append(v * 2 - 1)
        while len(out) < 384:
            out.append(0.0)
        return out[:384]

# ---- xAI Grok (OpenAI-compatible endpoint) ----
class GrokLLM(OpenAILLM):
    """xAI Grok via OpenAI-compatible SDK (uses custom base_url)."""

    def __init__(self, api_key: str, model: str = "grok-2-latest", **kwargs):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
        base_url = kwargs.get('base_url') or 'https://api.x.ai/v1'
        super().__init__(api_key=api_key, model=model, base_url=base_url, **kwargs)

    async def embed(self, text: str) -> List[float]:
        # Grok endpoint may not support OpenAI embeddings; provide safe fallback
        import hashlib
        hb = hashlib.sha256(text.encode()).digest()
        out: List[float] = []
        for i in range(0, min(len(hb), 96), 3):
            if i + 2 < len(hb):
                v = (hb[i] + hb[i+1] + hb[i+2]) / (255.0 * 3)
                out.append(v * 2 - 1)
        while len(out) < 384:
            out.append(0.0)
        return out[:384]

class LLMFactory:
    """Factory for creating LLM interfaces"""
    
    @staticmethod
    def create(config: 'Config') -> LLMInterface:
        """Create LLM interface based on configuration"""
        if config.llm_provider == "local":
            model_path = config.models_dir / f"{config.model_name}.gguf"
            if not model_path.exists():
                logger.warning(f"Model not found: {model_path}, using mock LLM for testing")
                from .llm_interface_minimal import MockLLM
                return MockLLM()
            # Log provider selection and model details
            try:
                logger.info(
                    f"LLM provider selected: local, model={config.model_name}, path={model_path}"
                )
            except Exception:
                pass
            return LocalLLM(
                model_path=model_path,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
        elif config.llm_provider == "openai":
            if not config.api_key:
                logger.warning("OpenAI API key not provided, using mock LLM for testing")
                from .llm_interface_minimal import MockLLM
                return MockLLM()
            # Log provider selection and model details
            try:
                logger.info(
                    f"LLM provider selected: openai, model={config.model_name}" +
                    (f", base_url={config.openai_base_url}" if getattr(config, 'openai_base_url', None) else "")
                )
            except Exception:
                pass
            return OpenAILLM(
                api_key=config.api_key,
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                base_url=getattr(config, 'openai_base_url', None)
            )
        elif config.llm_provider == "anthropic":
            api_key = getattr(config, 'anthropic_api_key', None) or config.api_key
            if not api_key:
                logger.warning("Anthropic API key not provided, using mock LLM for testing")
                from .llm_interface_minimal import MockLLM
                return MockLLM()
            try:
                logger.info(f"LLM provider selected: anthropic, model={config.model_name}")
            except Exception:
                pass
            return AnthropicLLM(
                api_key=api_key,
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        elif config.llm_provider in ("gemini", "google"):
            api_key = getattr(config, 'gemini_api_key', None)
            if not api_key:
                logger.warning("Gemini API key not provided, using mock LLM for testing")
                from .llm_interface_minimal import MockLLM
                return MockLLM()
            try:
                logger.info(f"LLM provider selected: gemini, model={config.model_name}")
            except Exception:
                pass
            return GeminiLLM(
                api_key=api_key,
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        elif config.llm_provider == "grok":
            api_key = getattr(config, 'xai_api_key', None) or config.api_key
            if not api_key:
                logger.warning("xAI (Grok) API key not provided, using mock LLM for testing")
                from .llm_interface_minimal import MockLLM
                return MockLLM()
            base_url = getattr(config, 'xai_base_url', None) or 'https://api.x.ai/v1'
            try:
                logger.info(f"LLM provider selected: grok, model={config.model_name}, base_url={base_url}")
            except Exception:
                pass
            return GrokLLM(
                api_key=api_key,
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                base_url=base_url,
            )
        elif config.llm_provider == "mock":
            from .llm_interface_minimal import MockLLM
            try:
                logger.info("LLM provider selected: mock")
            except Exception:
                pass
            return MockLLM()
        else:
            raise ValueError(f"Unknown LLM provider: {config.llm_provider}")