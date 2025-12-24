"""Baidu Search Tool for PraisonAI Agents.

Search using Baidu.

Usage:
    from praisonai_tools import BaiduSearchTool
    
    baidu = BaiduSearchTool()
    results = baidu.search("AI news")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class BaiduSearchTool(BaseTool):
    """Tool for Baidu search."""
    
    name = "baidu_search"
    description = "Search using Baidu."
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        num: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "search":
            return self.search(query=query, num=num)
        return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, num: int = 10) -> List[Dict[str, Any]]:
        """Search Baidu."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            return [{"error": "requests and beautifulsoup4 required"}]
        
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            params = {"wd": query, "rn": num}
            resp = requests.get("https://www.baidu.com/s", headers=headers, params=params, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            results = []
            for item in soup.select(".result")[:num]:
                title_el = item.select_one("h3 a")
                if title_el:
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "url": title_el.get("href", ""),
                        "snippet": item.select_one(".c-abstract").get_text(strip=True) if item.select_one(".c-abstract") else "",
                    })
            return results
        except Exception as e:
            logger.error(f"Baidu search error: {e}")
            return [{"error": str(e)}]


def baidu_search(query: str, num: int = 10) -> List[Dict[str, Any]]:
    """Search with Baidu."""
    return BaiduSearchTool().search(query=query, num=num)
