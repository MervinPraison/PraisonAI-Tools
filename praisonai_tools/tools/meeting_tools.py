"""Meeting Agent Tools for PraisonAI Agents.

Eight agent-callable ``@tool`` functions covering the Phase 1 meeting-agent
pipeline: transcription, meetings CRUD, summarisation, action-item extraction,
and RAG indexing/search.

Tools
-----
1. ``transcribe_file``       - Whisper transcription with segment timestamps.
2. ``save_meeting``          - Persist a meeting record (returns ``meeting_id``).
3. ``get_meeting``           - Fetch a full meeting record.
4. ``list_meetings``         - List meetings (limit/offset).
5. ``summarize_transcript``  - Structured summary (map-reduce for long input).
6. ``extract_action_items``  - Structured action items.
7. ``index_meeting``         - Chunk/embed/upsert into a vector store (idempotent).
8. ``search_meetings``       - Ranked cross-meeting semantic search.

Dependency hygiene
-------------------
``openai`` and ``chromadb`` are **lazy-imported inside functions**, never at
module import time. They are optional extras::

    pip install praisonai-tools[meeting]

Meetings are persisted in a small SQLite database (Python stdlib) under the app
data dir. This is a thin, swappable persistence layer: when the canonical
PAI-MEET-CORE schema is available it can back these same CRUD wrappers.

All tool outputs use deterministic serialisation (stable field order / sorted
keys) so results are reproducible.

Environment Variables
---------------------
    OPENAI_API_KEY      Required for transcription/summaries/embeddings.
    OPENAI_BASE_URL     Optional custom OpenAI-compatible endpoint.
    PRAISONAI_MEETINGS_DB   Optional path to the SQLite meetings database.
    PRAISONAI_MEETINGS_DIR  Optional app data dir (db + vector store live here).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from praisonai_tools.tools.decorator import tool

logger = logging.getLogger(__name__)

# Chunking / embedding defaults (issue spec).
_CHUNK_SIZE_TOKENS = 500
_CHUNK_OVERLAP_TOKENS = 50
_SUMMARY_CHUNK_TOKENS = 6000
_SUMMARY_OVERLAP_TOKENS = 200
_EMBEDDING_MODEL = "text-embedding-3-small"
_CHAT_MODEL = "gpt-4o-mini"
_WHISPER_MODEL = "whisper-1"
_COLLECTION = "meetings"

# Rough token->char ratio used only for deterministic, dependency-free chunking.
_CHARS_PER_TOKEN = 4


# ── Paths / persistence ─────────────────────────────────────────────


def _app_dir() -> Path:
    """Return the app data directory (created if missing)."""
    env = os.getenv("PRAISONAI_MEETINGS_DIR")
    base = Path(env) if env else Path.home() / ".praisonai" / "meetings"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _db_path() -> str:
    env = os.getenv("PRAISONAI_MEETINGS_DB")
    if env:
        Path(env).parent.mkdir(parents=True, exist_ok=True)
        return env
    return str(_app_dir() / "meetings.db")


def _connect() -> sqlite3.Connection:
    """Open the meetings DB, creating the schema on first use."""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meetings (
            meeting_id TEXT PRIMARY KEY,
            title      TEXT NOT NULL,
            source     TEXT,
            metadata   TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def _row_to_meeting(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a DB row to a deterministic meeting dict (stable key order)."""
    try:
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
    except (ValueError, TypeError):
        metadata = {}
    return {
        "created_at": row["created_at"],
        "meeting_id": row["meeting_id"],
        "metadata": metadata,
        "source": row["source"],
        "title": row["title"],
    }


# ── Lazy clients ────────────────────────────────────────────────────


def _get_openai_client():
    """Lazily construct an OpenAI client. Raises clear errors on misconfig."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is required. Set it in the environment before "
            "calling meeting transcription/summarisation/embedding tools."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - trivial
        raise ImportError(
            "openai package required. Install with: pip install praisonai-tools[meeting]"
        ) from exc
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def _get_vector_collection():
    """Lazily open (or create) the persistent Chroma collection."""
    try:
        import chromadb
    except ImportError as exc:  # pragma: no cover - trivial
        raise ImportError(
            "chromadb package required. Install with: pip install praisonai-tools[meeting]"
        ) from exc
    client = chromadb.PersistentClient(path=str(_app_dir() / "chroma"))
    return client.get_or_create_collection(_COLLECTION)


def _embed(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts with the configured embedding model."""
    client = _get_openai_client()
    resp = client.embeddings.create(model=_EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in resp.data]


# ── Chunking helpers ────────────────────────────────────────────────


def _chunk_text(text: str, size_tokens: int, overlap_tokens: int) -> List[str]:
    """Split text into overlapping chunks by approximate token size.

    Uses a deterministic character-window approximation so no tokenizer
    dependency is needed. Returns a list of non-empty chunk strings.
    """
    if not text:
        return []
    size = max(1, size_tokens * _CHARS_PER_TOKEN)
    overlap = max(0, min(overlap_tokens * _CHARS_PER_TOKEN, size - 1))
    step = size - overlap
    chunks: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        chunk = text[start : start + size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


# ── LLM JSON helpers ────────────────────────────────────────────────


def _chat_json(system: str, user: str) -> Dict[str, Any]:
    """Call the chat model requesting a JSON object and parse it."""
    client = _get_openai_client()
    resp = client.chat.completions.create(
        model=_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = resp.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except (ValueError, TypeError):
        return {}


# ── 1. transcribe_file ──────────────────────────────────────────────


@tool
def transcribe_file(media_path: str) -> Dict[str, Any]:
    """Transcribe an audio/video file to text with segment timestamps.

    Uses OpenAI Whisper (``whisper-1``) via the audio transcriptions API and
    returns word/segment level timing.

    Args:
        media_path: Path to the audio or video file to transcribe.

    Returns:
        Dict with ``text``, ``segments`` (start/end/text), ``duration_seconds``
        and ``language``. On failure returns ``{"error": "..."}`` with a clear
        message (missing file, API 403 key permissions, timeout, empty audio).
    """
    path = Path(media_path)
    if not media_path or not path.exists():
        return {"error": f"Media file not found: {media_path}"}

    try:
        client = _get_openai_client()
    except (ValueError, ImportError) as exc:
        return {"error": str(exc)}

    def _do_transcribe():
        with open(path, "rb") as audio_file:
            return client.audio.transcriptions.create(
                model=_WHISPER_MODEL,
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

    try:
        response = _do_transcribe()
    except Exception as exc:  # noqa: BLE001 - map to clear messages
        message = str(exc)
        status = getattr(exc, "status_code", None)
        exc_name = type(exc).__name__.lower()
        if status == 403 or "403" in message or "permission" in message.lower():
            return {"error": "Transcription failed: API key lacks permissions (403)."}
        if "timeout" in exc_name or "timeout" in message.lower():
            # Retry once, then fail with a clear message.
            try:
                response = _do_transcribe()
            except Exception:  # noqa: BLE001
                return {"error": "Transcription failed: request timed out after retry."}
        else:
            return {"error": f"Transcription failed: {message}"}

    text = (getattr(response, "text", "") or "").strip()
    segments_raw = getattr(response, "segments", None) or []
    segments = [
        {
            "end": float(getattr(seg, "end", 0.0)),
            "start": float(getattr(seg, "start", 0.0)),
            "text": (getattr(seg, "text", "") or "").strip(),
        }
        for seg in segments_raw
    ]

    if not text and not segments:
        return {"error": "No speech detected in recording"}

    return {
        "duration_seconds": float(getattr(response, "duration", 0.0) or 0.0),
        "language": getattr(response, "language", "unknown") or "unknown",
        "segments": segments,
        "text": text,
    }


# ── 2-4. Meetings CRUD ──────────────────────────────────────────────


@tool
def save_meeting(
    title: str,
    source: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Persist a meeting record and return its generated ``meeting_id``.

    Thin wrapper over the meetings persistence layer (SQLite by default).

    Args:
        title: Human-readable meeting title.
        source: Optional origin of the meeting (e.g. file path, URL).
        metadata: Optional JSON-serialisable metadata dict.

    Returns:
        Dict ``{"meeting_id": "<uuid>"}`` or ``{"error": "..."}``.
    """
    if not title:
        return {"error": "title is required"}
    meeting_id = str(uuid.uuid4())
    from datetime import datetime, timezone

    created_at = datetime.now(timezone.utc).isoformat()
    try:
        conn = _connect()
        with conn:
            conn.execute(
                "INSERT INTO meetings (meeting_id, title, source, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    meeting_id,
                    title,
                    source,
                    json.dumps(metadata or {}, sort_keys=True),
                    created_at,
                ),
            )
        conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.error("save_meeting error: %s", exc)
        return {"error": str(exc)}
    return {"meeting_id": meeting_id}


@tool
def get_meeting(meeting_id: str) -> Dict[str, Any]:
    """Fetch a full meeting record by id.

    Args:
        meeting_id: The meeting identifier returned by ``save_meeting``.

    Returns:
        The meeting record dict, or ``{"error": "..."}`` if not found.
    """
    if not meeting_id:
        return {"error": "meeting_id is required"}
    try:
        conn = _connect()
        row = conn.execute(
            "SELECT * FROM meetings WHERE meeting_id = ?", (meeting_id,)
        ).fetchone()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.error("get_meeting error: %s", exc)
        return {"error": str(exc)}
    if row is None:
        return {"error": f"Meeting not found: {meeting_id}"}
    return _row_to_meeting(row)


@tool
def list_meetings(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """List stored meetings, most recent first.

    Args:
        limit: Maximum number of meetings to return (default 20).
        offset: Number of meetings to skip for pagination (default 0).

    Returns:
        A list of meeting record dicts (possibly empty), or a single-element
        list ``[{"error": "..."}]`` on failure.
    """
    try:
        limit = max(0, int(limit))
        offset = max(0, int(offset))
        conn = _connect()
        rows = conn.execute(
            "SELECT * FROM meetings ORDER BY created_at DESC, meeting_id DESC "
            "LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.error("list_meetings error: %s", exc)
        return [{"error": str(exc)}]
    return [_row_to_meeting(r) for r in rows]


# ── 5. summarize_transcript ─────────────────────────────────────────


def _summarize_chunk(transcript: str) -> Dict[str, Any]:
    system = (
        "You are a meeting summariser. Return a JSON object with keys: "
        "'summary' (2-3 paragraph string), 'decisions' (array of strings), "
        "'topics' (array of strings), and 'key_quotes' (array of objects with "
        "'speaker' and 'quote'). Base output only on the transcript."
    )
    return _chat_json(system, transcript)


def _merge_summaries(parts: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged_summary = "\n\n".join(
        str(p.get("summary", "")).strip() for p in parts if p.get("summary")
    )
    decisions: List[str] = []
    topics: List[str] = []
    quotes: List[Dict[str, Any]] = []
    for p in parts:
        for d in p.get("decisions", []) or []:
            if d not in decisions:
                decisions.append(d)
        for t in p.get("topics", []) or []:
            if t not in topics:
                topics.append(t)
        for q in p.get("key_quotes", []) or []:
            quotes.append(
                {"quote": q.get("quote", ""), "speaker": q.get("speaker")}
            )
    return {
        "decisions": decisions,
        "key_quotes": quotes,
        "summary": merged_summary,
        "topics": topics,
    }


@tool
def summarize_transcript(transcript: str) -> Dict[str, Any]:
    """Summarise a meeting transcript into structured JSON.

    For long transcripts a map-reduce strategy is used: the transcript is split
    into overlapping chunks, each is summarised, and the partial summaries are
    merged.

    Args:
        transcript: The full plain-text transcript.

    Returns:
        Dict with ``summary`` (str), ``decisions`` (list), ``topics`` (list) and
        ``key_quotes`` (list of ``{speaker, quote}``). ``{"error": "..."}`` on
        failure.
    """
    if not transcript or not transcript.strip():
        return {"error": "transcript is required"}
    try:
        chunks = _chunk_text(
            transcript, _SUMMARY_CHUNK_TOKENS, _SUMMARY_OVERLAP_TOKENS
        )
        if len(chunks) <= 1:
            result = _summarize_chunk(transcript)
        else:
            partials = [_summarize_chunk(c) for c in chunks]
            result = _merge_summaries(partials)
    except (ValueError, ImportError) as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.error("summarize_transcript error: %s", exc)
        return {"error": str(exc)}

    return {
        "decisions": result.get("decisions", []) or [],
        "key_quotes": result.get("key_quotes", []) or [],
        "summary": result.get("summary", "") or "",
        "topics": result.get("topics", []) or [],
    }


# ── 6. extract_action_items ─────────────────────────────────────────


@tool
def extract_action_items(transcript: str) -> Dict[str, Any]:
    """Extract action items from a transcript as structured JSON.

    Args:
        transcript: The full plain-text transcript.

    Returns:
        Dict ``{"action_items": [{description, owner, due_date, priority}, ...]}``
        or ``{"error": "..."}`` on failure.
    """
    if not transcript or not transcript.strip():
        return {"error": "transcript is required"}
    system = (
        "You extract action items from meeting transcripts. Return a JSON object "
        "with a single key 'action_items': an array of objects each with keys "
        "'description' (string), 'owner' (string or null), 'due_date' (ISO date "
        "string or null), and 'priority' (one of 'low', 'medium', 'high' or null). "
        "Only include real, actionable items."
    )
    try:
        result = _chat_json(system, transcript)
    except (ValueError, ImportError) as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.error("extract_action_items error: %s", exc)
        return {"error": str(exc)}

    items = result.get("action_items", []) or []
    normalised = [
        {
            "description": it.get("description", ""),
            "due_date": it.get("due_date"),
            "owner": it.get("owner"),
            "priority": it.get("priority"),
        }
        for it in items
        if isinstance(it, dict)
    ]
    return {"action_items": normalised}


# ── 7. index_meeting ────────────────────────────────────────────────


@tool
def index_meeting(meeting_id: str, transcript: Optional[str] = None) -> Dict[str, Any]:
    """Chunk, embed and upsert a meeting transcript into the vector store.

    Idempotent: any existing chunks for ``meeting_id`` are deleted first, so
    re-indexing after an update never duplicates chunks.

    Args:
        meeting_id: The meeting identifier.
        transcript: Optional transcript text. If omitted, the transcript is read
            from the stored meeting metadata (``metadata['transcript']``).

    Returns:
        Dict ``{"chunks_indexed": N}`` or ``{"error": "..."}``.
    """
    if not meeting_id:
        return {"error": "meeting_id is required"}

    meeting = get_meeting(meeting_id)
    if "error" in meeting:
        return meeting

    text = transcript
    title = meeting.get("title", "")
    if not text:
        text = (meeting.get("metadata") or {}).get("transcript")
    if not text or not str(text).strip():
        return {"error": "No transcript available to index"}

    try:
        collection = _get_vector_collection()
        # Delete existing chunks for this meeting so re-index is idempotent.
        collection.delete(where={"meeting_id": meeting_id})

        chunks = _chunk_text(text, _CHUNK_SIZE_TOKENS, _CHUNK_OVERLAP_TOKENS)
        if not chunks:
            return {"chunks_indexed": 0}

        embeddings = _embed(chunks)
        ids = [f"{meeting_id}:{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "chunk_index": i,
                "meeting_id": meeting_id,
                "timestamp_end": 0.0,
                "timestamp_start": 0.0,
                "title": title,
            }
            for i in range(len(chunks))
        ]
        collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )
    except (ValueError, ImportError) as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.error("index_meeting error: %s", exc)
        return {"error": str(exc)}

    return {"chunks_indexed": len(chunks)}


# ── 8. search_meetings ──────────────────────────────────────────────


@tool
def search_meetings(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Semantic search across indexed meetings, returning ranked snippets.

    Args:
        query: The natural-language search query.
        limit: Maximum number of results to return (default 5).

    Returns:
        A list of ``{meeting_id, title, snippet, score, timestamp_start}`` dicts
        ranked by relevance (best first), or ``[{"error": "..."}]`` on failure.
    """
    if not query or not query.strip():
        return [{"error": "query is required"}]
    try:
        limit = max(1, int(limit))
        collection = _get_vector_collection()
        query_embedding = _embed([query])[0]
        results = collection.query(
            query_embeddings=[query_embedding], n_results=limit
        )
    except (ValueError, ImportError) as exc:
        return [{"error": str(exc)}]
    except Exception as exc:  # noqa: BLE001
        logger.error("search_meetings error: %s", exc)
        return [{"error": str(exc)}]

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    items: List[Dict[str, Any]] = []
    for i, doc in enumerate(documents):
        meta = metadatas[i] if i < len(metadatas) else {}
        distance = distances[i] if i < len(distances) else None
        score = round(1.0 - distance, 6) if distance is not None else None
        snippet = (doc or "")[:280]
        items.append(
            {
                "meeting_id": meta.get("meeting_id"),
                "score": score,
                "snippet": snippet,
                "timestamp_start": meta.get("timestamp_start", 0.0),
                "title": meta.get("title"),
            }
        )
    return items
