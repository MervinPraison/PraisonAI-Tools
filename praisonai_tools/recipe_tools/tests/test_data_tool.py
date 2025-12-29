"""Tests for DataTool."""

import json
import pytest
from pathlib import Path

from praisonai_tools.recipe_tools.data_tool import DataTool, data_profile, data_clean, data_convert


class TestDataTool:
    """Unit tests for DataTool."""
    
    @pytest.fixture
    def tool(self):
        return DataTool(verbose=True)
    
    @pytest.mark.unit
    def test_check_dependencies(self, tool):
        """Test dependency checking."""
        deps = tool.check_dependencies()
        assert "pandas" in deps
        assert "pyarrow" in deps
    
    @pytest.mark.unit
    def test_detect_format(self, tool):
        """Test format detection."""
        assert tool._detect_format(Path("test.csv")) == "csv"
        assert tool._detect_format(Path("test.json")) == "json"
        assert tool._detect_format(Path("test.parquet")) == "parquet"
        assert tool._detect_format(Path("test.xlsx")) == "excel"
    
    @pytest.mark.unit
    def test_profile_csv(self, tool, sample_csv, temp_dir):
        """Test profiling a CSV file."""
        if not sample_csv.exists():
            pytest.skip("Sample CSV not found")
        
        result = tool.profile(sample_csv)
        
        assert result.path == str(sample_csv)
        assert result.format == "csv"
        assert result.row_count == 10
        assert result.column_count == 6
        assert len(result.columns) == 6
        
        # Check column profiles
        id_col = next(c for c in result.columns if c.name == "id")
        assert id_col.dtype == "int64"
        assert id_col.null_count == 0
    
    @pytest.mark.unit
    def test_profile_json(self, tool, sample_json, temp_dir):
        """Test profiling a JSON file."""
        if not sample_json.exists():
            pytest.skip("Sample JSON not found")
        
        result = tool.profile(sample_json)
        
        assert result.format == "json"
        assert result.row_count == 5
    
    @pytest.mark.unit
    def test_clean_csv(self, tool, sample_csv, temp_dir):
        """Test cleaning a CSV file."""
        if not sample_csv.exists():
            pytest.skip("Sample CSV not found")
        
        output_path = temp_dir / "cleaned.csv"
        result = tool.clean(sample_csv, output_path, drop_duplicates=True)
        
        assert result.exists()
        assert result.stat().st_size > 0
    
    @pytest.mark.unit
    def test_convert_csv_to_json(self, tool, sample_csv, temp_dir):
        """Test converting CSV to JSON."""
        if not sample_csv.exists():
            pytest.skip("Sample CSV not found")
        
        output_path = temp_dir / "output.json"
        result = tool.convert(sample_csv, output_path)
        
        assert result.exists()
        
        # Verify JSON is valid
        with open(result) as f:
            data = json.load(f)
        assert len(data) == 10
    
    @pytest.mark.unit
    def test_infer_schema(self, tool, sample_csv, temp_dir):
        """Test schema inference."""
        if not sample_csv.exists():
            pytest.skip("Sample CSV not found")
        
        schema = tool.infer_schema(sample_csv, output_format="json_schema")
        
        assert "$schema" in schema
        assert "properties" in schema
        assert "id" in schema["properties"]
    
    @pytest.mark.unit
    def test_generate_profile_report(self, tool, sample_csv, temp_dir):
        """Test HTML report generation."""
        if not sample_csv.exists():
            pytest.skip("Sample CSV not found")
        
        output_path = temp_dir / "report.html"
        result = tool.generate_profile_report(sample_csv, output_path)
        
        assert result.exists()
        content = result.read_text()
        assert "<html>" in content
        assert "Data Profile" in content


class TestDataToolConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.unit
    def test_data_profile(self, sample_csv):
        """Test data_profile function."""
        if not sample_csv.exists():
            pytest.skip("Sample CSV not found")
        
        result = data_profile(sample_csv)
        assert result.row_count == 10
    
    @pytest.mark.unit
    def test_data_clean(self, sample_csv, temp_dir):
        """Test data_clean function."""
        if not sample_csv.exists():
            pytest.skip("Sample CSV not found")
        
        output = temp_dir / "cleaned.csv"
        result = data_clean(sample_csv, output)
        assert result.exists()
    
    @pytest.mark.unit
    def test_data_convert(self, sample_csv, temp_dir):
        """Test data_convert function."""
        if not sample_csv.exists():
            pytest.skip("Sample CSV not found")
        
        output = temp_dir / "output.json"
        result = data_convert(sample_csv, output)
        assert result.exists()
