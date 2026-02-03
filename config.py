"""
Paper Reader Agent - Configuration Module

Supports both OpenAI and DeepSeek APIs.
"""

import os
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMConfig(BaseModel):
    """LLM API Configuration"""
    
    provider: Literal["openai", "deepseek"] = Field(
        default="deepseek",
        description="API provider: 'openai' or 'deepseek'"
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
        description="Maximum tokens in response"
    )
    
    def get_api_key(self) -> str:
        """Get API key from config or environment"""
        if self.api_key:
            return self.api_key
        
        if self.provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
        else:  # deepseek
            key = os.getenv("DEEPSEEK_API_KEY")
        
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
        
        return None  # Use default for OpenAI


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


class AppConfig(BaseModel):
    """Main Application Configuration"""
    
    llm: LLMConfig = Field(default_factory=LLMConfig)
    parser: ParserConfig = Field(default_factory=ParserConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    
    @classmethod
    def from_args(
        cls,
        provider: str = "deepseek",
        model: Optional[str] = None,
        output_dir: str = "./output",
        use_gpu: bool = True
    ) -> "AppConfig":
        """Create config from command line arguments"""
        
        # Set default model based on provider
        if model is None:
            model = "deepseek-chat" if provider == "deepseek" else "gpt-4o"
        
        return cls(
            llm=LLMConfig(provider=provider, model=model),
            parser=ParserConfig(use_gpu=use_gpu),
            output=OutputConfig(output_dir=Path(output_dir))
        )


# Default configuration instance
default_config = AppConfig()
