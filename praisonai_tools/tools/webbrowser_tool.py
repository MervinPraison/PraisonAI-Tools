"""WebBrowser Tool for PraisonAI Agents.

Browser automation using Playwright.

Usage:
    from praisonai_tools import WebBrowserTool
    
    browser = WebBrowserTool()
    content = browser.get_page("https://example.com")
"""

import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WebBrowserTool(BaseTool):
    """Tool for web browser automation."""
    
    name = "webbrowser"
    description = "Browser automation using Playwright."
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        super().__init__()
    
    def run(
        self,
        action: str = "get_page",
        url: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        
        if action == "get_page":
            return self.get_page(url=url)
        elif action == "screenshot":
            return self.screenshot(url=url, output_path=kwargs.get("output_path"))
        elif action == "click":
            return self.click(url=url, selector=kwargs.get("selector"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get_page(self, url: str) -> Dict[str, Any]:
        """Get page content."""
        if not url:
            return {"error": "url is required"}
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {"error": "playwright not installed. Install with: pip install playwright && playwright install"}
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                page.goto(url)
                content = page.content()
                title = page.title()
                browser.close()
                return {"url": url, "title": title, "content": content[:10000]}
        except Exception as e:
            logger.error(f"WebBrowser get_page error: {e}")
            return {"error": str(e)}
    
    def screenshot(self, url: str, output_path: str = "screenshot.png") -> Dict[str, Any]:
        """Take screenshot."""
        if not url:
            return {"error": "url is required"}
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {"error": "playwright not installed"}
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                page.goto(url)
                page.screenshot(path=output_path)
                browser.close()
                return {"success": True, "output_path": output_path}
        except Exception as e:
            logger.error(f"WebBrowser screenshot error: {e}")
            return {"error": str(e)}
    
    def click(self, url: str, selector: str) -> Dict[str, Any]:
        """Click element on page."""
        if not url or not selector:
            return {"error": "url and selector are required"}
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {"error": "playwright not installed"}
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                page.goto(url)
                page.click(selector)
                content = page.content()
                browser.close()
                return {"success": True, "content": content[:10000]}
        except Exception as e:
            logger.error(f"WebBrowser click error: {e}")
            return {"error": str(e)}


def webbrowser_get_page(url: str) -> Dict[str, Any]:
    """Get page content."""
    return WebBrowserTool().get_page(url=url)
