"""Newspaper Tool for PraisonAI Agents.

Extract articles from news websites.

Usage:
    from praisonai_tools import NewspaperTool
    
    news = NewspaperTool()
    article = news.extract("https://example.com/article")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class NewspaperTool(BaseTool):
    """Tool for extracting news articles."""
    
    name = "newspaper"
    description = "Extract articles from news websites."
    
    def run(
        self,
        action: str = "extract",
        url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        if action == "extract":
            return self.extract(url=url)
        elif action == "build_source":
            return self.build_source(url=url)
        return {"error": f"Unknown action: {action}"}
    
    def extract(self, url: str) -> Dict[str, Any]:
        """Extract article from URL."""
        if not url:
            return {"error": "url is required"}
        
        try:
            from newspaper import Article
        except ImportError:
            return {"error": "newspaper3k not installed. Install with: pip install newspaper3k"}
        
        try:
            article = Article(url)
            article.download()
            article.parse()
            article.nlp()
            
            return {
                "title": article.title,
                "authors": article.authors,
                "publish_date": str(article.publish_date) if article.publish_date else None,
                "text": article.text,
                "summary": article.summary,
                "keywords": article.keywords,
                "top_image": article.top_image,
            }
        except Exception as e:
            logger.error(f"Newspaper extract error: {e}")
            return {"error": str(e)}
    
    def build_source(self, url: str) -> List[Dict[str, Any]]:
        """Build news source and get articles."""
        if not url:
            return [{"error": "url is required"}]
        
        try:
            import newspaper
        except ImportError:
            return [{"error": "newspaper3k not installed"}]
        
        try:
            source = newspaper.build(url, memoize_articles=False)
            articles = []
            for article in source.articles[:20]:
                articles.append({"url": article.url, "title": article.title or ""})
            return articles
        except Exception as e:
            logger.error(f"Newspaper build_source error: {e}")
            return [{"error": str(e)}]


def extract_article(url: str) -> Dict[str, Any]:
    """Extract article from URL."""
    return NewspaperTool().extract(url=url)
