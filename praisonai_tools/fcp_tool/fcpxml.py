"""
FCPXML Generator for Final Cut Pro Integration

Converts EditIntent to valid FCPXML 1.11 format.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional
from xml.dom import minidom

from .intent import EditIntent, Segment


class FCPXMLGenerator:
    """
    Generates FCPXML from EditIntent.
    
    FCPXML is the interchange format for Final Cut Pro. This generator
    produces valid FCPXML 1.11 that can be imported into FCP.
    """

    FCPXML_VERSION = "1.11"

    def __init__(self, intent: EditIntent):
        """
        Initialize the generator with an EditIntent.
        
        Args:
            intent: The EditIntent to convert to FCPXML
        """
        self.intent = intent
        self._warnings: list[str] = []

    def generate(self, pretty_print: bool = True) -> str:
        """
        Generate FCPXML string from the intent.
        
        Args:
            pretty_print: Whether to format the XML with indentation
            
        Returns:
            FCPXML string
        """
        self._warnings = list(self.intent.get_warnings())

        root = ET.Element("fcpxml", version=self.FCPXML_VERSION)

        resources = ET.SubElement(root, "resources")
        self._add_format_resource(resources)
        self._add_asset_resources(resources)

        library = ET.SubElement(root, "library")
        event = ET.SubElement(library, "event", name=self.intent.project.name)
        self._add_project(event)

        xml_str = ET.tostring(root, encoding="unicode")

        if pretty_print:
            xml_str = self._pretty_print(xml_str)

        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        doctype = '<!DOCTYPE fcpxml>\n'

        return xml_declaration + doctype + xml_str

    def get_warnings(self) -> list[str]:
        """Get warnings generated during FCPXML generation."""
        return self._warnings

    def _add_format_resource(self, resources: ET.Element) -> None:
        """Add the format resource definition."""
        fmt = self.intent.project.format
        audio = self.intent.project.audio

        format_elem = ET.SubElement(
            resources,
            "format",
            id="r1",
            name=f"{fmt.width}x{fmt.height}p{fmt.fps:.2f}".rstrip("0").rstrip("."),
            frameDuration=fmt.frame_duration_rational,
            width=str(fmt.width),
            height=str(fmt.height),
        )
        format_elem.set("audioChannels", str(audio.channels))
        format_elem.set("audioSampleRate", str(audio.rate))

    def _add_asset_resources(self, resources: ET.Element) -> None:
        """Add asset resource definitions."""
        for asset in self.intent.assets:
            asset_elem = ET.SubElement(
                resources,
                "asset",
                id=asset.id,
                name=asset.name,
                uid=asset.uid,
                src=asset.get_src_url(),
            )

            if asset.has_video:
                asset_elem.set("hasVideo", "1")
                if asset.format_ref:
                    asset_elem.set("format", asset.format_ref)
                else:
                    asset_elem.set("format", "r1")

            if asset.has_audio:
                asset_elem.set("hasAudio", "1")
                asset_elem.set("audioSources", "1")
                asset_elem.set("audioChannels", str(asset.audio_channels))
                asset_elem.set("audioRate", str(asset.audio_rate))

            if asset.duration_rational:
                asset_elem.set("duration", asset.duration_rational)

            ET.SubElement(
                asset_elem,
                "media-rep",
                kind="original-media",
                src=asset.get_src_url(),
            )

    def _add_project(self, event: ET.Element) -> None:
        """Add the project with sequence and spine."""
        project = ET.SubElement(
            event,
            "project",
            name=self.intent.project.name,
        )

        total_duration = self._calculate_total_duration()

        sequence = ET.SubElement(
            project,
            "sequence",
            format="r1",
            duration=total_duration,
            tcStart="0/2500s",
            tcFormat="NDF",
        )
        sequence.set("audioLayout", self.intent.project.audio.layout.value)
        sequence.set("audioRate", f"{self.intent.project.audio.rate}/1s")

        spine = ET.SubElement(sequence, "spine")

        self._add_timeline_clips(spine)

        self._add_markers(sequence)

    def _add_timeline_clips(self, spine: ET.Element) -> None:
        """Add clips to the spine based on timeline segments."""
        primary_segments = [s for s in self.intent.timeline.segments if s.lane == 0]
        connected_segments = [s for s in self.intent.timeline.segments if s.lane != 0]

        primary_segments.sort(key=lambda s: self._rational_to_frames(s.offset))

        for segment in primary_segments:
            self._add_asset_clip(spine, segment)

        for segment in connected_segments:
            self._warnings.append(
                f"Connected clip (lane={segment.lane}) for asset '{segment.asset_id}' "
                "added as primary storyline clip - connected clips not fully supported in v1"
            )
            self._add_asset_clip(spine, segment)

    def _add_asset_clip(self, parent: ET.Element, segment: Segment) -> None:
        """Add an asset-clip element for a segment."""
        asset = self.intent.get_asset_by_id(segment.asset_id)
        if not asset:
            self._warnings.append(f"Asset not found for segment: {segment.asset_id}")
            return

        clip_name = segment.name or asset.name

        clip = ET.SubElement(
            parent,
            "asset-clip",
            name=clip_name,
            offset=segment.offset,
            ref=asset.id,
            duration=segment.duration,
            start=segment.start,
        )

        if asset.has_audio:
            clip.set("audioRole", segment.role.value if segment.role else "dialogue")

        if segment.volume is not None and segment.volume != 1.0:
            adjust = ET.SubElement(clip, "adjust-volume")
            adjust.set("amount", f"{segment.volume * 100 - 100:+.1f}dB")

    def _add_markers(self, sequence: ET.Element) -> None:
        """Add markers to the sequence."""
        for marker in self.intent.timeline.markers:
            ET.SubElement(
                sequence,
                "marker",
                start=marker.start,
                duration=marker.duration,
                value=marker.name,
            )

    def _calculate_total_duration(self) -> str:
        """Calculate total timeline duration from segments."""
        if not self.intent.timeline.segments:
            return "0/2500s"

        max_end = 0
        for segment in self.intent.timeline.segments:
            offset_frames = self._rational_to_frames(segment.offset)
            duration_frames = self._rational_to_frames(segment.duration)
            end_frames = offset_frames + duration_frames
            max_end = max(max_end, end_frames)

        timescale = self.intent.project.format.get_timescale()
        return f"{max_end}/{timescale}s"

    def _rational_to_frames(self, rational: str) -> int:
        """Convert rational time to frame count."""
        parts = rational.rstrip("s").split("/")
        if len(parts) != 2:
            return 0
        return int(parts[0])

    def _pretty_print(self, xml_str: str) -> str:
        """Format XML with proper indentation."""
        try:
            dom = minidom.parseString(xml_str)
            pretty = dom.toprettyxml(indent="  ")
            lines = pretty.split("\n")
            lines = [line for line in lines if line.strip() and not line.startswith("<?xml")]
            return "\n".join(lines)
        except Exception:
            return xml_str


def generate_fcpxml(intent: EditIntent, pretty_print: bool = True) -> tuple[str, list[str]]:
    """
    Convenience function to generate FCPXML from an EditIntent.
    
    Args:
        intent: The EditIntent to convert
        pretty_print: Whether to format the XML
        
    Returns:
        Tuple of (fcpxml_string, warnings_list)
    """
    generator = FCPXMLGenerator(intent)
    xml = generator.generate(pretty_print=pretty_print)
    return xml, generator.get_warnings()


def validate_fcpxml_structure(xml_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate basic FCPXML structure.
    
    Args:
        xml_str: FCPXML string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        lines = xml_str.split("\n")
        xml_content = "\n".join(
            line for line in lines 
            if not line.strip().startswith("<!DOCTYPE")
        )
        root = ET.fromstring(xml_content)

        if root.tag != "fcpxml":
            return False, f"Root element must be 'fcpxml', got '{root.tag}'"

        resources = root.find("resources")
        if resources is None:
            return False, "Missing 'resources' element"

        library = root.find("library")
        if library is None:
            return False, "Missing 'library' element"

        event = library.find("event")
        if event is None:
            return False, "Missing 'event' element in library"

        project = event.find("project")
        if project is None:
            return False, "Missing 'project' element in event"

        sequence = project.find("sequence")
        if sequence is None:
            return False, "Missing 'sequence' element in project"

        spine = sequence.find("spine")
        if spine is None:
            return False, "Missing 'spine' element in sequence"

        return True, None

    except ET.ParseError as e:
        return False, f"XML parse error: {e}"
