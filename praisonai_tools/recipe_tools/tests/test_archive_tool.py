"""Tests for ArchiveTool."""

import pytest

from praisonai_tools.recipe_tools.archive_tool import ArchiveTool, archive_create, archive_extract, archive_list


class TestArchiveTool:
    """Unit tests for ArchiveTool."""
    
    @pytest.fixture
    def tool(self):
        return ArchiveTool(verbose=True)
    
    @pytest.mark.unit
    def test_check_dependencies(self, tool):
        """Test dependency checking."""
        deps = tool.check_dependencies()
        assert deps["zipfile"] is True
        assert deps["tarfile"] is True
    
    @pytest.mark.unit
    def test_create_zip(self, tool, sample_folder, temp_dir):
        """Test creating a zip archive."""
        if not sample_folder.exists():
            pytest.skip("Sample folder not found")
        
        output = temp_dir / "test.zip"
        result = tool.create(sample_folder, output, format="zip")
        
        assert result.exists()
        assert result.stat().st_size > 0
    
    @pytest.mark.unit
    def test_create_tar_gz(self, tool, sample_folder, temp_dir):
        """Test creating a tar.gz archive."""
        if not sample_folder.exists():
            pytest.skip("Sample folder not found")
        
        output = temp_dir / "test.tar.gz"
        result = tool.create(sample_folder, output, format="tar.gz")
        
        assert result.exists()
        assert result.stat().st_size > 0
    
    @pytest.mark.unit
    def test_list_zip(self, tool, sample_folder, temp_dir):
        """Test listing zip contents."""
        if not sample_folder.exists():
            pytest.skip("Sample folder not found")
        
        # Create archive first
        archive = temp_dir / "test.zip"
        tool.create(sample_folder, archive, format="zip")
        
        # List contents
        manifest = tool.list(archive)
        
        assert manifest.format == "zip"
        assert manifest.file_count > 0
        assert len(manifest.entries) > 0
    
    @pytest.mark.unit
    def test_extract_zip(self, tool, sample_folder, temp_dir):
        """Test extracting a zip archive."""
        if not sample_folder.exists():
            pytest.skip("Sample folder not found")
        
        # Create archive first
        archive = temp_dir / "test.zip"
        tool.create(sample_folder, archive, format="zip")
        
        # Extract
        extract_dir = temp_dir / "extracted"
        result = tool.extract(archive, extract_dir)
        
        assert result.exists()
        assert result.is_dir()
        # Check some files exist
        assert any(result.rglob("*.txt"))
    
    @pytest.mark.unit
    def test_create_manifest(self, tool, sample_folder, temp_dir):
        """Test creating a manifest."""
        if not sample_folder.exists():
            pytest.skip("Sample folder not found")
        
        output = temp_dir / "manifest.json"
        manifest = tool.create_manifest(sample_folder, output)
        
        assert "files" in manifest
        assert manifest["file_count"] > 0
        assert output.exists()
    
    @pytest.mark.unit
    def test_create_checksums(self, tool, sample_folder, temp_dir):
        """Test creating checksums file."""
        if not sample_folder.exists():
            pytest.skip("Sample folder not found")
        
        output = temp_dir / "checksums.txt"
        content = tool.create_checksums(sample_folder, output)
        
        assert len(content) > 0
        assert output.exists()
        # Check format
        lines = content.split("\n")
        assert all("  " in line for line in lines if line)
    
    @pytest.mark.unit
    def test_excludes(self, tool, temp_dir):
        """Test exclusion patterns."""
        # Create folder with files to exclude
        test_folder = temp_dir / "test_excludes"
        test_folder.mkdir()
        (test_folder / "keep.txt").write_text("keep")
        (test_folder / ".DS_Store").write_text("exclude")
        pycache = test_folder / "__pycache__"
        pycache.mkdir()
        (pycache / "test.pyc").write_text("exclude")
        
        # Create archive
        archive = temp_dir / "test.zip"
        tool.create(test_folder, archive, format="zip")
        
        # List and verify exclusions
        manifest = tool.list(archive)
        names = [e.name for e in manifest.entries]
        
        assert any("keep.txt" in n for n in names)
        assert not any(".DS_Store" in n for n in names)
        assert not any("__pycache__" in n for n in names)


class TestArchiveToolConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.unit
    def test_archive_create(self, sample_folder, temp_dir):
        """Test archive_create function."""
        if not sample_folder.exists():
            pytest.skip("Sample folder not found")
        
        output = temp_dir / "test.zip"
        result = archive_create(sample_folder, output)
        assert result.exists()
    
    @pytest.mark.unit
    def test_archive_extract(self, sample_folder, temp_dir):
        """Test archive_extract function."""
        if not sample_folder.exists():
            pytest.skip("Sample folder not found")
        
        archive = temp_dir / "test.zip"
        archive_create(sample_folder, archive)
        
        extract_dir = temp_dir / "extracted"
        result = archive_extract(archive, extract_dir)
        assert result.exists()
    
    @pytest.mark.unit
    def test_archive_list(self, sample_folder, temp_dir):
        """Test archive_list function."""
        if not sample_folder.exists():
            pytest.skip("Sample folder not found")
        
        archive = temp_dir / "test.zip"
        archive_create(sample_folder, archive)
        
        manifest = archive_list(archive)
        assert manifest.file_count > 0
