"""
Services Module - External API Integrations

Provides web search services for reproduction resources:
- GitHub Search API
- HuggingFace Model/Dataset Search
- Resource Finder (aggregation)
"""

from .github_search import GitHubSearchClient, GitHubRepo
from .huggingface_search import HuggingFaceClient, HFResource
from .resource_finder import ResourceFinder, ReproductionResources

__all__ = [
    'GitHubSearchClient',
    'GitHubRepo',
    'HuggingFaceClient',
    'HFResource',
    'ResourceFinder',
    'ReproductionResources',
]
