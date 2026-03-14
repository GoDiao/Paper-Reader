"""
Configuration Manager for Web-based API Key overrides

- .env = base config (never modified)
- data/user_config.json = web overrides (saved from Config page)
- Effective config = .env values overridden by user_config, applied to os.environ
"""

import os
import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from io import StringIO

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
USER_CONFIG_FILE = DATA_DIR / "user_config.json"


@dataclass
class ConfigField:
    """Definition of a configuration field."""
    key: str
    label: str
    description: str
    placeholder: str
    is_secret: bool = True
    required: bool = False


# Configuration schema (keys that can be overridden via web)
CONFIG_SCHEMA = {
    "general": {
        "title": "General Settings",
        "fields": [
            ConfigField("DEFAULT_LLM_PROVIDER", "Default LLM Provider", "Homepage analysis uses this provider (deepseek/openai/siliconflow/openrouter)", "deepseek", False),
            ConfigField("DEFAULT_LLM_MODEL", "Default LLM Model", "Homepage analysis uses this default model", "deepseek-chat", False),
            ConfigField("DEEPSEEK_API_KEY", "DeepSeek API Key", "Default provider for paper analysis", "sk-...", True, True),
            ConfigField("OPENAI_API_KEY", "OpenAI API Key", "Alternative provider", "sk-..."),
            ConfigField("SILICONFLOW_API_KEY", "SiliconFlow API Key", "Another alternative provider", "sk-..."),
            ConfigField("OPENROUTER_API_KEY", "OpenRouter API Key", "OpenRouter provider key", "sk-or-v1-..."),
            ConfigField("LLM_TIMEOUT_S", "LLM Timeout (seconds)", "Request timeout for LLM API calls", "60.0", False),
            ConfigField("LLM_MAX_RETRIES", "Max Retries", "Maximum retry attempts for failed API calls", "3", False),
            ConfigField("LLM_MAX_CONCURRENCY", "Max Concurrency", "Global concurrency limit (0 = disabled)", "0", False),
        ]
    },
    "agent_models": {
        "title": "Per-Agent Models",
        "fields": [
            ConfigField("AGENT_ARCHITECT_PROVIDER", "Architect Provider", "openai/deepseek/siliconflow/openrouter (optional)", "deepseek", False),
            ConfigField("AGENT_ARCHITECT_MODEL", "Architect Model", "Model override for Architect", "deepseek-chat", False),
            ConfigField("AGENT_CONTEXT_HUNTER_PROVIDER", "Context Hunter Provider", "openai/deepseek/siliconflow/openrouter (optional)", "deepseek", False),
            ConfigField("AGENT_CONTEXT_HUNTER_MODEL", "Context Hunter Model", "Model override for Context Hunter", "deepseek-chat", False),
            ConfigField("AGENT_MATH_SPECIALIST_PROVIDER", "Math Specialist Provider", "openai/deepseek/siliconflow/openrouter (optional)", "deepseek", False),
            ConfigField("AGENT_MATH_SPECIALIST_MODEL", "Math Specialist Model", "Model override for Math Specialist", "deepseek-reasoner", False),
            ConfigField("AGENT_DATA_AUDITOR_PROVIDER", "Data Auditor Provider", "openai/deepseek/siliconflow/openrouter (optional)", "deepseek", False),
            ConfigField("AGENT_DATA_AUDITOR_MODEL", "Data Auditor Model", "Model override for Data Auditor", "deepseek-chat", False),
            ConfigField("AGENT_GAP_AGENT_PROVIDER", "Gap Agent Provider", "openai/deepseek/siliconflow/openrouter (optional)", "deepseek", False),
            ConfigField("AGENT_GAP_AGENT_MODEL", "Gap Agent Model", "Model override for Gap Agent", "deepseek-chat", False),
            ConfigField("AGENT_EDITOR_ENGLISH_PROVIDER", "Editor (EN) Provider", "openai/deepseek/siliconflow/openrouter (optional)", "openai", False),
            ConfigField("AGENT_EDITOR_ENGLISH_MODEL", "Editor (EN) Model", "Model override for English Editor", "gpt-4o", False),
            ConfigField("AGENT_EDITOR_CHINESE_PROVIDER", "Editor (ZH) Provider", "openai/deepseek/siliconflow/openrouter (optional)", "openai", False),
            ConfigField("AGENT_EDITOR_CHINESE_MODEL", "Editor (ZH) Model", "Model override for Chinese Editor", "gpt-4o", False),
        ]
    },
    "web_search": {
        "title": "Web Search",
        "fields": [
            ConfigField("ENABLE_WEB_SEARCH", "Enable Web Search", "Enable web search for reproduction resources", "true", False),
            ConfigField("GITHUB_TOKEN", "GitHub Token", "Personal Access Token for higher rate limits", "ghp_..."),
            ConfigField("HUGGINGFACE_TOKEN", "HuggingFace Token", "API token for private models/datasets", "hf_..."),
            ConfigField("SERPER_API_KEY", "Serper API Key", "For Google search integration", "your_api_key"),
        ]
    },
    "deep_research": {
        "title": "Deep Research",
        "fields": [
            ConfigField("TAVILY_API_KEY", "Tavily API Key", "For Tavily Deep Research feature", "tvly-..."),
            ConfigField("VALYU_API_KEY", "Valyu API Key", "For Valyu Deep Research (alternative)", "val_..."),
            ConfigField("DEFAULT_RESEARCH_PROVIDER", "Default Provider", "tavily or valyu", "tavily", False),
        ]
    },
    "notion": {
        "title": "Notion Export",
        "fields": [
            ConfigField("NOTION_SECRET", "Notion Secret", "For exporting reports to Notion", "secret_..."),
            ConfigField("NOTION_PARENT_PAGE_ID", "Notion Parent Page ID", "Parent page ID for new exports", "your_page_id", False),
            ConfigField("IMGBB_API_KEY", "ImgBB API Key", "For image hosting in Notion exports", "your_imgbb_key"),
        ]
    }
}


def _get_effective_value(key: str, base_values: Dict[str, str], override_values: Dict[str, str]) -> str:
    """Effective = override if set, else base (.env)."""
    if key in override_values and override_values[key]:
        return override_values[key]
    return base_values.get(key, "")


def _parse_env_content(content: str) -> Dict[str, str]:
    """Parse .env-style content into key-value dict."""
    from dotenv import dotenv_values
    return dotenv_values(stream=StringIO(content))


class ConfigManager:
    """
    Web overrides stored in data/user_config.json.
    .env is NEVER modified. At runtime, user_config overrides .env.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    async def _load_base_config(self) -> Dict[str, str]:
        """Load base config from .env (read-only)."""
        env_file = BASE_DIR / ".env"
        if not env_file.exists():
            return {}
        async with aiofiles.open(env_file, "r", encoding="utf-8") as f:
            content = await f.read()
        return _parse_env_content(content) or {}

    async def _load_user_overrides(self) -> Dict[str, str]:
        """Load user overrides from data/user_config.json."""
        if not USER_CONFIG_FILE.exists():
            return {}
        try:
            async with aiofiles.open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _mask_value(self, value: str) -> str:
        """Mask secret values for display."""
        if not value:
            return ""
        if len(value) <= 8:
            return "*" * len(value)
        return value[:4] + "*" * (len(value) - 8) + value[-4:]

    async def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration: base (.env) merged with overrides (user_config)."""
        base = await self._load_base_config()
        overrides = await self._load_user_overrides()

        result = {}
        for category, schema in CONFIG_SCHEMA.items():
            result[category] = {
                "title": schema["title"],
                "fields": []
            }
            for field in schema["fields"]:
                effective = _get_effective_value(field.key, base, overrides)
                from_override = field.key in overrides and overrides[field.key]
                result[category]["fields"].append({
                    "key": field.key,
                    "label": field.label,
                    "description": field.description,
                    "value": effective if not field.is_secret else self._mask_value(effective),
                    "placeholder": field.placeholder,
                    "is_secret": field.is_secret,
                    "required": field.required,
                    "has_value": bool(effective),
                    "from_override": bool(from_override),
                })

        return result

    async def update_config(self, updates: Dict[str, str]) -> Dict[str, Any]:
        """
        Save overrides to data/user_config.json only. Never touch .env.
        Then apply to os.environ so they take effect immediately.
        """
        if not updates:
            return {"status": "success", "updated_keys": [], "count": 0}

        # Validate keys
        all_keys = set()
        for schema in CONFIG_SCHEMA.values():
            for field in schema["fields"]:
                all_keys.add(field.key)

        filtered = {k: v for k, v in updates.items() if k in all_keys and v}
        if not filtered:
            return {"status": "success", "updated_keys": [], "count": 0}

        async with self._lock:
            # Load current overrides
            current = await self._load_user_overrides()
            current.update(filtered)

            # Write to user_config.json only
            async with aiofiles.open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
                await f.write(json.dumps(current, ensure_ascii=False, indent=2))

            # Apply to os.environ (override .env in memory)
            for k, v in filtered.items():
                os.environ[k] = v

            return {
                "status": "success",
                "updated_keys": list(filtered.keys()),
                "count": len(filtered),
            }


config_manager = ConfigManager()
