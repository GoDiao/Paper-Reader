"""
HuggingFace API Client

Searches for models and datasets on HuggingFace Hub.
API Documentation: https://huggingface.co/docs/hub/api
"""

import aiohttp
import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class HFResource:
    """HuggingFace resource (model or dataset)"""
    resource_type: str  # "model" or "dataset"
    id: str             # owner/name
    downloads: int
    likes: int
    url: str
    tags: List[str] = None
    description: str = ""
    last_modified: str = ""
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class HuggingFaceClient:
    """HuggingFace Hub API client for searching models and datasets"""
    
    BASE_URL = "https://huggingface.co/api"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize HuggingFace client.
        
        Args:
            token: HuggingFace API token (optional, for private resources)
        """
        self.token = token
        self.headers = {
            "User-Agent": "Paper-Reader-Agent/1.0"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    async def search_models(
        self, 
        query: str, 
        limit: int = 5,
        tags: List[str] = None
    ) -> List[HFResource]:
        """
        Search for models on HuggingFace Hub.
        
        Args:
            query: Search query (paper title or method name)
            limit: Maximum results to return
            tags: Optional filter tags (e.g., ["pytorch", "text-generation"])
            
        Returns:
            List of HFResource objects
        """
        logger.info(f"Searching HuggingFace models for: {query}")
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/models"
                params = {
                    "search": query,
                    "limit": limit,
                    "full": "true"
                }
                
                if tags:
                    params["filter"] = ",".join(tags)
                
                async with session.get(
                    url, 
                    params=params, 
                    headers=self.headers
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"HuggingFace API error: {resp.status}")
                        return []
                    
                    data = await resp.json()
                
                # Handle response format
                if isinstance(data, dict) and "models" in data:
                    items = data["models"]
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                
                logger.info(f"Found {len(items)} HuggingFace models")
                
                return [
                    HFResource(
                        resource_type="model",
                        id=item.get("id", item.get("modelId", "unknown")),
                        downloads=item.get("downloads", 0),
                        likes=item.get("likes", 0),
                        url=f"https://huggingface.co/{item.get('id', item.get('modelId', ''))}",
                        tags=item.get("tags", []),
                        description=item.get("cardData", {}).get("description", ""),
                        last_modified=item.get("lastModified", "")
                    )
                    for item in items
                ]
                
        except aiohttp.ClientError as e:
            logger.error(f"HuggingFace search network error: {e}")
            return []
        except Exception as e:
            logger.error(f"HuggingFace search error: {e}")
            return []
    
    async def search_datasets(
        self, 
        query: str, 
        limit: int = 5
    ) -> List[HFResource]:
        """
        Search for datasets on HuggingFace Hub.
        
        Args:
            query: Search query (dataset name or paper title)
            limit: Maximum results to return
            
        Returns:
            List of HFResource objects
        """
        logger.info(f"Searching HuggingFace datasets for: {query}")
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/datasets"
                params = {
                    "search": query,
                    "limit": limit,
                    "full": "true"
                }
                
                async with session.get(
                    url, 
                    params=params, 
                    headers=self.headers
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"HuggingFace API error: {resp.status}")
                        return []
                    
                    data = await resp.json()
                
                # Handle response format
                if isinstance(data, dict) and "datasets" in data:
                    items = data["datasets"]
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                
                logger.info(f"Found {len(items)} HuggingFace datasets")
                
                return [
                    HFResource(
                        resource_type="dataset",
                        id=item.get("id", item.get("id", "unknown")),
                        downloads=item.get("downloads", 0),
                        likes=item.get("likes", 0),
                        url=f"https://huggingface.co/datasets/{item.get('id', '')}",
                        tags=item.get("tags", []),
                        description=item.get("cardData", {}).get("description", ""),
                        last_modified=item.get("lastModified", "")
                    )
                    for item in items
                ]
                
        except aiohttp.ClientError as e:
            logger.error(f"HuggingFace dataset search network error: {e}")
            return []
        except Exception as e:
            logger.error(f"HuggingFace dataset search error: {e}")
            return []
    
    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific model.
        
        Args:
            model_id: Model ID (owner/name)
            
        Returns:
            Model info dict or None
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/models/{model_id}"
                
                async with session.get(url, headers=self.headers) as resp:
                    if resp.status != 200:
                        return None
                    
                    return await resp.json()
                    
        except Exception as e:
            logger.error(f"Error fetching model info: {e}")
            return None
    
    async def get_dataset_info(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific dataset.
        
        Args:
            dataset_id: Dataset ID (owner/name)
            
        Returns:
            Dataset info dict or None
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/datasets/{dataset_id}"
                
                async with session.get(url, headers=self.headers) as resp:
                    if resp.status != 200:
                        return None
                    
                    return await resp.json()
                    
        except Exception as e:
            logger.error(f"Error fetching dataset info: {e}")
            return None
    
    async def search_paper_resources(
        self,
        paper_title: str,
        datasets: List[str] = None
    ) -> Dict[str, List[HFResource]]:
        """
        Search for all resources related to a paper.
        
        Args:
            paper_title: Paper title
            datasets: List of dataset names mentioned in paper
            
        Returns:
            Dict with "models" and "datasets" keys
        """
        results = {
            "models": [],
            "datasets": []
        }
        
        # Search models
        models = await self.search_models(paper_title)
        results["models"] = models
        
        # Search datasets mentioned in paper
        if datasets:
            for ds_name in datasets[:3]:  # Limit to 3 datasets
                ds_results = await self.search_datasets(ds_name)
                results["datasets"].extend(ds_results)
        
        # Also search paper title for datasets
        title_datasets = await self.search_datasets(paper_title, limit=3)
        results["datasets"].extend(title_datasets)
        
        # Deduplicate datasets by ID
        seen_ids = set()
        unique_datasets = []
        for ds in results["datasets"]:
            if ds.id not in seen_ids:
                seen_ids.add(ds.id)
                unique_datasets.append(ds)
        results["datasets"] = unique_datasets
        
        return results


# Synchronous wrapper for convenience
def search_huggingface_sync(
    paper_title: str, 
    token: str = None
) -> Dict[str, List[HFResource]]:
    """Synchronous wrapper for HuggingFace search"""
    client = HuggingFaceClient(token)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            client.search_paper_resources(paper_title)
        )
    finally:
        loop.close()
