"""Unit tests for EditIntent schema."""

import pytest
from praisonai_tools.fcp_tool.intent import (
    EditIntent,
    Asset,
    Segment,
    Timeline,
    Project,
    ProjectFormat,
    Operations,
    seconds_to_rational,
    rational_to_seconds,
    get_format_preset,
    FORMAT_PRESETS,
)


class TestProjectFormat:
    """Tests for ProjectFormat model."""

    def test_defaults(self):
        """Test default values."""
        fmt = ProjectFormat()
        assert fmt.width == 1920
        assert fmt.height == 1080
        assert fmt.fps == 25.0
        assert fmt.frame_duration_rational == "100/2500s"

    def test_custom_fps(self):
        """Test custom fps calculates correct frame duration."""
        fmt = ProjectFormat(fps=30.0)
        assert fmt.frame_duration_rational == "100/3000s"

    def test_get_timescale(self):
        """Test timescale calculation."""
        fmt = ProjectFormat(fps=25.0)
        assert fmt.get_timescale() == 2500

        fmt30 = ProjectFormat(fps=30.0)
        assert fmt30.get_timescale() == 3000


class TestAsset:
    """Tests for Asset model."""

    def test_uid_generation(self):
        """Test UID is generated from path."""
        asset = Asset(id="r2", name="test", path="/path/to/file.mov")
        assert asset.uid is not None
        assert len(asset.uid) == 32

    def test_same_path_same_uid(self):
        """Test same path generates same UID."""
        asset1 = Asset(id="r2", name="test1", path="/path/to/file.mov")
        asset2 = Asset(id="r3", name="test2", path="/path/to/file.mov")
        assert asset1.uid == asset2.uid

    def test_different_path_different_uid(self):
        """Test different paths generate different UIDs."""
        asset1 = Asset(id="r2", name="test1", path="/path/to/file1.mov")
        asset2 = Asset(id="r3", name="test2", path="/path/to/file2.mov")
        assert asset1.uid != asset2.uid

    def test_src_url(self):
        """Test file URL generation."""
        asset = Asset(id="r2", name="test", path="/path/to/file.mov")
        assert asset.get_src_url() == "file:///path/to/file.mov"

    def test_path_must_be_absolute(self):
        """Test that relative paths are rejected."""
        with pytest.raises(ValueError, match="must be absolute"):
            Asset(id="r2", name="test", path="relative/path.mov")


class TestSegment:
    """Tests for Segment model."""

    def test_rational_time_validation(self):
        """Test rational time format validation."""
        segment = Segment(
            asset_id="r2",
            offset="0/2500s",
            start="0/2500s",
            duration="5000/2500s",
        )
        assert segment.offset == "0/2500s"

    def test_invalid_rational_time(self):
        """Test invalid rational time is rejected."""
        with pytest.raises(ValueError, match="Invalid rational time"):
            Segment(
                asset_id="r2",
                offset="invalid",
                start="0/2500s",
                duration="5000/2500s",
            )


class TestOperations:
    """Tests for Operations model."""

    def test_unimplemented_warnings(self):
        """Test warnings for unimplemented operations."""
        ops = Operations(loudness_target_lufs=-16.0)
        warnings = ops.get_unimplemented_warnings()
        assert len(warnings) == 1
        assert "loudness" in warnings[0].lower()

    def test_multiple_warnings(self):
        """Test multiple unimplemented operations."""
        ops = Operations(
            loudness_target_lufs=-16.0,
            remove_pauses_over_seconds=2.0,
        )
        warnings = ops.get_unimplemented_warnings()
        assert len(warnings) == 2


class TestEditIntent:
    """Tests for EditIntent model."""

    def test_minimal_intent(self):
        """Test creating minimal valid intent."""
        intent = EditIntent(
            project=Project(name="Test"),
            assets=[Asset(id="r2", name="clip", path="/tmp/test.mov")],
            timeline=Timeline(segments=[
                Segment(asset_id="r2", offset="0/2500s", start="0/2500s", duration="5000/2500s")
            ])
        )
        assert intent.version == "1"
        assert len(intent.assets) == 1
        assert len(intent.timeline.segments) == 1

    def test_asset_reference_validation(self):
        """Test that invalid asset references are rejected."""
        with pytest.raises(ValueError, match="unknown asset_id"):
            EditIntent(
                project=Project(name="Test"),
                assets=[Asset(id="r2", name="clip", path="/tmp/test.mov")],
                timeline=Timeline(segments=[
                    Segment(asset_id="r99", offset="0/2500s", start="0/2500s", duration="5000/2500s")
                ])
            )

    def test_get_asset_by_id(self):
        """Test getting asset by ID."""
        intent = EditIntent(
            project=Project(name="Test"),
            assets=[
                Asset(id="r2", name="clip1", path="/tmp/test1.mov"),
                Asset(id="r3", name="clip2", path="/tmp/test2.mov"),
            ],
            timeline=Timeline(segments=[])
        )
        asset = intent.get_asset_by_id("r3")
        assert asset is not None
        assert asset.name == "clip2"

        assert intent.get_asset_by_id("r99") is None

    def test_get_warnings(self):
        """Test collecting warnings."""
        intent = EditIntent(
            project=Project(name="Test"),
            assets=[Asset(id="r2", name="clip", path="/tmp/test.mov")],
            timeline=Timeline(segments=[]),
            operations=Operations(loudness_target_lufs=-16.0),
            needs_user_timestamps=True,
        )
        warnings = intent.get_warnings()
        assert len(warnings) >= 2


class TestTimeConversion:
    """Tests for time conversion utilities."""

    def test_seconds_to_rational(self):
        """Test seconds to rational conversion."""
        assert seconds_to_rational(1.0, fps=25.0) == "2500/2500s"
        assert seconds_to_rational(2.0, fps=25.0) == "5000/2500s"
        assert seconds_to_rational(0.5, fps=25.0) == "1250/2500s"

    def test_rational_to_seconds(self):
        """Test rational to seconds conversion."""
        assert rational_to_seconds("2500/2500s") == 1.0
        assert rational_to_seconds("5000/2500s") == 2.0
        assert rational_to_seconds("1250/2500s") == 0.5

    def test_roundtrip(self):
        """Test conversion roundtrip."""
        original = 3.5
        rational = seconds_to_rational(original, fps=25.0)
        result = rational_to_seconds(rational)
        assert abs(result - original) < 0.001


class TestFormatPresets:
    """Tests for format presets."""

    def test_preset_exists(self):
        """Test getting existing preset."""
        preset = get_format_preset("1080p25")
        assert preset.width == 1920
        assert preset.height == 1080
        assert preset.fps == 25.0

    def test_preset_not_found(self):
        """Test error for unknown preset."""
        with pytest.raises(ValueError, match="Unknown format preset"):
            get_format_preset("invalid_preset")

    def test_all_presets_valid(self):
        """Test all presets are valid."""
        for name in FORMAT_PRESETS:
            preset = get_format_preset(name)
            assert preset.width > 0
            assert preset.height > 0
            assert preset.fps > 0
