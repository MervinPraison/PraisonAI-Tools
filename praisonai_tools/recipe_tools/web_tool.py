"""
Web Tool - URL fetching and content extraction.

Provides:
- Fetching web pages
- Extracting article content (readability-style)
- Parsing sitemaps
- Respecting robots.txt
"""

import logging
import re
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import sys
import os as _os
_dir = _os.path.dirname(_os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

try:
    from .base import RecipeToolBase
except ImportError:
    from base import RecipeToolBase

logger = logging.getLogger(__name__)

# Try to import requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

# Try to import BeautifulSoup
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None


@dataclass
class WebContent:
    """Content extracted from a web page."""
    url: str
    title: str
    content: str  # Main content as text
    html: str  # Raw HTML
    markdown: str = ""  # Content as markdown
    author: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None
    images: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    status_code: int = 200
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "author": self.author,
            "date": self.date,
            "description": self.description,
            "image_count": len(self.images),
            "link_count": len(self.links),
            "status_code": self.status_code,
        }


class WebTool(RecipeToolBase):
    """
    Web content fetching and extraction tool.
    
    Provides URL fetching, article extraction, and sitemap parsing.
    """
    
    name = "web_tool"
    description = "URL fetching and content extraction"
    
    # Rate limiting
    _last_request_time: Dict[str, float] = {}
    _rate_limit_seconds: float = 1.0
    
    def __init__(self, verbose: bool = False, user_agent: str = None):
        super().__init__(verbose)
        self.user_agent = user_agent or "PraisonAI/1.0 (https://praison.ai)"
        self._robots_cache: Dict[str, urllib.robotparser.RobotFileParser] = {}
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check for requests and beautifulsoup4."""
        return {
            "requests": REQUESTS_AVAILABLE,
            "beautifulsoup4": BS4_AVAILABLE,
        }
    
    def _require_requests(self):
        """Ensure requests is available."""
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests is required. Install with: pip install requests")
    
    def _require_bs4(self):
        """Ensure BeautifulSoup is available."""
        if not BS4_AVAILABLE:
            raise ImportError("beautifulsoup4 is required. Install with: pip install beautifulsoup4")
    
    def _rate_limit(self, domain: str):
        """Apply rate limiting per domain."""
        now = time.time()
        last_time = self._last_request_time.get(domain, 0)
        wait_time = self._rate_limit_seconds - (now - last_time)
        
        if wait_time > 0:
            time.sleep(wait_time)
        
        self._last_request_time[domain] = time.time()
    
    def _get_robots_parser(self, url: str) -> urllib.robotparser.RobotFileParser:
        """Get robots.txt parser for a URL."""
        parsed = urllib.parse.urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        if robots_url not in self._robots_cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
            except Exception:
                pass  # Ignore robots.txt errors
            self._robots_cache[robots_url] = rp
        
        return self._robots_cache[robots_url]
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        rp = self._get_robots_parser(url)
        return rp.can_fetch(self.user_agent, url)
    
    def fetch(
        self,
        url: str,
        timeout: int = 30,
        respect_robots: bool = True,
    ) -> WebContent:
        """
        Fetch a web page.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            respect_robots: Whether to respect robots.txt
            
        Returns:
            WebContent with page data
        """
        self._require_requests()
        self._require_bs4()
        
        # Check robots.txt
        if respect_robots and not self.can_fetch(url):
            raise PermissionError(f"robots.txt disallows fetching: {url}")
        
        # Rate limit
        parsed = urllib.parse.urlparse(url)
        self._rate_limit(parsed.netloc)
        
        # Fetch
        headers = {"User-Agent": self.user_agent}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()
        
        # Extract meta info
        description = None
        author = None
        date = None
        
        for meta in soup.find_all("meta"):
            name = meta.get("name", "").lower()
            prop = meta.get("property", "").lower()
            content = meta.get("content", "")
            
            if name == "description" or prop == "og:description":
                description = content
            elif name == "author":
                author = content
            elif name in ("date", "article:published_time") or prop == "article:published_time":
                date = content
        
        # Extract main content
        content = self._extract_content(soup)
        
        # Extract images
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src:
                images.append(urllib.parse.urljoin(url, src))
        
        # Extract links
        links = []
        for a in soup.find_all("a"):
            href = a.get("href")
            if href and href.startswith("http"):
                links.append(href)
        
        # Convert to markdown
        markdown = self._html_to_markdown(soup)
        
        return WebContent(
            url=url,
            title=title,
            content=content,
            html=html,
            markdown=markdown,
            author=author,
            date=date,
            description=description,
            images=images[:50],  # Limit images
            links=links[:100],  # Limit links
            status_code=response.status_code,
        )
    
    def _extract_content(self, soup: "BeautifulSoup") -> str:
        """Extract main content from page (readability-style)."""
        # Remove script, style, nav, header, footer
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        
        # Try to find article or main content
        content_tags = soup.find_all(["article", "main", "[role='main']"])
        if content_tags:
            return " ".join(tag.get_text(separator=" ", strip=True) for tag in content_tags)
        
        # Fall back to body
        body = soup.find("body")
        if body:
            return body.get_text(separator=" ", strip=True)
        
        return soup.get_text(separator=" ", strip=True)
    
    def _html_to_markdown(self, soup: "BeautifulSoup") -> str:
        """Convert HTML to basic markdown."""
        # Remove unwanted tags
        for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        
        lines = []
        
        # Find main content area
        main = soup.find(["article", "main"]) or soup.find("body") or soup
        
        for element in main.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "pre", "blockquote"]):
            tag_name = element.name
            text = element.get_text(strip=True)
            
            if not text:
                continue
            
            if tag_name == "h1":
                lines.append(f"# {text}\n")
            elif tag_name == "h2":
                lines.append(f"## {text}\n")
            elif tag_name == "h3":
                lines.append(f"### {text}\n")
            elif tag_name in ("h4", "h5", "h6"):
                lines.append(f"#### {text}\n")
            elif tag_name == "p":
                lines.append(f"{text}\n")
            elif tag_name in ("ul", "ol"):
                for li in element.find_all("li", recursive=False):
                    li_text = li.get_text(strip=True)
                    lines.append(f"- {li_text}")
                lines.append("")
            elif tag_name == "pre":
                lines.append(f"```\n{text}\n```\n")
            elif tag_name == "blockquote":
                lines.append(f"> {text}\n")
        
        return "\n".join(lines)
    
    def extract_article(
        self,
        url: str,
        output_path: Optional[Union[str, Path]] = None,
        include_images: bool = True,
    ) -> WebContent:
        """
        Extract article content from URL and optionally save.
        
        Args:
            url: URL to extract from
            output_path: Path to save markdown (optional)
            include_images: Download and include images
            
        Returns:
            WebContent with extracted article
        """
        content = self.fetch(url)
        
        if output_path:
            output_path = Path(output_path)
            self._ensure_output_dir(output_path.parent)
            
            # Write markdown
            output_path.write_text(content.markdown, encoding="utf-8")
            
            # Download images if requested
            if include_images and content.images:
                images_dir = output_path.parent / "images"
                self._ensure_output_dir(images_dir)
                
                for i, img_url in enumerate(content.images[:20]):  # Limit to 20 images
                    try:
                        self._download_image(img_url, images_dir / f"image_{i:03d}.jpg")
                    except Exception as e:
                        logger.warning(f"Failed to download image {img_url}: {e}")
        
        return content
    
    def _download_image(self, url: str, path: Path):
        """Download an image."""
        self._require_requests()
        
        response = requests.get(url, timeout=30, headers={"User-Agent": self.user_agent})
        response.raise_for_status()
        
        path.write_bytes(response.content)
    
    def fetch_sitemap(
        self,
        url: str,
        limit: int = 100,
    ) -> List[str]:
        """
        Fetch and parse a sitemap.
        
        Args:
            url: Sitemap URL (or base URL to find sitemap)
            limit: Maximum URLs to return
            
        Returns:
            List of URLs from sitemap
        """
        self._require_requests()
        self._require_bs4()
        
        # If not a sitemap URL, try to find it
        if not url.endswith(".xml"):
            parsed = urllib.parse.urlparse(url)
            url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
        
        headers = {"User-Agent": self.user_agent}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "xml")
        
        urls = []
        
        # Check for sitemap index
        sitemaps = soup.find_all("sitemap")
        if sitemaps:
            # It's a sitemap index, fetch child sitemaps
            for sitemap in sitemaps[:5]:  # Limit child sitemaps
                loc = sitemap.find("loc")
                if loc:
                    child_urls = self.fetch_sitemap(loc.get_text(), limit=limit // 5)
                    urls.extend(child_urls)
                    if len(urls) >= limit:
                        break
        else:
            # Regular sitemap
            for url_tag in soup.find_all("url"):
                loc = url_tag.find("loc")
                if loc:
                    urls.append(loc.get_text())
                    if len(urls) >= limit:
                        break
        
        return urls[:limit]
    
    def batch_fetch(
        self,
        urls: List[str],
        output_dir: Optional[Union[str, Path]] = None,
        delay: float = 1.0,
    ) -> List[WebContent]:
        """
        Fetch multiple URLs with rate limiting.
        
        Args:
            urls: List of URLs to fetch
            output_dir: Directory to save content
            delay: Delay between requests
            
        Returns:
            List of WebContent objects
        """
        results = []
        
        if output_dir:
            output_dir = Path(output_dir)
            self._ensure_output_dir(output_dir)
        
        for i, url in enumerate(urls):
            try:
                content = self.fetch(url)
                results.append(content)
                
                if output_dir:
                    # Save as markdown
                    safe_name = re.sub(r'[^\w\-]', '_', urllib.parse.urlparse(url).path)[:50]
                    output_path = output_dir / f"{i:03d}_{safe_name}.md"
                    output_path.write_text(content.markdown, encoding="utf-8")
                
                logger.info(f"Fetched {i+1}/{len(urls)}: {url}")
                
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
            
            if i < len(urls) - 1:
                time.sleep(delay)
        
        return results


# Convenience functions
def web_fetch(
    url: str,
    timeout: int = 30,
    verbose: bool = False,
) -> WebContent:
    """Fetch a web page."""
    return WebTool(verbose=verbose).fetch(url, timeout)


def web_extract_article(
    url: str,
    output_path: Optional[Union[str, Path]] = None,
    verbose: bool = False,
) -> WebContent:
    """Extract article from URL."""
    return WebTool(verbose=verbose).extract_article(url, output_path)


def web_fetch_sitemap(
    url: str,
    limit: int = 100,
    verbose: bool = False,
) -> List[str]:
    """Fetch sitemap URLs."""
    return WebTool(verbose=verbose).fetch_sitemap(url, limit)
