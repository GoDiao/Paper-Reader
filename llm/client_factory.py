"""
Unified LLM Client Factory

Centralizes LLM client creation and API call handling with:
- Provider/key/base_url resolution (via LLMConfig)
- Timeout configuration
- Retry/backoff with exponential backoff + jitter
- Global concurrency limiting (optional)
"""

import os
import time
import random
import logging
import threading
from typing import Optional, Dict, List, Any
from openai import OpenAI

from config import LLMConfig

logger = logging.getLogger(__name__)

# Global concurrency limiter (optional, controlled by env)
_global_semaphore: Optional[threading.BoundedSemaphore] = None
_semaphore_lock = threading.Lock()


def _get_global_semaphore() -> Optional[threading.BoundedSemaphore]:
    """Get or create global concurrency semaphore."""
    global _global_semaphore
    
    with _semaphore_lock:
        if _global_semaphore is None:
            max_concurrency = int(os.getenv("LLM_MAX_CONCURRENCY", "0"))
            if max_concurrency > 0:
                _global_semaphore = threading.BoundedSemaphore(max_concurrency)
                logger.info(f"Global LLM concurrency limit: {max_concurrency}")
            else:
                logger.debug("Global LLM concurrency limit disabled")
    
    return _global_semaphore


def create_llm_client(llm_config: LLMConfig) -> OpenAI:
    """
    Create an OpenAI-compatible client from LLMConfig.
    
    Args:
        llm_config: LLMConfig instance with provider/model/etc.
        
    Returns:
        OpenAI client instance configured for the provider.
    """
    api_key = llm_config.get_api_key()
    base_url = llm_config.get_base_url()
    
    return OpenAI(
        api_key=api_key,
        base_url=base_url
    )


def chat_completions_create(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    base_delay: float = 2.0,
    progress_callback: Optional[Any] = None,
    agent_name: str = "LLM",
    phase: str = "analysis",
    agent_key: str = "llm"
) -> str:
    """
    Unified chat completions call with retry/backoff and optional progress callbacks.
    
    Args:
        client: OpenAI client instance
        model: Model name
        messages: List of message dicts (role/content)
        temperature: Sampling temperature (optional)
        max_tokens: Max response tokens (optional)
        timeout: Request timeout in seconds (default from LLM_TIMEOUT_S env or 60.0)
        max_retries: Max retry attempts (default from LLM_MAX_RETRIES env or 3)
        base_delay: Base delay for exponential backoff (seconds)
        progress_callback: Optional ProgressCallback instance for emitting progress events
        agent_name: Human-readable agent name for logging
        phase: Progress phase ("analysis", "assembly", etc.)
        agent_key: Agent key for progress events (must match frontend data-agent values)
        
    Returns:
        Response content string
        
    Raises:
        Exception: If all retries exhausted or non-retryable error
    """
    # Get timeout and retry config from env or defaults
    if timeout is None:
        timeout = float(os.getenv("LLM_TIMEOUT_S", "60.0"))
    
    if max_retries is None:
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
    
    # Get global semaphore for concurrency limiting
    semaphore = _get_global_semaphore()
    
    # Emit progress: starting LLM call
    if progress_callback:
        progress_callback.emit(
            phase=phase,
            agent=agent_key,
            status="in_progress",
            message=f"Calling {agent_name}... (attempt 1/{max_retries + 1})",
            progress=10
        )
    
    # Retry loop with exponential backoff + jitter
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            # Acquire semaphore if concurrency limiting enabled
            if semaphore:
                semaphore.acquire()
            
            try:
                # Make API call
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
                
                result = response.choices[0].message.content
                
                # Emit progress: success
                if progress_callback:
                    progress_callback.emit(
                        phase=phase,
                        agent=agent_key,
                        status="in_progress",
                        message=f"{agent_name} responded ({len(result):,} chars)",
                        progress=90
                    )
                
                return result
                
            finally:
                # Always release semaphore
                if semaphore:
                    semaphore.release()
                    
        except Exception as e:
            last_exception = e
            error_str = str(e)
            
            # Check if retryable (rate limit or server errors)
            is_retryable = (
                "429" in error_str or 
                "503" in error_str or 
                "500" in error_str or
                "timeout" in error_str.lower() or
                "connection" in error_str.lower()
            )
            
            if is_retryable and attempt < max_retries:
                # Calculate delay with exponential backoff + jitter
                delay = (base_delay * (2 ** attempt)) + (random.random() * 0.5)
                
                # Emit progress: retrying
                if progress_callback:
                    error_type = "429" if "429" in error_str else "5xx" if any(x in error_str for x in ["500", "503"]) else "timeout"
                    progress_callback.emit(
                        phase=phase,
                        agent=agent_key,
                        status="in_progress",
                        message=f"{error_type} error, retrying in {delay:.1f}s (attempt {attempt + 2}/{max_retries + 1})",
                        progress=20 + (attempt * 10)
                    )
                
                logger.warning(
                    f"{agent_name} hit {error_str}. Retrying in {delay:.1f}s "
                    f"(Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
                continue
            
            # Not retryable or out of retries
            if progress_callback:
                progress_callback.emit(
                    phase=phase,
                    agent=agent_key,
                    status="error",
                    message=f"{agent_name} failed: {error_str[:100]}",
                    progress=0
                )
            
            logger.error(f"API Error ({agent_name}): {e}")
            raise
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError(f"{agent_name} failed after {max_retries + 1} attempts")


class LLMClientFactory:
    """
    Factory class for creating and managing LLM clients.
    
    Provides a convenient interface for creating clients and making calls
    with unified configuration.
    """
    
    def __init__(self, llm_config: LLMConfig):
        """
        Initialize factory with LLM configuration.
        
        Args:
            llm_config: LLMConfig instance
        """
        self.config = llm_config
        self._client: Optional[OpenAI] = None
    
    @property
    def client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            self._client = create_llm_client(self.config)
        return self._client
    
    def chat_completions(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        progress_callback: Optional[Any] = None,
        agent_name: str = "LLM",
        phase: str = "analysis",
        agent_key: str = "llm"
    ) -> str:
        """
        Make a chat completions call using factory configuration.
        
        Args:
            messages: List of message dicts
            temperature: Override default temperature
            max_tokens: Override default max_tokens (uses config.get_max_tokens() if None)
            timeout: Override default timeout
            max_retries: Override default max_retries
            progress_callback: Optional progress callback
            agent_name: Human-readable agent name
            phase: Progress phase
            agent_key: Agent key for progress events
            
        Returns:
            Response content string
        """
        # Use config's max_tokens if not provided
        if max_tokens is None:
            max_tokens = self.config.get_max_tokens()
        
        return chat_completions_create(
            client=self.client,
            model=self.config.model,
            messages=messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            progress_callback=progress_callback,
            agent_name=agent_name,
            phase=phase,
            agent_key=agent_key
        )
