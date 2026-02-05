"""
Chat Agent for Paper Reader

Allows users to chat with the AI about analyzed papers.
"""

import os
import logging
from typing import List, Dict, Tuple, Optional

from config import LLMConfig
from llm import LLMClientFactory

logger = logging.getLogger(__name__)


CHAT_SYSTEM_PROMPT = """You are a helpful research assistant. You have access to a detailed analysis report of an academic paper.

Your role is to:
1. Answer questions about the paper's content, methods, and findings
2. Explain technical concepts in simpler terms when asked
3. Help the user understand specific equations or algorithms
4. Discuss the paper's strengths, limitations, and potential applications
5. Compare aspects of this paper to general knowledge in the field

Be precise, cite specific sections when relevant, and acknowledge when something is unclear or not covered in the report.

Here is the paper analysis report you should reference:
---
{report}
---

Now respond to the user's questions about this paper."""


class ChatAgent:
    """
    Chat agent for discussing paper analysis reports.
    Uses the same LLM provider as the main analysis.
    """
    
    def __init__(
        self,
        provider: str = "deepseek",
        model: str = "deepseek-chat",
        api_key: str = None,
        base_url: str = None
    ):
        self.provider = provider
        self.model = model
        
        # Create LLM config and factory
        llm_config = LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url
        )
        
        self.factory = LLMClientFactory(llm_config)
    
    async def summarize_history(
        self,
        current_summary: str,
        recent_messages: List[Dict[str, str]]
    ) -> str:
        """
        Summarize the recent conversation history, merging with existing summary.
        """
        if not recent_messages:
            return current_summary
            
        summary_prompt = f"""Summarize the following conversation history, incorporating the previous summary if it exists. 
Focus on key information, user intent, and important context that should be preserved for future turns.
Keep the summary concise but comprehensive.

Previous Summary:
{current_summary or "None"}

Recent Messages:
"""
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            summary_prompt += f"{role}: {content}\n"
            
        summary_prompt += "\n\nNew Summary:"
        
        try:
            return self.factory.chat_completions(
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=1000,
                temperature=0.5,
                agent_name="ChatSummarizer"
            ).strip()
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return current_summary

    async def chat(
        self,
        report: str,
        messages: List[Dict[str, str]],
        context_summary: str = "",
        max_tokens: int = 2048
    ) -> Tuple[str, Optional[Dict]]:
        """
        Process a chat request with message history and context summary.
        """
        # Determine system prompt
        base_prompt = CHAT_SYSTEM_PROMPT.format(report=report[:30000])
        if context_summary:
            system_prompt = f"{base_prompt}\n\nContext Summary:\n{context_summary}"
        else:
            system_prompt = base_prompt
        
        # Build messages list
        api_messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (limit to last 10 messages)
        # The summary handles older context
        for msg in messages[-10:]:
            api_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        try:
            # Note: factory doesn't return usage metadata, so we'll create a basic one
            # For full metadata, we'd need to extend the factory or call client directly
            content = self.factory.chat_completions(
                messages=api_messages,
                max_tokens=max_tokens,
                temperature=0.7,
                agent_name="ChatAgent"
            )
            
            metadata = {
                "model": self.model,
                "usage": {
                    "prompt_tokens": 0,  # Not available from factory wrapper
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
            
            return content, metadata
            
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            raise
    
    def chat_stream(
        self,
        report: str,
        messages: List[Dict[str, str]],
        context_summary: str = "",
        max_tokens: int = 2048
    ):
        """
        Stream chat response with context summary.
        """
        # Determine system prompt
        base_prompt = CHAT_SYSTEM_PROMPT.format(report=report[:30000])
        if context_summary:
            system_prompt = f"{base_prompt}\n\nContext Summary:\n{context_summary}"
        else:
            system_prompt = base_prompt
        
        # Build messages list
        api_messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in messages[-10:]:
            api_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        try:
            # For streaming, we need to use the client directly
            # Factory doesn't support streaming yet, so use client
            response = self.factory.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                max_tokens=max_tokens,
                temperature=0.7,
                stream=True
            )
            
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
                    
        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            raise
            
    def chat_sync(
        self,
        report: str,
        messages: List[Dict[str, str]],
        context_summary: str = "",
        max_tokens: int = 2048
    ) -> Tuple[str, Optional[Dict]]:
        """Synchronous version of chat."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.chat(report, messages, context_summary, max_tokens)
        )
