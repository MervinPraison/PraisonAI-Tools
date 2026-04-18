"""Tests for LangExtract Tool."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from praisonai_tools.tools.langextract_tool import (
    LangExtractTool,
    langextract_extract,
    langextract_render_file,
    _get_langextract,
    _create_annotated_document
)


class TestLangExtractTool:
    """Test LangExtractTool class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = LangExtractTool()
    
    def test_tool_properties(self):
        """Test tool name and description."""
        assert self.tool.name == "langextract"
        assert "interactive HTML visualizations" in self.tool.description
    
    def test_run_unknown_action(self):
        """Test run with unknown action."""
        result = self.tool.run(action="unknown")
        assert "error" in result
        assert "Unknown action" in result["error"]
    
    def test_extract_without_langextract(self):
        """Test extract when langextract is not installed."""
        with patch('praisonai_tools.tools.langextract_tool._get_langextract', return_value=None):
            result = self.tool.extract(text="test text")
            assert "error" in result
            assert "langextract not installed" in result["error"]
    
    def test_extract_empty_text(self):
        """Test extract with empty text."""
        result = self.tool.extract(text="")
        assert "error" in result
        assert "text parameter is required" in result["error"]
    
    @patch('praisonai_tools.tools.langextract_tool._get_langextract')
    @patch('praisonai_tools.tools.langextract_tool._create_annotated_document')
    def test_extract_success(self, mock_create_doc, mock_get_lx):
        """Test successful text extraction."""
        # Mock langextract
        mock_lx = Mock()
        mock_get_lx.return_value = mock_lx
        
        # Mock annotated document
        mock_doc = Mock()
        mock_create_doc.return_value = mock_doc
        
        # Mock visualization methods
        mock_lx.io.save_annotated_documents = Mock()
        mock_lx.visualize = Mock(return_value="<html>mock visualization</html>")
        
        text = "John Doe works at OpenAI"
        extractions = ["John Doe", "OpenAI"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "test.html")
            
            result = self.tool.extract(
                text=text,
                extractions=extractions,
                document_id="test-doc",
                output_path=output_path
            )
            
            assert result["success"] is True
            assert result["document_id"] == "test-doc"
            assert result["extractions_count"] == 2
            assert result["text_length"] == len(text)
            
            # Verify langextract was called
            mock_create_doc.assert_called_once_with(text, extractions, "test-doc")
            mock_lx.io.save_annotated_documents.assert_called_once()
            mock_lx.visualize.assert_called_once()
    
    @patch('praisonai_tools.tools.langextract_tool._get_langextract')
    def test_extract_with_auto_open(self, mock_get_lx):
        """Test extract with auto_open=True."""
        # Mock langextract
        mock_lx = Mock()
        mock_get_lx.return_value = mock_lx
        
        # Mock document creation and visualization
        with patch('praisonai_tools.tools.langextract_tool._create_annotated_document') as mock_create_doc:
            mock_create_doc.return_value = Mock()
            mock_lx.io.save_annotated_documents = Mock()
            mock_lx.visualize = Mock(return_value="<html>mock visualization</html>")
            
            with patch('webbrowser.open') as mock_open:
                with tempfile.TemporaryDirectory() as temp_dir:
                    output_path = os.path.join(temp_dir, "test.html")
                    
                    result = self.tool.extract(
                        text="test text",
                        auto_open=True,
                        output_path=output_path
                    )
                    
                    assert result["success"] is True
                    assert "auto_opened" in result
                    mock_open.assert_called_once()
    
    def test_render_file_missing_path(self):
        """Test render_file with missing file_path."""
        result = self.tool.render_file(file_path="")
        assert "error" in result
        assert "file_path parameter is required" in result["error"]
    
    def test_render_file_nonexistent(self):
        """Test render_file with non-existent file."""
        result = self.tool.render_file(file_path="/nonexistent/file.txt")
        assert "error" in result
        assert "File not found" in result["error"]
    
    @patch('praisonai_tools.tools.langextract_tool._get_langextract')
    @patch('praisonai_tools.tools.langextract_tool._create_annotated_document')
    def test_render_file_success(self, mock_create_doc, mock_get_lx):
        """Test successful file rendering."""
        # Mock langextract
        mock_lx = Mock()
        mock_get_lx.return_value = mock_lx
        
        # Mock annotated document
        mock_doc = Mock()
        mock_create_doc.return_value = mock_doc
        
        # Mock visualization methods
        mock_lx.io.save_annotated_documents = Mock()
        mock_lx.visualize = Mock(return_value="<html>mock visualization</html>")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            temp_file.write("This is test content with important terms.")
            temp_file_path = temp_file.name
        
        try:
            result = self.tool.render_file(
                file_path=temp_file_path,
                extractions=["important terms"]
            )
            
            assert result["success"] is True
            assert result["text_length"] > 0
            
        finally:
            os.unlink(temp_file_path)


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_get_langextract_not_installed(self):
        """Test _get_langextract when module not installed."""
        with patch.dict('sys.modules', {'langextract': None}):
            with patch('builtins.__import__', side_effect=ImportError):
                result = _get_langextract()
                assert result is None
    
    @patch('praisonai_tools.tools.langextract_tool._get_langextract')
    def test_create_annotated_document(self, mock_get_lx):
        """Test _create_annotated_document function."""
        # Mock langextract
        mock_lx = Mock()
        mock_get_lx.return_value = mock_lx
        
        # Mock CharInterval and AnnotatedDocument
        mock_char_interval = Mock()
        mock_lx.data.CharInterval.return_value = mock_char_interval
        mock_annotated_doc = Mock()
        mock_lx.data.AnnotatedDocument.return_value = mock_annotated_doc
        
        text = "John Doe works at OpenAI"
        extractions = ["John Doe"]
        document_id = "test"
        
        result = _create_annotated_document(text, extractions, document_id)
        
        assert result == mock_annotated_doc
        mock_lx.data.CharInterval.assert_called()
        mock_lx.data.AnnotatedDocument.assert_called_once()
    
    def test_create_annotated_document_no_langextract(self):
        """Test _create_annotated_document when langextract not available."""
        with patch('praisonai_tools.tools.langextract_tool._get_langextract', return_value=None):
            result = _create_annotated_document("text", [], "id")
            assert result is None


class TestToolDecorators:
    """Test tool decorator functions."""
    
    @patch('praisonai_tools.tools.langextract_tool.LangExtractTool')
    def test_langextract_extract_function(self, mock_tool_class):
        """Test langextract_extract decorator function."""
        mock_tool = Mock()
        mock_tool_class.return_value = mock_tool
        mock_tool.extract.return_value = {"success": True}
        
        result = langextract_extract(
            text="test text",
            extractions=["test"],
            document_id="test-doc"
        )
        
        assert result == {"success": True}
        mock_tool.extract.assert_called_once_with(
            text="test text",
            extractions=["test"],
            document_id="test-doc",
            output_path=None,
            auto_open=False
        )
    
    @patch('praisonai_tools.tools.langextract_tool.LangExtractTool')
    def test_langextract_render_file_function(self, mock_tool_class):
        """Test langextract_render_file decorator function."""
        mock_tool = Mock()
        mock_tool_class.return_value = mock_tool
        mock_tool.render_file.return_value = {"success": True}
        
        result = langextract_render_file(
            file_path="/test/path.txt",
            extractions=["test"]
        )
        
        assert result == {"success": True}
        mock_tool.render_file.assert_called_once_with(
            file_path="/test/path.txt",
            extractions=["test"],
            output_path=None,
            auto_open=False
        )


class TestIntegration:
    """Integration tests with real agentic scenarios."""
    
    @patch('praisonai_tools.tools.langextract_tool._get_langextract')
    @patch('praisonai_tools.tools.langextract_tool._create_annotated_document')
    def test_contract_analysis_scenario(self, mock_create_doc, mock_get_lx):
        """Test contract analysis use case."""
        # Mock langextract
        mock_lx = Mock()
        mock_get_lx.return_value = mock_lx
        mock_create_doc.return_value = Mock()
        mock_lx.io.save_annotated_documents = Mock()
        mock_lx.visualize = Mock(return_value="<html>mock visualization</html>")
        
        # Simulate contract text with key terms
        contract_text = """
        This Agreement is entered into between John Doe (the "Client") 
        and OpenAI Corporation (the "Service Provider") effective 
        January 1, 2024. The payment terms are Net 30 days.
        """
        
        key_terms = ["John Doe", "OpenAI Corporation", "January 1, 2024", "Net 30 days"]
        
        result = langextract_extract(
            text=contract_text,
            extractions=key_terms,
            document_id="contract-001",
            auto_open=False
        )
        
        assert result["success"] is True
        assert result["document_id"] == "contract-001"
        assert result["extractions_count"] == len(key_terms)
    
    def test_agent_usage_pattern(self):
        """Test typical agent usage pattern."""
        # This would be how an agent uses the tool
        from praisonai_tools import langextract_extract
        
        # Agent analyzes text and wants to highlight findings
        analysis_text = "The quarterly report shows revenue of $1.2M and profit of $300K."
        findings = ["$1.2M", "$300K", "quarterly report"]
        
        result = langextract_extract(
            text=analysis_text,
            extractions=findings,
            document_id="financial-analysis",
            auto_open=False,
        )

        assert result["success"] is True
        assert result["document_id"] == "financial-analysis"
        assert result["extractions_count"] == len(findings)