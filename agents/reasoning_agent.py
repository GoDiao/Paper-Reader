"""
Reasoning Agent Module - LLM-powered paper analysis.

Implements two-role analysis strategy:
1. Architect: Global structure analysis
2. Math Deriver: Detailed formula derivation
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import LLMConfig
from llm import LLMClientFactory

from .prompts import (
    ARCHITECT_PROMPT,
    MATH_DERIVER_PROMPT,
    SYNTHESIS_PROMPT,
    DOMAIN_DETECTION_PROMPT,
    IMAGE_CAPTION_PROMPT,
)

console = Console()


@dataclass
class AnalysisResult:
    """Result of paper analysis"""
    title: str = ""
    domain: str = ""
    tldr: str = ""
    background: str = ""
    problem: str = ""
    method_overview: str = ""
    method_derivations: str = ""
    experiments: str = ""
    conclusions: str = ""
    figure_suggestions: Dict[str, str] = field(default_factory=dict)
    full_report: str = ""
    raw_architect_output: str = ""
    raw_math_output: str = ""


class ReasoningAgent:
    """
    LLM-powered reasoning agent for paper analysis.
    
    Supports both OpenAI and DeepSeek APIs.
    """
    
    def __init__(
        self,
        provider: str = "deepseek",
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ):
        """
        Initialize the reasoning agent.
        
        Args:
            provider: API provider ("openai", "deepseek", or "siliconflow")
            model: Model name to use
            api_key: API key (or from environment)
            base_url: Custom API base URL
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
        """
        # Create LLM config
        llm_config = LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Create factory for unified client management
        self.factory = LLMClientFactory(llm_config)
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        console.print(
            f"[green]✓[/green] Initialized {provider} client "
            f"with model: {model}"
        )
    
    def analyze_paper(
        self,
        content: str,
        title: str = "",
        images: Optional[List[Any]] = None
    ) -> AnalysisResult:
        """
        Perform comprehensive paper analysis.
        
        Args:
            content: Markdown content of the paper
            title: Paper title (optional)
            images: List of ImageInfo objects (optional)
            
        Returns:
            AnalysisResult with full analysis
        """
        result = AnalysisResult(title=title)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Step 1: Detect domain
            task = progress.add_task("Detecting research domain...", total=None)
            result.domain = self._detect_domain(content[:8000])
            progress.remove_task(task)
            console.print(f"[blue]  → Domain:[/blue] {result.domain}")
            
            # Step 2: Global structure analysis (Architect)
            task = progress.add_task("Analyzing paper structure...", total=None)
            result.raw_architect_output = self._run_architect(content)
            progress.remove_task(task)
            console.print("[green]  ✓ Structure analysis complete[/green]")
            
            # Step 3: Extract equations for derivation
            task = progress.add_task("Extracting equations...", total=None)
            equations = self._extract_equations(content, result.raw_architect_output)
            progress.remove_task(task)
            console.print(f"[blue]  → Found {len(equations)} key equations[/blue]")
            
            # Step 4: Mathematical derivation (Math Deriver)
            if equations:
                task = progress.add_task("Deriving formulas...", total=None)
                result.raw_math_output = self._run_math_deriver(
                    equations=equations,
                    context=content,
                    domain=result.domain
                )
                progress.remove_task(task)
                console.print("[green]  ✓ Formula derivation complete[/green]")
            
            # Step 5: Synthesize final report
            task = progress.add_task("Generating report...", total=None)
            result.full_report = self._synthesize_report(
                architect_output=result.raw_architect_output,
                math_output=result.raw_math_output,
                title=title
            )
            progress.remove_task(task)
            console.print("[green]  ✓ Report generated[/green]")
            
            # Step 6: Extract figure suggestions
            result.figure_suggestions = self._extract_figure_suggestions(
                result.full_report
            )
        
        return result
    
    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Make an LLM API call using unified factory"""
        return self.factory.chat_completions(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            agent_name="ReasoningAgent"
        )
    
    def _detect_domain(self, excerpt: str) -> str:
        """Detect the research domain of the paper"""
        prompt = DOMAIN_DETECTION_PROMPT.format(excerpt=excerpt[:5000])
        
        messages = [
            {"role": "system", "content": "You are a research domain classifier."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_llm(messages, temperature=0.1, max_tokens=50)
        return response.strip()
    
    def _run_architect(self, content: str) -> str:
        """Run the Architect agent for global analysis"""
        # Truncate if too long (keep most important parts)
        if len(content) > 100000:
            # Keep abstract, introduction, method, and conclusion
            content = self._smart_truncate(content, 100000)
        
        prompt = ARCHITECT_PROMPT.format(content=content)
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior research scientist analyzing academic papers. "
                    "Provide thorough, accurate analysis with specific references to the content."
                )
            },
            {"role": "user", "content": prompt}
        ]
        
        return self._call_llm(messages)
    
    def _extract_equations(
        self,
        content: str,
        architect_output: str
    ) -> str:
        """Extract key equations for detailed derivation"""
        equations = []
        
        # Find LaTeX block equations
        block_pattern = r'\$\$(.*?)\$\$'
        block_matches = re.findall(block_pattern, content, re.DOTALL)
        equations.extend(block_matches[:10])  # Limit to 10 equations
        
        # Find inline equations that look important (referenced in text)
        inline_pattern = r'(?:Eq\.?\s*\(?\d+\)?|equation\s*\(?\d+\)?)[^$]*(\$[^$]+\$)'
        inline_matches = re.findall(inline_pattern, content, re.IGNORECASE)
        equations.extend(inline_matches[:5])
        
        # Look for <DERIVE: ...> tags from architect output
        derive_pattern = r'<DERIVE:\s*([^>]+)>'
        derive_matches = re.findall(derive_pattern, architect_output)
        
        # Combine and format
        equation_text = ""
        for i, eq in enumerate(equations, 1):
            equation_text += f"\n### Equation {i}\n$$\n{eq.strip()}\n$$\n"
        
        if derive_matches:
            equation_text += "\n### Equations marked for derivation:\n"
            for match in derive_matches:
                equation_text += f"- {match}\n"
        
        return equation_text
    
    def _run_math_deriver(
        self,
        equations: str,
        context: str,
        domain: str
    ) -> str:
        """Run the Math Deriver agent for formula derivation"""
        if not equations.strip():
            return ""
        
        # Extract relevant context around equations
        context_excerpt = self._extract_method_section(context)
        
        prompt = MATH_DERIVER_PROMPT.format(
            domain=domain,
            equations=equations,
            context=context_excerpt
        )
        
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a mathematical expert specializing in {domain}. "
                    "Provide detailed, step-by-step derivations with clear explanations."
                )
            },
            {"role": "user", "content": prompt}
        ]
        
        return self._call_llm(messages)
    
    def _synthesize_report(
        self,
        architect_output: str,
        math_output: str,
        title: str
    ) -> str:
        """Synthesize the final comprehensive report"""
        prompt = SYNTHESIS_PROMPT.format(
            architect_output=architect_output,
            math_output=math_output or "(No mathematical derivations needed)"
        )
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a technical writer creating a comprehensive paper analysis. "
                    "Create a well-structured, readable document that combines all analysis."
                )
            },
            {"role": "user", "content": prompt}
        ]
        
        report = self._call_llm(messages)
        
        # Add title header if provided
        if title:
            report = f"# 📄 {title}\n\n{report}"
        
        return report
    
    def _extract_figure_suggestions(
        self,
        report: str
    ) -> Dict[str, str]:
        """Extract figure insertion suggestions from report"""
        suggestions = {}
        
        # Find <INSERT_FIGURE: ...> tags
        pattern = r'<INSERT_FIGURE:\s*([^>]+)>'
        matches = re.findall(pattern, report)
        
        for match in matches:
            parts = match.split(' - ', 1)
            figure_id = parts[0].strip()
            description = parts[1].strip() if len(parts) > 1 else ""
            suggestions[figure_id] = description
        
        return suggestions
    
    def _smart_truncate(self, content: str, max_length: int) -> str:
        """Intelligently truncate content keeping important sections"""
        if len(content) <= max_length:
            return content
        
        # Try to keep: abstract, intro, method, conclusion
        sections = []
        
        # Find abstract
        abstract_match = re.search(
            r'(?:^#*\s*abstract|abstract\s*$)(.*?)(?=^#|\Z)',
            content, re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        if abstract_match:
            sections.append(("Abstract", abstract_match.group(0)[:5000]))
        
        # Find introduction
        intro_match = re.search(
            r'(?:^#*\s*(?:1\.?\s*)?introduction)(.*?)(?=^#|\Z)',
            content, re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        if intro_match:
            sections.append(("Introduction", intro_match.group(0)[:15000]))
        
        # Find method section
        method_match = re.search(
            r'(?:^#*\s*(?:\d\.?\s*)?(?:method|approach|proposed))(.*?)(?=^#|\Z)',
            content, re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        if method_match:
            sections.append(("Method", method_match.group(0)))
        
        # Find experiments
        exp_match = re.search(
            r'(?:^#*\s*(?:\d\.?\s*)?experiment)(.*?)(?=^#|\Z)',
            content, re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        if exp_match:
            sections.append(("Experiments", exp_match.group(0)[:30000]))
        
        # Find conclusion
        concl_match = re.search(
            r'(?:^#*\s*(?:\d\.?\s*)?conclusion)(.*?)(?=^#|\Z)',
            content, re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        if concl_match:
            sections.append(("Conclusion", concl_match.group(0)[:8000]))
        
        # Combine sections
        if sections:
            truncated = "\n\n".join(
                f"## {name}\n{text}" for name, text in sections
            )
            return truncated[:max_length]
        
        # Fallback: just truncate
        return content[:max_length]
    
    def _extract_method_section(self, content: str) -> str:
        """Extract the method/approach section from content"""
        method_match = re.search(
            r'(?:^#*\s*(?:\d\.?\s*)?(?:method|approach|proposed|our|model))(.*?)(?=^#\s*(?:\d\.?\s*)?(?:experiment|result|evaluation)|\Z)',
            content, re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        
        if method_match:
            return method_match.group(0)
        
        # Return middle portion as fallback
        mid = len(content) // 3
        return content[mid:mid*2]
    
    def describe_image(
        self,
        image_path: str,
        context: str = ""
    ) -> str:
        """
        Generate description for an image using vision model.
        Only works with GPT-4V/GPT-4o.
        """
        if "gpt-4" not in self.model.lower():
            return "(Image description requires GPT-4V model)"
        
        import base64
        
        # Encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Determine media type
        ext = Path(image_path).suffix.lower()
        media_type = "image/png" if ext == ".png" else "image/jpeg"
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": IMAGE_CAPTION_PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}"
                        }
                    }
                ]
            }
        ]
        
        try:
            return self._call_llm(messages, max_tokens=500)
        except Exception as e:
            console.print(f"[yellow]Warning: Image description failed: {e}[/yellow]")
            return ""
