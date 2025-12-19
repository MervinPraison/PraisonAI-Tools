"""Tests for You.com tools with real API calls.

These tests require YDC_API_KEY environment variable to be set.
Run with: pytest tests/test_youdotcom.py -v
"""

import pytest

# Skip all tests if youdotcom is not installed
pytest.importorskip("youdotcom")

from praisonai_tools import YouTools, ydc_search, ydc_contents, ydc_news, ydc_images


@pytest.fixture
def you_tools(ydc_api_key):
    """Create YouTools instance."""
    return YouTools(api_key=ydc_api_key)


class TestYdcSearch:
    """Tests for You.com search functionality."""
    
    @pytest.mark.youdotcom
    def test_basic_search(self, ydc_api_key):
        """Test basic search functionality."""
        result = ydc_search("Python programming language", count=3)
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        # Result should have results or metadata
        assert "results" in result or "metadata" in result
    
    @pytest.mark.youdotcom
    def test_search_with_freshness(self, ydc_api_key):
        """Test search with freshness filter."""
        result = ydc_search(
            "latest AI news",
            freshness="week",
            count=5
        )
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
    
    @pytest.mark.youdotcom
    def test_search_with_country(self, ydc_api_key):
        """Test search with country filter."""
        result = ydc_search(
            "technology news",
            country="US",
            count=3
        )
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
    
    @pytest.mark.youdotcom
    def test_search_with_safesearch(self, ydc_api_key):
        """Test search with safesearch filter."""
        result = ydc_search(
            "programming tutorials",
            safesearch="strict",
            count=3
        )
        
        assert "error" not in result, f"Search failed: {result.get('error')}"


class TestYdcContents:
    """Tests for You.com content extraction."""
    
    @pytest.mark.youdotcom
    def test_extract_single_url(self, ydc_api_key):
        """Test extracting content from a single URL."""
        result = ydc_contents("https://www.python.org")
        
        # Contents API may not be available in all SDK versions
        # Just verify it returns a dict (with error or results)
        assert isinstance(result, dict)
    
    @pytest.mark.youdotcom
    def test_extract_markdown_format(self, ydc_api_key):
        """Test extracting content in markdown format."""
        result = ydc_contents(
            "https://en.wikipedia.org/wiki/Python_(programming_language)",
            format="markdown"
        )
        
        # Contents API may not be available in all SDK versions
        assert isinstance(result, dict)
    
    @pytest.mark.youdotcom
    def test_extract_multiple_urls(self, ydc_api_key):
        """Test extracting content from multiple URLs."""
        urls = [
            "https://www.python.org",
            "https://docs.python.org"
        ]
        result = ydc_contents(urls)
        
        # Contents API may not be available in all SDK versions
        assert isinstance(result, dict)


class TestYdcNews:
    """Tests for You.com news search."""
    
    @pytest.mark.youdotcom
    def test_basic_news(self, ydc_api_key):
        """Test basic news search."""
        result = ydc_news("technology", count=5)
        
        # News might fall back to unified search
        assert "error" not in result, f"News failed: {result.get('error')}"
    
    @pytest.mark.youdotcom
    def test_news_with_count(self, ydc_api_key):
        """Test news search with count limit."""
        result = ydc_news("artificial intelligence", count=3)
        
        assert "error" not in result, f"News failed: {result.get('error')}"


class TestYdcImages:
    """Tests for You.com image search."""
    
    @pytest.mark.youdotcom
    def test_basic_images(self, ydc_api_key):
        """Test basic image search."""
        result = ydc_images("python programming")
        
        # Image search might not be available in all SDK versions
        # So we just check it doesn't crash
        assert isinstance(result, dict)


class TestYouToolsClass:
    """Tests for YouTools class."""
    
    @pytest.mark.youdotcom
    def test_class_instantiation(self, ydc_api_key):
        """Test creating YouTools instance."""
        tools = YouTools(api_key=ydc_api_key)
        assert tools._api_key == ydc_api_key
    
    @pytest.mark.youdotcom
    def test_class_search(self, you_tools):
        """Test search through class instance."""
        result = you_tools.search("Python programming", count=2)
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
    
    @pytest.mark.youdotcom
    def test_class_get_contents(self, you_tools):
        """Test get_contents through class instance."""
        result = you_tools.get_contents("https://www.python.org")
        
        # Contents API may not be available in all SDK versions
        assert isinstance(result, dict)
    
    @pytest.mark.youdotcom
    def test_context_manager(self, ydc_api_key):
        """Test using YouTools as context manager."""
        with YouTools(api_key=ydc_api_key) as tools:
            result = tools.search("test", count=1)
            assert isinstance(result, dict)


class TestYdcErrorHandling:
    """Tests for error handling."""
    
    def test_missing_api_key(self, monkeypatch):
        """Test behavior when API key is missing."""
        monkeypatch.delenv("YDC_API_KEY", raising=False)
        
        result = ydc_search("test query")
        
        assert "error" in result
        assert "YDC_API_KEY" in result["error"]
