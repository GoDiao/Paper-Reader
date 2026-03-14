"""
Paper Reader Agent - Configuration Module

Supports both OpenAI and DeepSeek APIs.
"""

import os
from pathlib import Path
from typing import Optional, Literal, ClassVar
from dotenv import load_dotenv
from pydantic import BaseModel, Field
# Load environment variables
load_dotenv()


ProviderType = Literal["openai", "deepseek", "siliconflow", "openrouter"]


class LLMConfig(BaseModel):
    """LLM API Configuration"""
    
    # Model-specific token limits (thinking models need more output tokens)
    MODEL_TOKEN_LIMITS: ClassVar[dict] = {
        # DeepSeek models
        "deepseek-chat": 8192,
        "deepseek-reasoner": 16384,   # DeepSeek-R1 (official API name)
        "deepseek-r1-distill": 16384, # Distilled reasoning model
        # Silicon Flow models
        "deepseek-ai/DeepSeek-V3": 8192,
        "deepseek-ai/DeepSeek-R1": 16384,
        "deepseek-ai/DeepSeek-V3.2": 8192,
        "Qwen/Qwen2.5-72B-Instruct": 8192,
        "Qwen/Qwen2.5-Coder-32B-Instruct": 8192,
        "MiniMaxAI/MiniMax-M2.1": 8192,
        "zai-org/GLM-4.7": 8192,
        "moonshotai/Kimi-K2-Thinking": 16384,
        # OpenAI models
        "gpt-4o": 16384,
        "gpt-4o-mini": 16384,
        "o1": 32768,                  # OpenAI reasoning model
        "o1-mini": 32768,
        "o1-preview": 32768,
        # OpenRouter curated models
        "openrouter/hunter-alpha": 8192,
    }
    
    provider: ProviderType = Field(
        default="deepseek",
        description="API provider: 'openai', 'deepseek', 'siliconflow', or 'openrouter'"
    )
    
    api_key: Optional[str] = Field(
        default=None,
        description="API key (loaded from env if not provided)"
    )
    
    model: str = Field(
        default="deepseek-chat",
        description="Model name to use"
    )
    
    base_url: Optional[str] = Field(
        default=None,
        description="Custom API base URL"
    )
    
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )
    
    max_tokens: int = Field(
        default=8192,
        description="Maximum tokens in response (overridden by model-specific limits)"
    )
    
    def get_max_tokens(self) -> int:
        """Get max tokens for the current model, with special handling for thinking models"""
        return self.MODEL_TOKEN_LIMITS.get(self.model, self.max_tokens)
    
    def is_thinking_model(self) -> bool:
        """Check if the current model is a reasoning/thinking model"""
        thinking_models = {
            "deepseek-reasoner", "deepseek-r1-distill",
            "deepseek-ai/DeepSeek-R1", # Silicon Flow R1
            "moonshotai/Kimi-K2-Thinking", # Kimi Thinking
            "o1", "o1-mini", "o1-preview"
        }
        return self.model in thinking_models
    
    def get_api_key(self) -> str:
        """Get API key from config or environment"""
        if self.api_key:
            return self.api_key
        
        if self.provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
        elif self.provider == "deepseek":
            key = os.getenv("DEEPSEEK_API_KEY")
        elif self.provider == "openrouter":
            key = os.getenv("OPENROUTER_API_KEY")
        else:  # siliconflow
            key = os.getenv("SILICONFLOW_API_KEY")
        
        if not key:
            raise ValueError(
                f"No API key found. Set {self.provider.upper()}_API_KEY environment variable "
                f"or pass api_key to config."
            )
        return key
    
    def get_base_url(self) -> Optional[str]:
        """Get API base URL"""
        if self.base_url:
            return self.base_url
        
        if self.provider == "deepseek":
            return "https://api.deepseek.com"
        elif self.provider == "siliconflow":
            return "https://api.siliconflow.com/v1"
        elif self.provider == "openrouter":
            return "https://openrouter.ai/api/v1"
        
        return None  # Use default for OpenAI


class AgentModelOverride(BaseModel):
    """Optional per-agent LLM overrides."""

    provider: Optional[ProviderType] = Field(
        default=None,
        description="Override provider for this agent"
    )
    model: Optional[str] = Field(
        default=None,
        description="Override model for this agent"
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Override temperature for this agent"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        description="Override max tokens for this agent"
    )

    def is_empty(self) -> bool:
        return (
            self.provider is None
            and self.model is None
            and self.temperature is None
            and self.max_tokens is None
        )


class PerAgentModelConfig(BaseModel):
    """Per-agent model overrides for hierarchical orchestrator roles."""

    architect: Optional[AgentModelOverride] = None
    context_hunter: Optional[AgentModelOverride] = None
    math_specialist: Optional[AgentModelOverride] = None
    data_auditor: Optional[AgentModelOverride] = None
    gap_agent: Optional[AgentModelOverride] = None
    editor_english: Optional[AgentModelOverride] = None
    editor_chinese: Optional[AgentModelOverride] = None

    @classmethod
    def from_env(cls) -> "PerAgentModelConfig":
        """
        Build per-agent override config from environment variables.

        Naming convention (per agent role):
        - AGENT_<ROLE>_PROVIDER
        - AGENT_<ROLE>_MODEL
        - AGENT_<ROLE>_TEMPERATURE
        - AGENT_<ROLE>_MAX_TOKENS
        """
        role_env_map = {
            "architect": "ARCHITECT",
            "context_hunter": "CONTEXT_HUNTER",
            "math_specialist": "MATH_SPECIALIST",
            "data_auditor": "DATA_AUDITOR",
            "gap_agent": "GAP_AGENT",
            "editor_english": "EDITOR_ENGLISH",
            "editor_chinese": "EDITOR_CHINESE",
        }

        data = {}
        for role, suffix in role_env_map.items():
            provider = (os.getenv(f"AGENT_{suffix}_PROVIDER") or "").strip() or None
            model = (os.getenv(f"AGENT_{suffix}_MODEL") or "").strip() or None

            temp_raw = (os.getenv(f"AGENT_{suffix}_TEMPERATURE") or "").strip()
            max_tokens_raw = (os.getenv(f"AGENT_{suffix}_MAX_TOKENS") or "").strip()

            temperature: Optional[float] = None
            if temp_raw:
                try:
                    temperature = float(temp_raw)
                except ValueError:
                    temperature = None

            max_tokens: Optional[int] = None
            if max_tokens_raw:
                try:
                    max_tokens = int(max_tokens_raw)
                except ValueError:
                    max_tokens = None

            override = AgentModelOverride(
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if not override.is_empty():
                data[role] = override

        return cls(**data)



class ParserConfig(BaseModel):
    """PDF Parser Configuration"""
    
    use_gpu: bool = Field(
        default=True,
        description="Use GPU acceleration for MinerU"
    )
    
    extract_images: bool = Field(
        default=True,
        description="Extract figures from PDF"
    )
    
    image_format: Literal["png", "jpg"] = Field(
        default="png",
        description="Output format for extracted images"
    )


class OutputConfig(BaseModel):
    """Output Configuration"""
    
    output_dir: Path = Field(
        default=Path("./output"),
        description="Output directory path"
    )
    
    report_filename: str = Field(
        default="paper_analysis.md",
        description="Output Markdown filename"
    )
    
    images_subdir: str = Field(
        default="images",
        description="Subdirectory for extracted images"
    )
    
    def ensure_dirs(self) -> None:
        """Create output directories if they don't exist"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / self.images_subdir).mkdir(exist_ok=True)
    
    @property
    def images_dir(self) -> Path:
        return self.output_dir / self.images_subdir
    
    @property
    def report_path(self) -> Path:
        return self.output_dir / self.report_filename


class WebSearchConfig(BaseModel):
    """Web Search Configuration for Reproduction Resources"""
    
    enable_web_search: bool = Field(
        default=False,
        description="Enable web search for reproduction resources"
    )
    
    github_token: Optional[str] = Field(
        default=None,
        description="GitHub Personal Access Token for higher rate limits"
    )
    
    huggingface_token: Optional[str] = Field(
        default=None,
        description="HuggingFace API token for accessing private resources"
    )
    
    serper_api_key: Optional[str] = Field(
        default=None,
        description="Serper API key for Google search (optional)"
    )
    
    def get_github_token(self) -> Optional[str]:
        """Get GitHub token from config or environment"""
        if self.github_token:
            return self.github_token
        return os.getenv("GITHUB_TOKEN")
    
    def get_huggingface_token(self) -> Optional[str]:
        """Get HuggingFace token from config or environment"""
        if self.huggingface_token:
            return self.huggingface_token
        return os.getenv("HUGGINGFACE_TOKEN")
    
    def get_serper_api_key(self) -> Optional[str]:
        """Get Serper API key from config or environment"""
        if self.serper_api_key:
            return self.serper_api_key
        return os.getenv("SERPER_API_KEY")
    
    def is_enabled(self) -> bool:
        """Check if web search is effectively enabled"""
        if not self.enable_web_search:
            return False
        # Web search is enabled if we have at least one token
        return bool(
            self.get_github_token() or 
            self.get_huggingface_token() or 
            self.get_serper_api_key()
        )


class IterationConfig(BaseModel):
    """Iterative analysis configuration."""

    enable_iteration: bool = Field(
        default=False,
        description="Enable iterative analysis (experts can request more info)",
    )
    max_iterations: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum iteration rounds",
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold to trigger iteration",
    )
    request_timeout: int = Field(
        default=30,
        description="Timeout (seconds) for processing each request",
    )
    auto_approve_requests: bool = Field(
        default=True,
        description="Automatically approve all requests (vs user approval)",
    )


class GapAgentConfig(BaseModel):
    """Gap Agent configuration."""

    enable_gap_agent: bool = Field(
        default=True,
        description="Enable Gap Agent review between specialist rounds",
    )
    gap_agent_model: str = Field(
        default="deepseek-chat",
        description="Model to use for Gap Agent (can be a cheaper model)",
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Iteration is recommended when overall confidence is below this threshold",
    )
    max_requests_per_round: int = Field(
        default=5,
        ge=0,
        description="Maximum number of unified requests per iteration round",
    )


class AppConfig(BaseModel):
    """Main Application Configuration"""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    per_agent_model: PerAgentModelConfig = Field(default_factory=PerAgentModelConfig)
    parser: ParserConfig = Field(default_factory=ParserConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    web_search: WebSearchConfig = Field(default_factory=WebSearchConfig)
    iteration: IterationConfig = Field(default_factory=IterationConfig)
    gap_agent: GapAgentConfig = Field(default_factory=GapAgentConfig)
    
    @classmethod
    def from_args(
        cls,
        provider: ProviderType = "deepseek",
        model: Optional[str] = None,
        output_dir: str = "./output",
        use_gpu: bool = True,
        enable_web_search: bool = False
    ) -> "AppConfig":
        """Create config from command line arguments"""
        
        # Set default model based on provider
        if model is None:
            if provider == "deepseek":
                model = "deepseek-chat"
            elif provider == "openrouter":
                model = "openai/gpt-4o-mini"
            else:
                model = "gpt-4o"
        
        return cls(
            llm=LLMConfig(provider=provider, model=model),
            parser=ParserConfig(use_gpu=use_gpu),
            output=OutputConfig(output_dir=Path(output_dir)),
            web_search=WebSearchConfig(enable_web_search=enable_web_search)
        )


# Default configuration instance
default_config = AppConfig()
