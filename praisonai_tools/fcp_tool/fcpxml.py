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

        ET.SubElement(
            resources,
            "format",
            id="r1",
            name=f"FFVideoFormat{fmt.height}p{int(fmt.fps)}",
            frameDuration=fmt.frame_duration_rational,
            width=str(fmt.width),
            height=str(fmt.height),
        )
        # Note: audioChannels and audioSampleRate are NOT valid on format element per DTD

    def _add_asset_resources(self, resources: ET.Element) -> None:
        """Add asset resource definitions."""
        for asset in self.intent.assets:
            asset_elem = ET.SubElement(
                resources,
                "asset",
                id=asset.id,
                name=asset.name,
                uid=asset.uid,
            )
            # Note: src is NOT valid on asset element per DTD - only on media-rep

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
                # audioRate must be one of: 32k, 44.1k, 48k, 88.2k, 96k, 176.4k, 192k
                audio_rate_map = {
                    32000: "32k", 44100: "44.1k", 48000: "48k",
                    88200: "88.2k", 96000: "96k", 176400: "176.4k", 192000: "192k"
                }
                asset_elem.set("audioRate", audio_rate_map.get(asset.audio_rate, "48k"))

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
        # audioRate must be one of: 32k, 44.1k, 48k, 88.2k, 96k, 176.4k, 192k
        audio_rate_map = {
            32000: "32k", 44100: "44.1k", 48000: "48k",
            88200: "88.2k", 96000: "96k", 176400: "176.4k", 192000: "192k"
        }
        sequence.set("audioRate", audio_rate_map.get(self.intent.project.audio.rate, "48k"))

        spine = ET.SubElement(sequence, "spine")

        self._add_timeline_clips(spine)
        # Note: markers are added inside asset-clips, not on sequence
        # Sequence content must be (note?, spine, metadata?) per DTD

    def _add_timeline_clips(self, spine: ET.Element) -> None:
        """Add clips to the spine based on timeline segments."""
        primary_segments = [s for s in self.intent.timeline.segments if s.lane == 0]
        connected_segments = [s for s in self.intent.timeline.segments if s.lane != 0]

        primary_segments.sort(key=lambda s: self._rational_to_frames(s.offset))

        for i, segment in enumerate(primary_segments):
            self._add_asset_clip(spine, segment, is_first=(i == 0))

        for segment in connected_segments:
            self._warnings.append(
                f"Connected clip (lane={segment.lane}) for asset '{segment.asset_id}' "
                "added as primary storyline clip - connected clips not fully supported in v1"
            )
            self._add_asset_clip(spine, segment)

    def _add_asset_clip(self, parent: ET.Element, segment: Segment, is_first: bool = False) -> None:
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
            ref=asset.id,
            offset=segment.offset,
            duration=segment.duration,
            start=segment.start,
        )

        if asset.has_audio:
            clip.set("audioRole", segment.role.value if segment.role else "dialogue")

        if segment.volume is not None and segment.volume != 1.0:
            adjust = ET.SubElement(clip, "adjust-volume")
            adjust.set("amount", f"{segment.volume * 100 - 100:+.1f}dB")

        # Add markers inside the clip (first clip gets all markers)
        if is_first:
            for marker in self.intent.timeline.markers:
                ET.SubElement(
                    clip,
                    "marker",
                    start=marker.start,
                    duration=marker.duration,
                    value=marker.name,
                )

    # Markers are now added inside asset-clips in _add_asset_clip method

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


def align_to_frame_boundary(time_str: str, fps: float = 30.0) -> str:
    """
    Align a rational time string to the nearest frame boundary.
    
    Args:
        time_str: Rational time string like "12345/3000s"
        fps: Frames per second (default 30.0)
        
    Returns:
        Frame-aligned rational time string
    """
    parts = time_str.rstrip("s").split("/")
    if len(parts) != 2:
        return time_str
    
    numerator = int(parts[0])
    timescale = int(parts[1])
    
    # Calculate frame duration in timescale units
    frame_duration = int(timescale / fps)
    
    # Round to nearest frame boundary
    aligned = round(numerator / frame_duration) * frame_duration
    
    return f"{aligned}/{timescale}s"


def import_fcpxml_silent(fcpxml_path: str, timeout: int = 30) -> dict:
    """
    Import FCPXML into Final Cut Pro with automatic dialog handling.
    
    Args:
        fcpxml_path: Path to the FCPXML file
        timeout: Maximum seconds to wait for import
        
    Returns:
        Dict with success status and any messages
    """
    import subprocess
    import time
    import os
    from datetime import datetime
    
    result = {
        "success": False,
        "fcpxml_path": fcpxml_path,
        "messages": [],
    }
    
    if not os.path.exists(fcpxml_path):
        result["messages"].append(f"File not found: {fcpxml_path}")
        return result
    
    # Open FCPXML in FCP
    subprocess.run(['open', '-a', 'Final Cut Pro', fcpxml_path])
    time.sleep(3)
    
    # Auto-handle dialogs
    auto_script = '''
    tell application "System Events"
        tell process "Final Cut Pro"
            set frontmost to true
            delay 0.5
            
            repeat 10 times
                set windowNames to name of every window
                
                if (windowNames as string) contains "Import XML" then
                    keystroke tab
                    delay 0.2
                    keystroke return
                    delay 2
                else if (windowNames as string) contains "Open Library" then
                    key code 53
                    delay 0.5
                else if (count of windowNames) > 1 then
                    keystroke return
                    delay 1
                else
                    exit repeat
                end if
            end repeat
            
            return "done"
        end tell
    end tell
    '''
    
    try:
        subprocess.run(['osascript', '-e', auto_script], capture_output=True, timeout=timeout)
        result["messages"].append("Dialog handling completed")
    except subprocess.TimeoutExpired:
        result["messages"].append("Dialog handling timed out")
    
    # Check if library was modified
    lib_path = os.path.expanduser("~/Movies/Untitled.fcpbundle/CurrentVersion.flexolibrary")
    if os.path.exists(lib_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(lib_path))
        age = (datetime.now() - mtime).total_seconds()
        if age < 60:
            result["success"] = True
            result["messages"].append(f"Library modified {age:.0f}s ago")
    
    return result
