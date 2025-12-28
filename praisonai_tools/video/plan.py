"""LLM-based content analysis and edit planning."""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

try:
    from .transcribe import Word, TranscriptResult
except ImportError:
    from transcribe import Word, TranscriptResult


# Common filler words to detect
FILLER_WORDS = {
    "um", "uh", "er", "ah", "like", "you know", "i mean", "basically",
    "actually", "literally", "so", "well", "right", "okay", "ok",
}


@dataclass
class Segment:
    """A segment of video to keep or remove."""
    start: float
    end: float
    action: str  # "keep" or "remove"
    reason: str
    category: str  # "filler", "repetition", "silence", "tangent", "content"
    text: Optional[str] = None
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "action": self.action,
            "reason": self.reason,
            "category": self.category,
            "text": self.text,
            "confidence": self.confidence,
        }


@dataclass
class EditPlan:
    """Complete edit plan for a video."""
    segments: List[Segment] = field(default_factory=list)
    original_duration: float = 0.0
    edited_duration: float = 0.0
    removed_duration: float = 0.0
    removal_summary: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "original_duration": self.original_duration,
            "edited_duration": self.edited_duration,
            "removed_duration": self.removed_duration,
            "removal_summary": self.removal_summary,
        }
    
    def get_keep_segments(self) -> List[Segment]:
        """Get only segments marked for keeping."""
        return [s for s in self.segments if s.action == "keep"]
    
    def get_remove_segments(self) -> List[Segment]:
        """Get only segments marked for removal."""
        return [s for s in self.segments if s.action == "remove"]


def detect_fillers(words: List[Word]) -> List[Segment]:
    """Detect filler words in transcript."""
    segments = []
    
    for word in words:
        text_lower = word.text.lower().strip()
        # Remove punctuation for comparison
        text_clean = re.sub(r'[^\w\s]', '', text_lower)
        
        if text_clean in FILLER_WORDS:
            segments.append(Segment(
                start=word.start,
                end=word.end,
                action="remove",
                reason=f"Filler word: '{word.text}'",
                category="filler",
                text=word.text,
                confidence=0.9,
            ))
    
    return segments


def detect_repetitions(words: List[Word], window: int = 3) -> List[Segment]:
    """Detect repeated words/phrases."""
    segments = []
    
    if len(words) < 2:
        return segments
    
    i = 0
    while i < len(words) - 1:
        # Check for immediate repetition
        curr_text = words[i].text.lower().strip()
        curr_clean = re.sub(r'[^\w]', '', curr_text)
        
        if not curr_clean:
            i += 1
            continue
        
        # Look ahead for repetitions
        j = i + 1
        while j < len(words) and j < i + window:
            next_text = words[j].text.lower().strip()
            next_clean = re.sub(r'[^\w]', '', next_text)
            
            if curr_clean == next_clean and len(curr_clean) > 2:
                # Found repetition - mark the first occurrence for removal
                segments.append(Segment(
                    start=words[i].start,
                    end=words[i].end,
                    action="remove",
                    reason=f"Repeated word: '{words[i].text}'",
                    category="repetition",
                    text=words[i].text,
                    confidence=0.85,
                ))
                break
            j += 1
        i += 1
    
    return segments


def detect_silences(
    words: List[Word],
    duration: float,
    min_silence: float = 1.5,
) -> List[Segment]:
    """Detect long silences between words."""
    segments = []
    
    if not words:
        return segments
    
    # Check silence at start
    if words[0].start > min_silence:
        segments.append(Segment(
            start=0,
            end=words[0].start - 0.2,  # Keep small buffer
            action="remove",
            reason=f"Long silence at start: {words[0].start:.1f}s",
            category="silence",
            confidence=0.95,
        ))
    
    # Check silences between words
    for i in range(len(words) - 1):
        gap = words[i + 1].start - words[i].end
        if gap > min_silence:
            segments.append(Segment(
                start=words[i].end + 0.1,
                end=words[i + 1].start - 0.1,
                action="remove",
                reason=f"Long silence: {gap:.1f}s",
                category="silence",
                confidence=0.95,
            ))
    
    # Check silence at end
    if words and duration - words[-1].end > min_silence:
        segments.append(Segment(
            start=words[-1].end + 0.2,
            end=duration,
            action="remove",
            reason=f"Long silence at end: {duration - words[-1].end:.1f}s",
            category="silence",
            confidence=0.95,
        ))
    
    return segments


def create_edit_plan(
    transcript: TranscriptResult,
    duration: float,
    remove_fillers: bool = True,
    remove_repetitions: bool = True,
    remove_silence: bool = True,
    remove_tangents: bool = False,
    min_silence: float = 1.5,
    use_llm: bool = False,
) -> EditPlan:
    """
    Create an edit plan based on transcript analysis.
    
    Args:
        transcript: Transcription result with word-level timestamps
        duration: Total video duration in seconds
        remove_fillers: Remove filler words (um, uh, like, etc.)
        remove_repetitions: Remove repeated words/phrases
        remove_silence: Remove long silences
        remove_tangents: Use LLM to detect off-topic content
        min_silence: Minimum silence duration to remove (seconds)
        use_llm: Use LLM for advanced analysis
        
    Returns:
        EditPlan with segments to keep/remove
    """
    remove_segments = []
    
    if remove_fillers:
        remove_segments.extend(detect_fillers(transcript.words))
    
    if remove_repetitions:
        remove_segments.extend(detect_repetitions(transcript.words))
    
    if remove_silence:
        remove_segments.extend(detect_silences(
            transcript.words, duration, min_silence
        ))
    
    if remove_tangents and use_llm:
        # LLM-based tangent detection would go here
        # For now, skip as it requires more complex implementation
        pass
    
    # Sort by start time
    remove_segments.sort(key=lambda s: s.start)
    
    # Merge overlapping remove segments
    merged_removes = _merge_overlapping(remove_segments)
    
    # Create keep segments from gaps between removes
    all_segments = _create_keep_segments(merged_removes, duration)
    
    # Calculate statistics
    removed_duration = sum(s.end - s.start for s in merged_removes)
    edited_duration = duration - removed_duration
    
    # Summarize by category
    removal_summary = {}
    for seg in merged_removes:
        cat = seg.category
        removal_summary[cat] = removal_summary.get(cat, 0) + (seg.end - seg.start)
    
    return EditPlan(
        segments=all_segments,
        original_duration=duration,
        edited_duration=edited_duration,
        removed_duration=removed_duration,
        removal_summary=removal_summary,
    )


def _merge_overlapping(segments: List[Segment]) -> List[Segment]:
    """Merge overlapping segments."""
    if not segments:
        return []
    
    merged = [segments[0]]
    
    for seg in segments[1:]:
        last = merged[-1]
        # If overlapping or adjacent (within 0.1s)
        if seg.start <= last.end + 0.1:
            # Extend the last segment
            merged[-1] = Segment(
                start=last.start,
                end=max(last.end, seg.end),
                action="remove",
                reason=f"{last.reason}; {seg.reason}",
                category=last.category if last.category == seg.category else "mixed",
                confidence=min(last.confidence, seg.confidence),
            )
        else:
            merged.append(seg)
    
    return merged


def _create_keep_segments(
    remove_segments: List[Segment],
    duration: float,
) -> List[Segment]:
    """Create keep segments from gaps between remove segments."""
    all_segments = []
    current_time = 0.0
    
    for remove_seg in remove_segments:
        # Add keep segment before this remove
        if remove_seg.start > current_time + 0.05:
            all_segments.append(Segment(
                start=current_time,
                end=remove_seg.start,
                action="keep",
                reason="Content",
                category="content",
                confidence=1.0,
            ))
        
        # Add the remove segment
        all_segments.append(remove_seg)
        current_time = remove_seg.end
    
    # Add final keep segment
    if current_time < duration - 0.05:
        all_segments.append(Segment(
            start=current_time,
            end=duration,
            action="keep",
            reason="Content",
            category="content",
            confidence=1.0,
        ))
    
    return all_segments
