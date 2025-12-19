"""Tests for Tavily tools with real API calls.

These tests require TAVILY_API_KEY environment variable to be set.
Run with: pytest tests/test_tavily.py -v
"""

import pytest

# Skip all tests if tavily is not installed
pytest.importorskip("tavily")

from praisonai_tools import TavilyTools, tavily_search, tavily_extract, tavily_crawl, tavily_map


@pytest.fixture
def tavily_tools(tavily_api_key):
    """Create TavilyTools instance."""
    return TavilyTools(api_key=tavily_api_key)


class TestTavilySearch:
    """Tests for Tavily search functionality."""
    
    @pytest.mark.tavily
    def test_basic_search(self, tavily_api_key):
        """Test basic search functionality."""
        result = tavily_search("What is Python programming language?", max_results=3)
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        assert "results" in result
        assert len(result["results"]) > 0
        
        # Check result structure
        first_result = result["results"][0]
        assert "url" in first_result
        assert "title" in first_result or "content" in first_result
    
    @pytest.mark.tavily
    def test_search_with_answer(self, tavily_api_key):
        """Test search with LLM-generated answer."""
        result = tavily_search(
            "What is the capital of France?",
            include_answer=True,
            max_results=3
        )
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        assert "answer" in result
        assert len(result["answer"]) > 0
    
    @pytest.mark.tavily
    def test_search_with_topic(self, tavily_api_key):
        """Test search with topic filter."""
        result = tavily_search(
            "latest AI developments",
            topic="news",
            max_results=5
        )
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        assert "results" in result
    
    @pytest.mark.tavily
    def test_search_with_domain_filter(self, tavily_api_key):
        """Test search with domain filtering."""
        result = tavily_search(
            "machine learning",
            include_domains=["arxiv.org"],
            max_results=3
        )
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        # Results should be from arxiv.org
        for r in result.get("results", []):
            if "url" in r:
                assert "arxiv.org" in r["url"].lower() or len(result["results"]) == 0
    
    @pytest.mark.tavily
    def test_search_advanced_depth(self, tavily_api_key):
        """Test search with advanced depth."""
        result = tavily_search(
            "quantum computing applications",
            search_depth="advanced",
            max_results=3
        )
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        assert "results" in result


class TestTavilyExtract:
    """Tests for Tavily content extraction."""
    
    @pytest.mark.tavily
    def test_extract_single_url(self, tavily_api_key):
        """Test extracting content from a single URL."""
        result = tavily_extract("https://en.wikipedia.org/wiki/Python_(programming_language)")
        
        assert "error" not in result, f"Extract failed: {result.get('error')}"
        assert "results" in result
        if len(result["results"]) > 0:
            assert "raw_content" in result["results"][0] or "url" in result["results"][0]
    
    @pytest.mark.tavily
    def test_extract_multiple_urls(self, tavily_api_key):
        """Test extracting content from multiple URLs."""
        urls = [
            "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "https://en.wikipedia.org/wiki/Machine_learning"
        ]
        result = tavily_extract(urls)
        
        assert "error" not in result, f"Extract failed: {result.get('error')}"
        assert "results" in result


class TestTavilyCrawl:
    """Tests for Tavily website crawling."""
    
    @pytest.mark.tavily
    def test_basic_crawl(self, tavily_api_key):
        """Test basic website crawling."""
        result = tavily_crawl(
            "https://docs.python.org/3/",
            max_depth=1,
            limit=5
        )
        
        assert "error" not in result, f"Crawl failed: {result.get('error')}"
        # Crawl should return results or base_url
        assert "results" in result or "base_url" in result


class TestTavilyMap:
    """Tests for Tavily site mapping."""
    
    @pytest.mark.tavily
    def test_basic_map(self, tavily_api_key):
        """Test basic site mapping."""
        result = tavily_map(
            "https://docs.python.org/3/",
            max_depth=1,
            limit=10
        )
        
        assert "error" not in result, f"Map failed: {result.get('error')}"
        # Map should return results or base_url
        assert "results" in result or "base_url" in result


class TestTavilyToolsClass:
    """Tests for TavilyTools class."""
    
    @pytest.mark.tavily
    def test_class_instantiation(self, tavily_api_key):
        """Test creating TavilyTools instance."""
        tools = TavilyTools(api_key=tavily_api_key)
        assert tools._api_key == tavily_api_key
    
    @pytest.mark.tavily
    def test_class_search(self, tavily_tools):
        """Test search through class instance."""
        result = tavily_tools.search("Python programming", max_results=2)
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        assert "results" in result
    
    @pytest.mark.tavily
    def test_class_extract(self, tavily_tools):
        """Test extract through class instance."""
        result = tavily_tools.extract("https://www.python.org")
        
        assert "error" not in result, f"Extract failed: {result.get('error')}"


class TestTavilyErrorHandling:
    """Tests for error handling."""
    
    def test_missing_api_key(self, monkeypatch):
        """Test behavior when API key is missing."""
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        
        result = tavily_search("test query")
        
        assert "error" in result
        assert "TAVILY_API_KEY" in result["error"]
    
    @pytest.mark.tavily
    def test_invalid_url_extract(self, tavily_api_key):
        """Test extracting from invalid URL."""
        result = tavily_extract("https://this-domain-does-not-exist-12345.com")
        
        # Should either have error or failed_results
        assert "error" in result or "failed_results" in result or "results" in result
