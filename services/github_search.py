"""
GitHub Search API Client

Searches for paper-related code repositories using GitHub's search API.
Rate limits:
- Without token: 60 requests/hour
- With token: 5000 requests/hour
"""

import aiohttp
import asyncio
from typing import List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class GitHubRepo:
    """GitHub repository information"""
    full_name: str        # owner/repo
    description: str
    stars: int
    url: str
    language: str
    forks: int = 0
    updated_at: str = ""
    

class GitHubSearchClient:
    """GitHub Search API client for finding paper code repositories"""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub search client.
        
        Args:
            token: GitHub Personal Access Token (optional, increases rate limit)
        """
        self.token = token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Paper-Reader-Agent/1.0"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
    
    async def search_paper_code(
        self, 
        paper_title: str, 
        authors: str = "",
        max_results: int = 5
    ) -> List[GitHubRepo]:
        """
        Search for code repositories related to a paper.
        
        Args:
            paper_title: Title of the paper
            authors: Author names (optional, helps refine search)
            max_results: Maximum number of results to return
            
        Returns:
            List of GitHubRepo objects
        """
        # Build search query
        query = self._build_search_query(paper_title, authors)
        
        logger.info(f"Searching GitHub for: {query}")
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/search/repositories"
                params = {
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": max_results
                }
                
                async with session.get(
                    url, 
                    params=params, 
                    headers=self.headers
                ) as resp:
                    if resp.status == 403:
                        logger.warning("GitHub API rate limit exceeded")
                        return []
                    
                    if resp.status != 200:
                        logger.error(f"GitHub API error: {resp.status}")
                        return []
                    
                    data = await resp.json()
                    
                items = data.get("items", [])
                logger.info(f"Found {len(items)} GitHub repositories")
                
                return [
                    GitHubRepo(
                        full_name=item["full_name"],
                        description=item.get("description", "") or "",
                        stars=item["stargazers_count"],
                        url=item["html_url"],
                        language=item.get("language", "") or "",
                        forks=item.get("forks_count", 0),
                        updated_at=item.get("updated_at", "")
                    )
                    for item in items
                ]
                
        except aiohttp.ClientError as e:
            logger.error(f"GitHub search network error: {e}")
            return []
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
            return []
    
    def _build_search_query(self, paper_title: str, authors: str) -> str:
        """
        Build a GitHub search query from paper info.
        
        Strategy:
        1. Use paper title (cleaned)
        2. Add first author surname if available
        3. Add relevant keywords
        """
        # Clean paper title
        title = paper_title.strip()
        
        # Remove common filler words
        filler_words = ["a ", "an ", "the ", "on ", "for ", "with ", "using "]
        for word in filler_words:
            if title.lower().startswith(word):
                title = title[len(word):]
        
        # Build base query
        query_parts = [f'"{title}"']
        
        # Add author if available
        if authors:
            # Extract first author's last name
            first_author = authors.split(",")[0].strip() if "," in authors else authors
            last_name = first_author.split()[-1] if " " in first_author else first_author
            if last_name and len(last_name) > 2:
                query_parts.append(last_name)
        
        # Combine
        query = " ".join(query_parts)
        
        return query
    
    async def get_repo_info(self, owner: str, repo: str) -> Optional[dict]:
        """
        Get detailed information about a specific repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Repository info dict or None
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/repos/{owner}/{repo}"
                
                async with session.get(url, headers=self.headers) as resp:
                    if resp.status != 200:
                        return None
                    
                    return await resp.json()
                    
        except Exception as e:
            logger.error(f"Error fetching repo info: {e}")
            return None
    
    async def check_repo_exists(self, url: str) -> bool:
        """
        Check if a GitHub repository URL exists.
        
        Args:
            url: Full GitHub URL (e.g., https://github.com/owner/repo)
            
        Returns:
            True if repo exists, False otherwise
        """
        try:
            # Extract owner/repo from URL
            parts = url.rstrip("/").split("/")
            if len(parts) >= 2:
                owner, repo = parts[-2], parts[-1]
            else:
                return False
            
            async with aiohttp.ClientSession() as session:
                api_url = f"{self.BASE_URL}/repos/{owner}/{repo}"
                
                async with session.get(api_url, headers=self.headers) as resp:
                    return resp.status == 200
                    
        except Exception:
            return False


# Synchronous wrapper for convenience
def search_github_sync(paper_title: str, authors: str = "", token: str = None) -> List[GitHubRepo]:
    """Synchronous wrapper for GitHub search"""
    client = GitHubSearchClient(token)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            client.search_paper_code(paper_title, authors)
        )
    finally:
        loop.close()
