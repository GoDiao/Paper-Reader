"""
Services Module - External API Integrations

Provides web search services for reproduction resources:
- GitHub Search API
- HuggingFace Model/Dataset Search
- Resource Finder (aggregation)
- Tavily Deep Research
"""

from .github_search import GitHubSearchClient, GitHubRepo
from .huggingface_search import HuggingFaceClient, HFResource
from .resource_finder import ResourceFinder, ReproductionResources
from .tavily_service import TavilyService, TavilyServiceError
from .valyu_service import ValyuService, ValyuServiceError
from .deep_research_errors import DeepResearchServiceError

__all__ = [
    'GitHubSearchClient',
    'GitHubRepo',
    'HuggingFaceClient',
    'HFResource',
    'ResourceFinder',
    'ReproductionResources',
    'TavilyService',
    'TavilyServiceError',
    'ValyuService',
    'ValyuServiceError',
    'DeepResearchServiceError',
]
