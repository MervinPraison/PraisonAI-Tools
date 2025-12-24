"""Wikipedia Tool for PraisonAI Agents.

Search and retrieve Wikipedia articles.

Usage:
    from praisonai_tools import WikipediaTool
    
    wiki = WikipediaTool()
    results = wiki.search("Python programming")
    article = wiki.get_page("Python (programming language)")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WikipediaTool(BaseTool):
    """Tool for searching Wikipedia."""
    
    name = "wikipedia"
    description = "Search Wikipedia and retrieve article content."
    
    def __init__(self, language: str = "en"):
        self.language = language
        super().__init__()
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        title: Optional[str] = None,
        max_results: int = 5,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query, max_results=max_results)
        elif action == "get_page":
            return self.get_page(title=title or query)
        elif action == "summary":
            return self.summary(title=title or query)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search Wikipedia."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            import wikipedia
            wikipedia.set_lang(self.language)
        except ImportError:
            return [{"error": "wikipedia not installed. Install with: pip install wikipedia"}]
        
        try:
            results = wikipedia.search(query, results=max_results)
            return [{"title": title} for title in results]
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
            return [{"error": str(e)}]
    
    def get_page(self, title: str) -> Dict[str, Any]:
        """Get full Wikipedia page."""
        if not title:
            return {"error": "title is required"}
        
        try:
            import wikipedia
            wikipedia.set_lang(self.language)
        except ImportError:
            return {"error": "wikipedia not installed"}
        
        try:
            page = wikipedia.page(title, auto_suggest=True)
            return {
                "title": page.title,
                "url": page.url,
                "summary": page.summary[:1000],
                "content": page.content[:5000],
                "categories": page.categories[:10],
            }
        except wikipedia.DisambiguationError as e:
            return {"error": "Disambiguation", "options": e.options[:10]}
        except wikipedia.PageError:
            return {"error": f"Page '{title}' not found"}
        except Exception as e:
            logger.error(f"Wikipedia get_page error: {e}")
            return {"error": str(e)}
    
    def summary(self, title: str, sentences: int = 5) -> Dict[str, Any]:
        """Get Wikipedia summary."""
        if not title:
            return {"error": "title is required"}
        
        try:
            import wikipedia
            wikipedia.set_lang(self.language)
        except ImportError:
            return {"error": "wikipedia not installed"}
        
        try:
            summary = wikipedia.summary(title, sentences=sentences, auto_suggest=True)
            return {"title": title, "summary": summary}
        except wikipedia.DisambiguationError as e:
            return {"error": "Disambiguation", "options": e.options[:10]}
        except wikipedia.PageError:
            return {"error": f"Page '{title}' not found"}
        except Exception as e:
            logger.error(f"Wikipedia summary error: {e}")
            return {"error": str(e)}


def wikipedia_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search Wikipedia."""
    return WikipediaTool().search(query=query, max_results=max_results)
