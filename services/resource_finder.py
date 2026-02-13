"""
Resource Finder Service

Aggregates search results from multiple sources (GitHub, HuggingFace)
to find reproduction resources for academic papers.
"""

import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import logging

from .github_search import GitHubSearchClient, GitHubRepo
from .huggingface_search import HuggingFaceClient, HFResource

logger = logging.getLogger(__name__)


@dataclass
class ReproductionResources:
    """Aggregated reproduction resources for a paper"""
    github_repos: List[Dict] = field(default_factory=list)
    hf_models: List[Dict] = field(default_factory=list)
    hf_datasets: List[Dict] = field(default_factory=list)
    search_links: Dict[str, str] = field(default_factory=dict)
    confidence: str = "low"  # "high", "medium", "low"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "github_repos": self.github_repos,
            "hf_models": self.hf_models,
            "hf_datasets": self.hf_datasets,
            "search_links": self.search_links,
            "confidence": self.confidence
        }


class ResourceFinder:
    """
    Finds reproduction resources for academic papers.
    
    Searches multiple sources:
    - GitHub: Code repositories
    - HuggingFace: Models and datasets
    """
    
    def __init__(
        self,
        enable_web: bool = False,
        github_token: Optional[str] = None,
        huggingface_token: Optional[str] = None
    ):
        """
        Initialize ResourceFinder.
        
        Args:
            enable_web: Whether to enable web searches
            github_token: GitHub Personal Access Token
            huggingface_token: HuggingFace API token
        """
        self.enable_web = enable_web
        self.github = GitHubSearchClient(github_token) if enable_web else None
        self.hf = HuggingFaceClient(huggingface_token) if enable_web else None
    
    async def find_resources(
        self,
        paper_title: str,
        authors: str = "",
        datasets: List[str] = None
    ) -> ReproductionResources:
        """
        Find all reproduction resources for a paper.
        
        Args:
            paper_title: Paper title
            authors: Author names (comma-separated)
            datasets: List of dataset names mentioned in paper
            
        Returns:
            ReproductionResources object with all found resources
        """
        if not self.enable_web:
            logger.info("Web search disabled, returning empty resources")
            return ReproductionResources()
        
        resources = ReproductionResources()
        
        # Run all searches in parallel
        tasks = []
        
        # GitHub search
        if self.github:
            tasks.append(self._search_github(paper_title, authors))
        
        # HuggingFace search
        if self.hf:
            tasks.append(self._search_huggingface(paper_title, datasets))
        
        # Execute all searches
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Search error: {result}")
                elif isinstance(result, dict):
                    if "github" in result:
                        resources.github_repos = result["github"]
                        if result["github"]:
                            resources.confidence = "high"
                    if "models" in result:
                        resources.hf_models = result["models"]
                    if "datasets" in result:
                        resources.hf_datasets = result["datasets"]
        
        # Build manual search links
        resources.search_links = self._build_search_links(paper_title, authors)
        
        logger.info(
            f"Found resources: {len(resources.github_repos)} repos, "
            f"{len(resources.hf_models)} models, "
            f"{len(resources.hf_datasets)} datasets"
        )
        
        return resources
    
    async def _search_github(
        self, 
        paper_title: str, 
        authors: str
    ) -> Dict[str, List[Dict]]:
        """Search GitHub for code repositories"""
        try:
            repos = await self.github.search_paper_code(paper_title, authors)
            
            return {
                "github": [
                    {
                        "full_name": repo.full_name,
                        "description": repo.description,
                        "stars": repo.stars,
                        "url": repo.url,
                        "language": repo.language,
                        "forks": repo.forks,
                        "updated_at": repo.updated_at
                    }
                    for repo in repos
                ]
            }
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
            return {"github": []}
    
    async def _search_huggingface(
        self,
        paper_title: str,
        datasets: List[str] = None
    ) -> Dict[str, List[Dict]]:
        """Search HuggingFace for models and datasets"""
        try:
            results = await self.hf.search_paper_resources(paper_title, datasets)
            
            return {
                "models": [
                    {
                        "id": m.id,
                        "downloads": m.downloads,
                        "likes": m.likes,
                        "url": m.url,
                        "tags": m.tags[:5] if m.tags else [],  # Limit tags
                        "description": m.description[:200] if m.description else ""
                    }
                    for m in results.get("models", [])
                ],
                "datasets": [
                    {
                        "id": d.id,
                        "downloads": d.downloads,
                        "likes": d.likes,
                        "url": d.url,
                        "tags": d.tags[:5] if d.tags else [],
                        "description": d.description[:200] if d.description else ""
                    }
                    for d in results.get("datasets", [])
                ]
            }
        except Exception as e:
            logger.error(f"HuggingFace search error: {e}")
            return {"models": [], "datasets": []}
    
    def _build_search_links(self, paper_title: str, authors: str) -> Dict[str, str]:
        """Build manual search links for user reference"""
        import urllib.parse
        
        # URL encode the query
        encoded_title = urllib.parse.quote(paper_title)
        
        links = {
            "github": f"https://github.com/search?q={encoded_title}&type=repositories",
            "huggingface_models": f"https://huggingface.co/models?search={encoded_title}",
            "huggingface_datasets": f"https://huggingface.co/datasets?search={encoded_title}",
            "google_scholar": f"https://scholar.google.com/scholar?q={encoded_title}",
            "semantic_scholar": f"https://www.semanticscholar.org/search?q={encoded_title}"
        }
        
        # Add author-specific GitHub search
        if authors:
            first_author = authors.split(",")[0].strip() if "," in authors else authors
            last_name = first_author.split()[-1] if " " in first_author else first_author
            links["github_author"] = f"https://github.com/search?q={encoded_title}+{last_name}&type=repositories"
        
        return links
    
    async def enrich_checklist(
        self,
        checklist: Dict,
        paper_title: str,
        authors: str = ""
    ) -> Dict:
        """
        Enrich a reproduction checklist with web-found resources.
        
        Args:
            checklist: Existing reproduction checklist dict
            paper_title: Paper title
            authors: Author names
            
        Returns:
            Enriched checklist dict
        """
        if not self.enable_web:
            return checklist
        
        resources = await self.find_resources(paper_title, authors)
        
        # Enrich code availability
        if resources.github_repos and "code_availability" in checklist:
            code_avail = checklist["code_availability"]
            
            # Check if we found official-looking repos
            for repo in resources.github_repos[:3]:
                repo_name = repo["full_name"].lower()
                
                # Check if repo name matches paper title keywords
                title_words = [w.lower() for w in paper_title.split() if len(w) > 3]
                matches = sum(1 for w in title_words if w in repo_name)
                
                if matches >= 2 or repo["stars"] > 100:
                    # Likely an official or popular implementation
                    if "official_code" not in code_avail or code_avail.get("official_code", {}).get("status", "") == "❓ Not mentioned":
                        code_avail["official_code"] = {
                            "status": "🔍 Found",
                            "link": repo["url"],
                            "stars": repo["stars"],
                            "confidence": "high" if matches >= 2 else "medium"
                        }
                    break
        
        # Enrich dataset links
        if resources.hf_datasets and "datasets" in checklist:
            for ds in checklist["datasets"]:
                ds_name = ds.get("dataset", ds.get("name", "")).lower()
                
                # Try to match with HuggingFace datasets
                for hf_ds in resources.hf_datasets:
                    if ds_name in hf_ds["id"].lower() or hf_ds["id"].lower() in ds_name:
                        if not ds.get("download_link"):
                            ds["download_link"] = hf_ds["url"]
                            ds["hf_id"] = hf_ds["id"]
                            ds["hf_downloads"] = hf_ds["downloads"]
                        break
        
        # Add search links to checklist
        checklist["search_links"] = resources.search_links
        
        return checklist


# Convenience function
async def find_paper_resources(
    paper_title: str,
    authors: str = "",
    datasets: List[str] = None,
    github_token: str = None,
    huggingface_token: str = None
) -> Dict:
    """
    Convenience function to find paper resources.
    
    Args:
        paper_title: Paper title
        authors: Author names
        datasets: List of dataset names
        github_token: GitHub token
        huggingface_token: HuggingFace token
        
    Returns:
        Dict with resources
    """
    finder = ResourceFinder(
        enable_web=True,
        github_token=github_token,
        huggingface_token=huggingface_token
    )
    
    resources = await finder.find_resources(paper_title, authors, datasets)
    return resources.to_dict()
