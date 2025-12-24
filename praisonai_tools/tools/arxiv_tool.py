"""ArXiv Tool for PraisonAI Agents.

Search and retrieve academic papers from ArXiv.

Usage:
    from praisonai_tools import ArxivTool
    
    arxiv = ArxivTool()
    papers = arxiv.search("machine learning")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ArxivTool(BaseTool):
    """Tool for searching ArXiv papers."""
    
    name = "arxiv"
    description = "Search and retrieve academic papers from ArXiv."
    
    def __init__(self):
        super().__init__()
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        paper_id: Optional[str] = None,
        max_results: int = 5,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query, max_results=max_results)
        elif action == "get_paper":
            return self.get_paper(paper_id=paper_id)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search ArXiv papers."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            import arxiv
        except ImportError:
            return [{"error": "arxiv not installed. Install with: pip install arxiv"}]
        
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            
            results = []
            for paper in search.results():
                results.append({
                    "id": paper.entry_id.split("/")[-1],
                    "title": paper.title,
                    "authors": [a.name for a in paper.authors[:5]],
                    "summary": paper.summary[:500],
                    "published": str(paper.published.date()),
                    "pdf_url": paper.pdf_url,
                    "categories": paper.categories,
                })
            return results
        except Exception as e:
            logger.error(f"ArXiv search error: {e}")
            return [{"error": str(e)}]
    
    def get_paper(self, paper_id: str) -> Dict[str, Any]:
        """Get paper by ID."""
        if not paper_id:
            return {"error": "paper_id is required"}
        
        try:
            import arxiv
        except ImportError:
            return {"error": "arxiv not installed"}
        
        try:
            search = arxiv.Search(id_list=[paper_id])
            paper = next(search.results(), None)
            
            if not paper:
                return {"error": f"Paper '{paper_id}' not found"}
            
            return {
                "id": paper.entry_id.split("/")[-1],
                "title": paper.title,
                "authors": [a.name for a in paper.authors],
                "summary": paper.summary,
                "published": str(paper.published.date()),
                "updated": str(paper.updated.date()),
                "pdf_url": paper.pdf_url,
                "categories": paper.categories,
                "primary_category": paper.primary_category,
            }
        except Exception as e:
            logger.error(f"ArXiv get_paper error: {e}")
            return {"error": str(e)}


def arxiv_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search ArXiv papers."""
    return ArxivTool().search(query=query, max_results=max_results)
