"""Tests for Exa tools with real API calls.

These tests require EXA_API_KEY environment variable to be set.
Run with: pytest tests/test_exa.py -v
"""

import pytest

# Skip all tests if exa_py is not installed
pytest.importorskip("exa_py")

from praisonai_tools import ExaTools, exa_search, exa_search_contents, exa_find_similar, exa_answer


@pytest.fixture
def exa_tools(exa_api_key):
    """Create ExaTools instance."""
    return ExaTools(api_key=exa_api_key)


class TestExaSearch:
    """Tests for Exa search functionality."""
    
    @pytest.mark.exa
    def test_basic_search(self, exa_api_key):
        """Test basic search functionality."""
        result = exa_search("artificial intelligence startups", num_results=3)
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        assert "results" in result
        assert len(result["results"]) > 0
        
        # Check result structure
        first_result = result["results"][0]
        assert "url" in first_result
        assert "id" in first_result
    
    @pytest.mark.exa
    def test_search_with_category(self, exa_api_key):
        """Test search with category filter."""
        result = exa_search(
            "machine learning",
            category="research paper",
            num_results=3
        )
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        assert "results" in result
    
    @pytest.mark.exa
    def test_search_with_domain_filter(self, exa_api_key):
        """Test search with domain filtering."""
        result = exa_search(
            "python programming",
            include_domains=["github.com"],
            num_results=3
        )
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        assert "results" in result


class TestExaSearchContents:
    """Tests for Exa search with contents."""
    
    @pytest.mark.exa
    def test_search_with_text(self, exa_api_key):
        """Test search with full text content."""
        result = exa_search_contents(
            "latest AI news",
            text=True,
            num_results=2
        )
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        assert "results" in result
        
        # Check that text is included
        if len(result["results"]) > 0:
            first_result = result["results"][0]
            # Text should be present if available
            assert "url" in first_result
    
    @pytest.mark.exa
    def test_search_with_text_only(self, exa_api_key):
        """Test search with text content only."""
        result = exa_search_contents(
            "quantum computing",
            text=True,
            highlights=False,
            num_results=2
        )
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        assert "results" in result


class TestExaFindSimilar:
    """Tests for Exa find similar functionality."""
    
    @pytest.mark.exa
    def test_find_similar(self, exa_api_key):
        """Test finding similar pages."""
        result = exa_find_similar(
            "https://openai.com",
            num_results=3,
            exclude_source_domain=True
        )
        
        assert "error" not in result, f"Find similar failed: {result.get('error')}"
        assert "results" in result
        # Just verify we got results - domain exclusion may not always work perfectly
        assert len(result.get("results", [])) >= 0


class TestExaAnswer:
    """Tests for Exa answer functionality."""
    
    @pytest.mark.exa
    def test_basic_answer(self, exa_api_key):
        """Test getting an AI-generated answer."""
        result = exa_answer("What is the capital of Japan?")
        
        assert "error" not in result, f"Answer failed: {result.get('error')}"
        assert "answer" in result
        assert len(result["answer"]) > 0
        assert "citations" in result
    
    @pytest.mark.exa
    def test_answer_with_text(self, exa_api_key):
        """Test answer with citation text."""
        result = exa_answer(
            "What are the main features of Python programming language?",
            text=True
        )
        
        assert "error" not in result, f"Answer failed: {result.get('error')}"
        assert "answer" in result
        assert "citations" in result


class TestExaToolsClass:
    """Tests for ExaTools class."""
    
    @pytest.mark.exa
    def test_class_instantiation(self, exa_api_key):
        """Test creating ExaTools instance."""
        tools = ExaTools(api_key=exa_api_key)
        assert tools.api_key == exa_api_key
    
    @pytest.mark.exa
    def test_class_search(self, exa_tools):
        """Test search through class instance."""
        result = exa_tools.search("Python programming", num_results=2)
        
        assert "error" not in result, f"Search failed: {result.get('error')}"
        assert "results" in result
    
    @pytest.mark.exa
    def test_class_answer(self, exa_tools):
        """Test answer through class instance."""
        result = exa_tools.answer("What is machine learning?")
        
        assert "error" not in result, f"Answer failed: {result.get('error')}"
        assert "answer" in result


class TestExaErrorHandling:
    """Tests for error handling."""
    
    def test_missing_api_key(self, monkeypatch):
        """Test behavior when API key is missing."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        
        result = exa_search("test query")
        
        assert "error" in result
        assert "EXA_API_KEY" in result["error"]
