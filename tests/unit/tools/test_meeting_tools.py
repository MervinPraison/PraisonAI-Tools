"""Unit tests for meeting_tools.

All external clients (OpenAI, Chroma) are mocked so no network or heavy
dependency is required. The SQLite persistence is redirected to a temp dir.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from praisonai_tools.tools import meeting_tools as mt


@pytest.fixture(autouse=True)
def _isolated_app_dir(tmp_path, monkeypatch):
    """Point the meetings DB and vector store at a temp dir per test."""
    monkeypatch.setenv("PRAISONAI_MEETINGS_DIR", str(tmp_path))
    monkeypatch.setenv("PRAISONAI_MEETINGS_DB", str(tmp_path / "meetings.db"))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    yield


# ── transcribe_file ─────────────────────────────────────────────────


class TestTranscribeFile:
    def test_missing_file(self):
        result = mt.transcribe_file.__wrapped__("/no/such/file.mp3")
        assert "error" in result
        assert "not found" in result["error"].lower()

    def _fake_response(self):
        return SimpleNamespace(
            text="Good morning everyone",
            duration=12.5,
            language="en",
            segments=[
                SimpleNamespace(start=0.0, end=4.2, text="Good morning everyone"),
            ],
        )

    def test_success(self, tmp_path):
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"fake")
        client = MagicMock()
        client.audio.transcriptions.create.return_value = self._fake_response()
        with patch.object(mt, "_get_openai_client", return_value=client):
            result = mt.transcribe_file.__wrapped__(str(audio))
        assert result["text"] == "Good morning everyone"
        assert result["language"] == "en"
        assert result["duration_seconds"] == 12.5
        assert result["segments"][0]["start"] == 0.0
        assert result["segments"][0]["end"] == 4.2

    def test_403_error_mapping(self, tmp_path):
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"fake")
        exc = Exception("403 forbidden")
        setattr(exc, "status_code", 403)
        client = MagicMock()
        client.audio.transcriptions.create.side_effect = exc
        with patch.object(mt, "_get_openai_client", return_value=client):
            result = mt.transcribe_file.__wrapped__(str(audio))
        assert "403" in result["error"] or "permission" in result["error"].lower()

    def test_timeout_retries_once_then_fails(self, tmp_path):
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"fake")

        class TimeoutError_(Exception):
            pass

        client = MagicMock()
        client.audio.transcriptions.create.side_effect = TimeoutError_("timeout")
        with patch.object(mt, "_get_openai_client", return_value=client):
            result = mt.transcribe_file.__wrapped__(str(audio))
        assert "timed out" in result["error"].lower()
        assert client.audio.transcriptions.create.call_count == 2

    def test_empty_audio(self, tmp_path):
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"fake")
        client = MagicMock()
        client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="", duration=0.0, language="en", segments=[]
        )
        with patch.object(mt, "_get_openai_client", return_value=client):
            result = mt.transcribe_file.__wrapped__(str(audio))
        assert result["error"] == "No speech detected in recording"


# ── Meetings CRUD ───────────────────────────────────────────────────


class TestMeetingsCRUD:
    def test_save_and_get(self):
        saved = mt.save_meeting.__wrapped__(
            title="Weekly standup", source="file.mp3", metadata={"team": "eng"}
        )
        mid = saved["meeting_id"]
        assert mid
        record = mt.get_meeting.__wrapped__(mid)
        assert record["title"] == "Weekly standup"
        assert record["source"] == "file.mp3"
        assert record["metadata"] == {"team": "eng"}

    def test_save_requires_title(self):
        assert "error" in mt.save_meeting.__wrapped__(title="")

    def test_get_not_found(self):
        assert "error" in mt.get_meeting.__wrapped__("nope")

    def test_list(self):
        mt.save_meeting.__wrapped__(title="A")
        mt.save_meeting.__wrapped__(title="B")
        meetings = mt.list_meetings.__wrapped__(limit=10, offset=0)
        assert len(meetings) == 2
        titles = {m["title"] for m in meetings}
        assert titles == {"A", "B"}

    def test_list_pagination(self):
        for i in range(3):
            mt.save_meeting.__wrapped__(title=f"M{i}")
        page = mt.list_meetings.__wrapped__(limit=1, offset=1)
        assert len(page) == 1


# ── summarize_transcript ────────────────────────────────────────────


class TestSummarize:
    def test_requires_transcript(self):
        assert "error" in mt.summarize_transcript.__wrapped__("")

    def test_single_chunk(self):
        payload = {
            "summary": "It was a good meeting.",
            "decisions": ["Ship on Friday"],
            "topics": ["release"],
            "key_quotes": [{"speaker": "Alex", "quote": "Ship it"}],
        }
        with patch.object(mt, "_chat_json", return_value=payload):
            result = mt.summarize_transcript.__wrapped__("short transcript")
        assert result["summary"] == "It was a good meeting."
        assert result["decisions"] == ["Ship on Friday"]
        assert result["topics"] == ["release"]
        assert result["key_quotes"][0]["quote"] == "Ship it"

    def test_map_reduce_merges_chunks(self):
        long_text = "word " * 8000  # forces multiple summary chunks
        calls = []

        def fake_chat(system, user):
            idx = len(calls)
            calls.append(user)
            return {
                "summary": f"para{idx}",
                "decisions": [f"d{idx}"],
                "topics": ["t"],
                "key_quotes": [{"speaker": None, "quote": f"q{idx}"}],
            }

        with patch.object(mt, "_chat_json", side_effect=fake_chat):
            result = mt.summarize_transcript.__wrapped__(long_text)

        assert len(calls) > 1
        assert "para0" in result["summary"]
        assert "t" in result["topics"]  # deduped
        assert result["topics"].count("t") == 1
        assert len(result["decisions"]) == len(calls)


# ── extract_action_items ────────────────────────────────────────────


class TestActionItems:
    def test_requires_transcript(self):
        assert "error" in mt.extract_action_items.__wrapped__("")

    def test_returns_valid_schema(self):
        payload = {
            "action_items": [
                {
                    "description": "Fix API bug",
                    "owner": "Alex",
                    "due_date": "2026-09-05",
                    "priority": "high",
                }
            ]
        }
        with patch.object(mt, "_chat_json", return_value=payload):
            result = mt.extract_action_items.__wrapped__("transcript")
        item = result["action_items"][0]
        assert set(item.keys()) == {"description", "owner", "due_date", "priority"}
        assert item["owner"] == "Alex"

    def test_handles_empty(self):
        with patch.object(mt, "_chat_json", return_value={}):
            result = mt.extract_action_items.__wrapped__("transcript")
        assert result["action_items"] == []


# ── Fake in-memory vector collection ────────────────────────────────


class _FakeCollection:
    """Minimal Chroma-like collection using cosine-ish distance on tags."""

    def __init__(self):
        self.store = {}  # id -> (document, metadata, embedding)

    def delete(self, where=None):
        if not where:
            self.store.clear()
            return
        mid = where.get("meeting_id")
        for k in [k for k, v in self.store.items() if v[1].get("meeting_id") == mid]:
            del self.store[k]

    def add(self, ids, documents, embeddings, metadatas):
        for i, _id in enumerate(ids):
            self.store[_id] = (documents[i], metadatas[i], embeddings[i])

    def query(self, query_embeddings, n_results):
        q = query_embeddings[0]

        def dist(emb):
            return sum((a - b) ** 2 for a, b in zip(q, emb))

        ranked = sorted(self.store.items(), key=lambda kv: dist(kv[1][2]))
        ranked = ranked[:n_results]
        return {
            "documents": [[v[0] for _, v in ranked]],
            "metadatas": [[v[1] for _, v in ranked]],
            "distances": [[dist(v[2]) for _, v in ranked]],
        }


class TestIndexAndSearch:
    def _embed_map(self):
        # deterministic embeddings keyed by content keyword
        def fake_embed(texts):
            out = []
            for t in texts:
                if "apple" in t.lower():
                    out.append([1.0, 0.0])
                elif "banana" in t.lower():
                    out.append([0.0, 1.0])
                else:
                    out.append([0.5, 0.5])
            return out

        return fake_embed

    def test_index_and_rank(self):
        coll = _FakeCollection()
        m1 = mt.save_meeting.__wrapped__(title="Apple meeting")["meeting_id"]
        m2 = mt.save_meeting.__wrapped__(title="Banana meeting")["meeting_id"]
        with patch.object(mt, "_get_vector_collection", return_value=coll), patch.object(
            mt, "_embed", side_effect=self._embed_map()
        ):
            mt.index_meeting.__wrapped__(m1, transcript="all about apple pie")
            mt.index_meeting.__wrapped__(m2, transcript="all about banana bread")
            results = mt.search_meetings.__wrapped__("apple", limit=2)

        assert results[0]["meeting_id"] == m1
        assert results[0]["score"] is not None
        assert results[0]["title"] == "Apple meeting"

    def test_reindex_does_not_duplicate(self):
        coll = _FakeCollection()
        mid = mt.save_meeting.__wrapped__(title="M")["meeting_id"]
        with patch.object(mt, "_get_vector_collection", return_value=coll), patch.object(
            mt, "_embed", side_effect=self._embed_map()
        ):
            r1 = mt.index_meeting.__wrapped__(mid, transcript="apple " * 600)
            count_after_first = len(coll.store)
            r2 = mt.index_meeting.__wrapped__(mid, transcript="apple " * 600)
            count_after_second = len(coll.store)

        assert r1["chunks_indexed"] == r2["chunks_indexed"]
        assert count_after_first == count_after_second

    def test_index_missing_transcript(self):
        mid = mt.save_meeting.__wrapped__(title="M")["meeting_id"]
        result = mt.index_meeting.__wrapped__(mid)
        assert "error" in result

    def test_search_requires_query(self):
        assert "error" in mt.search_meetings.__wrapped__("")[0]


# ── Lazy import hygiene ─────────────────────────────────────────────


def test_no_heavy_deps_at_import_time():
    import sys

    # meeting_tools is already imported at top; ensure it did not pull heavy deps.
    mod = sys.modules["praisonai_tools.tools.meeting_tools"]
    src = open(mod.__file__).read()
    # No top-level (unindented) imports of openai/chromadb.
    for line in src.splitlines():
        if line.startswith("import openai") or line.startswith("from openai"):
            raise AssertionError("openai imported at module top level")
        if line.startswith("import chromadb") or line.startswith("from chromadb"):
            raise AssertionError("chromadb imported at module top level")


def test_all_tools_are_registerable():
    import praisonai_tools

    for name in (
        "transcribe_file",
        "save_meeting",
        "get_meeting",
        "list_meetings",
        "summarize_transcript",
        "extract_action_items",
        "index_meeting",
        "search_meetings",
    ):
        assert getattr(praisonai_tools, name) is not None
