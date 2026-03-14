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

from config import LLMConfig, AgentModelOverride

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


def build_llm_config_for_agent(
    global_config: LLMConfig,
    override: Optional[AgentModelOverride] = None,
) -> LLMConfig:
    """
    Build effective LLM config for a specific agent role.

    If override is not provided, returns a clone of global config.
    """
    data = global_config.dict()
    if override:
        if override.provider is not None:
            data["provider"] = override.provider
        if override.model is not None:
            data["model"] = override.model
        if override.temperature is not None:
            data["temperature"] = override.temperature
        if override.max_tokens is not None:
            data["max_tokens"] = override.max_tokens
    return LLMConfig(**data)


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
    agent_key: str = "llm",
    **kwargs
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
                # Check if we should stream (passed in kwargs or default false, checking here just in case, but we need to add stream param to function first)
                # Actually, we'll modify the function signature to accept `stream` param or just use kwargs.
                # Let's check signature again. We need to add `stream` parameter.
                
                is_stream = kwargs.get("stream", False)
                
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    stream=is_stream
                )
                
                if is_stream:
                    chunks = []
                    for chunk in response:
                        if chunk is None:
                            continue
                        choices = getattr(chunk, "choices", None)
                        if not choices or len(choices) == 0:
                            continue
                        delta = getattr(choices[0], "delta", None)
                        if delta is None:
                            continue
                        content = getattr(delta, "content", None) if delta else None
                        if content:
                            chunks.append(content)
                            if progress_callback:
                                progress_callback.stream_token(agent_key, content)
                    result = "".join(chunks)
                else:
                    # Support both object and dict-like response (e.g. OpenRouter)
                    try:
                        if response is None:
                            raise ValueError("API returned no response.")
                        choices = getattr(response, "choices", None)
                        if choices is None and hasattr(response, "__getitem__"):
                            choices = response.get("choices") if callable(getattr(response, "get", None)) else None
                        if choices is None or (hasattr(choices, "__len__") and len(choices) == 0):
                            raise ValueError(
                                f"API returned no choices (response.choices is {choices!r}). "
                                "Check provider/model and API response format."
                            )
                        first = next(iter(choices), None) if choices is not None else None
                        if first is None:
                            raise ValueError("API response has no first choice.")
                        msg = getattr(first, "message", None)
                        if msg is None and hasattr(first, "__getitem__"):
                            msg = first.get("message") if callable(getattr(first, "get", None)) else None
                        if msg is None:
                            raise ValueError("API response.choices[0].message is missing.")
                        result = getattr(msg, "content", None)
                        if result is None and hasattr(msg, "get"):
                            result = msg.get("content")
                        result = result or ""
                    except (TypeError, KeyError) as e:
                        # e.g. 'NoneType' object is not subscriptable when provider returns malformed body
                        logger.warning(
                            "API response structure unexpected (%s): %s. Using empty content.",
                            agent_name, e
                        )
                        result = ""
                
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
        agent_key: str = "llm",
        **kwargs
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
            agent_key=agent_key,
            **kwargs
        )
