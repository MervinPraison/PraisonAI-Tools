"""Tests for MediaTool."""

import pytest

from praisonai_tools.recipe_tools.media_tool import MediaTool, media_probe


class TestMediaTool:
    """Unit tests for MediaTool."""
    
    @pytest.fixture
    def tool(self):
        return MediaTool(verbose=True)
    
    @pytest.mark.unit
    def test_check_dependencies(self, tool):
        """Test dependency checking."""
        deps = tool.check_dependencies()
        assert "ffmpeg" in deps
        assert "ffprobe" in deps
    
    @pytest.mark.requires_ffmpeg
    def test_probe_video(self, tool, sample_video, has_ffmpeg):
        """Test probing a video file."""
        if not has_ffmpeg:
            pytest.skip("ffmpeg not available")
        if not sample_video.exists():
            pytest.skip("Sample video not found")
        
        result = tool.probe(sample_video)
        
        assert result.path == str(sample_video)
        assert result.duration > 0
        assert result.has_video or result.has_audio
    
    @pytest.mark.requires_ffmpeg
    def test_probe_audio(self, tool, sample_audio, has_ffmpeg):
        """Test probing an audio file."""
        if not has_ffmpeg:
            pytest.skip("ffmpeg not available")
        if not sample_audio.exists():
            pytest.skip("Sample audio not found")
        
        result = tool.probe(sample_audio)
        
        assert result.path == str(sample_audio)
        assert result.has_audio
    
    @pytest.mark.requires_ffmpeg
    def test_extract_audio(self, tool, sample_video, temp_dir, has_ffmpeg):
        """Test extracting audio from video."""
        if not has_ffmpeg:
            pytest.skip("ffmpeg not available")
        if not sample_video.exists():
            pytest.skip("Sample video not found")
        
        output = temp_dir / "audio.mp3"
        result = tool.extract_audio(sample_video, output)
        
        assert result.exists()
        assert result.stat().st_size > 0
    
    @pytest.mark.requires_ffmpeg
    def test_trim(self, tool, sample_video, temp_dir, has_ffmpeg):
        """Test trimming a video."""
        if not has_ffmpeg:
            pytest.skip("ffmpeg not available")
        if not sample_video.exists():
            pytest.skip("Sample video not found")
        
        output = temp_dir / "trimmed.mp4"
        result = tool.trim(sample_video, output, start=0, duration=2)
        
        assert result.exists()
    
    @pytest.mark.requires_ffmpeg
    def test_extract_frames(self, tool, sample_video, temp_dir, has_ffmpeg):
        """Test extracting frames from video."""
        if not has_ffmpeg:
            pytest.skip("ffmpeg not available")
        if not sample_video.exists():
            pytest.skip("Sample video not found")
        
        frames = tool.extract_frames(sample_video, temp_dir, interval=1)
        
        assert len(frames) > 0
        assert all(f.exists() for f in frames)
    
    @pytest.mark.unit
    def test_probe_file_not_found(self, tool):
        """Test probing non-existent file."""
        with pytest.raises(FileNotFoundError):
            tool.probe("/nonexistent/file.mp4")


class TestMediaToolConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.requires_ffmpeg
    def test_media_probe(self, sample_video, has_ffmpeg):
        """Test media_probe function."""
        if not has_ffmpeg:
            pytest.skip("ffmpeg not available")
        if not sample_video.exists():
            pytest.skip("Sample video not found")
        
        result = media_probe(sample_video)
        assert result.duration > 0
