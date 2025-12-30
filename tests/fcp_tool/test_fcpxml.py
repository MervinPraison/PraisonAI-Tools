"""Unit tests for FCPXML generator."""

import xml.etree.ElementTree as ET
from praisonai_tools.fcp_tool.intent import (
    EditIntent,
    Asset,
    Segment,
    Timeline,
    Project,
    ProjectFormat,
    AudioSettings,
    AudioRole,
)
from praisonai_tools.fcp_tool.fcpxml import (
    FCPXMLGenerator,
    generate_fcpxml,
    validate_fcpxml_structure,
)


def create_test_intent():
    """Create a test EditIntent."""
    return EditIntent(
        project=Project(
            name="Test Project",
            format=ProjectFormat(width=1920, height=1080, fps=25.0),
            audio=AudioSettings(),
        ),
        assets=[
            Asset(id="r2", name="clip1", path="/path/to/clip1.mov", has_video=True, has_audio=True),
            Asset(id="r3", name="audio1", path="/path/to/audio1.wav", has_video=False, has_audio=True),
        ],
        timeline=Timeline(segments=[
            Segment(asset_id="r2", offset="0/2500s", start="0/2500s", duration="5000/2500s", role=AudioRole.DIALOGUE),
            Segment(asset_id="r3", offset="5000/2500s", start="0/2500s", duration="2500/2500s", role=AudioRole.MUSIC),
        ])
    )


class TestFCPXMLGenerator:
    """Tests for FCPXML generation."""

    def test_generate_basic(self):
        """Test basic FCPXML generation."""
        intent = create_test_intent()
        generator = FCPXMLGenerator(intent)
        xml_str = generator.generate()

        assert '<?xml version="1.0"' in xml_str
        assert '<!DOCTYPE fcpxml>' in xml_str
        assert '<fcpxml' in xml_str

    def test_validate_structure(self):
        """Test FCPXML structure validation."""
        intent = create_test_intent()
        generator = FCPXMLGenerator(intent)
        xml_str = generator.generate()

        is_valid, error = validate_fcpxml_structure(xml_str)
        assert is_valid, f"Validation failed: {error}"

    def test_contains_resources(self):
        """Test FCPXML contains resources section."""
        intent = create_test_intent()
        generator = FCPXMLGenerator(intent)
        xml_str = generator.generate()

        assert '<resources>' in xml_str
        assert '<format' in xml_str
        assert '<asset' in xml_str

    def test_contains_spine(self):
        """Test FCPXML contains spine with clips."""
        intent = create_test_intent()
        generator = FCPXMLGenerator(intent)
        xml_str = generator.generate()

        assert '<spine>' in xml_str
        assert '<asset-clip' in xml_str

    def test_clips_count(self):
        """Test correct number of clips."""
        intent = create_test_intent()
        generator = FCPXMLGenerator(intent)
        xml_str = generator.generate()

        # Parse XML (remove DOCTYPE for parsing)
        xml_content = '\n'.join(
            line for line in xml_str.split('\n')
            if not line.strip().startswith('<!DOCTYPE')
        )
        root = ET.fromstring(xml_content)
        clips = root.findall('.//asset-clip')
        assert len(clips) == 2

    def test_format_resource(self):
        """Test format resource is correct."""
        intent = create_test_intent()
        generator = FCPXMLGenerator(intent)
        xml_str = generator.generate()

        xml_content = '\n'.join(
            line for line in xml_str.split('\n')
            if not line.strip().startswith('<!DOCTYPE')
        )
        root = ET.fromstring(xml_content)
        format_elem = root.find('.//format')

        assert format_elem is not None
        assert format_elem.get('width') == '1920'
        assert format_elem.get('height') == '1080'


class TestGenerateFcpxml:
    """Tests for generate_fcpxml convenience function."""

    def test_returns_tuple(self):
        """Test function returns tuple of xml and warnings."""
        intent = create_test_intent()
        xml_str, warnings = generate_fcpxml(intent)

        assert isinstance(xml_str, str)
        assert isinstance(warnings, list)
        assert len(xml_str) > 0


class TestValidateFcpxmlStructure:
    """Tests for FCPXML validation."""

    def test_valid_xml(self):
        """Test valid FCPXML passes validation."""
        intent = create_test_intent()
        xml_str, _ = generate_fcpxml(intent)

        is_valid, error = validate_fcpxml_structure(xml_str)
        assert is_valid
        assert error is None

    def test_invalid_xml(self):
        """Test invalid XML fails validation."""
        is_valid, error = validate_fcpxml_structure("not xml")
        assert not is_valid
        assert error is not None

    def test_missing_resources(self):
        """Test XML without resources fails."""
        xml = '<?xml version="1.0"?><fcpxml version="1.11"><library/></fcpxml>'
        is_valid, error = validate_fcpxml_structure(xml)
        assert not is_valid
        assert "resources" in error.lower()
