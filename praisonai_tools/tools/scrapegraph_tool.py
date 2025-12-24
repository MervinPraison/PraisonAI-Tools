"""ScrapeGraph Tool for PraisonAI Agents.

AI-powered web scraping using ScrapeGraph.

Usage:
    from praisonai_tools import ScrapeGraphTool
    
    sg = ScrapeGraphTool()
    content = sg.scrape("https://example.com", "Extract product prices")
"""

import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ScrapeGraphTool(BaseTool):
    """Tool for ScrapeGraph AI scraping."""
    
    name = "scrapegraph"
    description = "AI-powered web scraping using ScrapeGraph."
    
    def run(
        self,
        action: str = "scrape",
        url: Optional[str] = None,
        prompt: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "scrape":
            return self.scrape(url=url, prompt=prompt)
        return {"error": f"Unknown action: {action}"}
    
    def scrape(self, url: str, prompt: str = "Extract the main content") -> Dict[str, Any]:
        """Scrape with AI extraction."""
        if not url:
            return {"error": "url is required"}
        
        try:
            from scrapegraphai.graphs import SmartScraperGraph
        except ImportError:
            return {"error": "scrapegraphai not installed. Install with: pip install scrapegraphai"}
        
        try:
            graph = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config={"llm": {"model": "openai/gpt-4o-mini"}},
            )
            result = graph.run()
            return {"url": url, "result": result}
        except Exception as e:
            logger.error(f"ScrapeGraph error: {e}")
            return {"error": str(e)}


def scrapegraph_scrape(url: str, prompt: str = "Extract the main content") -> Dict[str, Any]:
    """Scrape with ScrapeGraph."""
    return ScrapeGraphTool().scrape(url=url, prompt=prompt)
