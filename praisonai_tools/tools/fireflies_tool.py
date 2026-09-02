"""Fireflies.ai Tool for PraisonAI Agents.

Curated GraphQL operations over the Fireflies.ai meeting-intelligence API:
list recent meetings, fetch a transcript, and keyword search.

Design (Option B from the issue): each agent-callable method maps to a small,
pre-approved GraphQL document rather than letting the LLM craft arbitrary
queries. This keeps the surface predictable and robust.

Usage:
    from praisonai_tools import FirefliesTool

    fireflies = FirefliesTool()
    meetings = fireflies.list_recent_meetings(limit=5)
    transcript = fireflies.get_transcript(meeting_id="abc123")

Environment Variables:
    FIREFLIES_API_KEY: Fireflies API key (sent as ``Authorization: Bearer <key>``)
    FIREFLIES_API_URL: Optional endpoint override (defaults to the public API)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.fireflies.ai/graphql"


class FirefliesTool(BaseTool):
    """Tool for querying Fireflies.ai meeting intelligence via curated GraphQL."""

    name = "fireflies"
    description = (
        "Query Fireflies.ai meeting intelligence: list recent meetings, "
        "fetch transcripts, and search by keyword."
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("FIREFLIES_API_KEY")
        self.api_url = api_url or os.getenv("FIREFLIES_API_URL") or DEFAULT_API_URL
        super().__init__()

    def _graphql(self, query: str, variables: Dict = None) -> Dict:
        """Execute a curated GraphQL document, returning normalized results.

        Missing credentials are reported distinctly from HTTP auth failures so
        callers can tell a misconfiguration (no key) apart from a rejected key
        (401/403).
        """
        if not self.api_key:
            return {"error": "FIREFLIES_API_KEY required"}

        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}

        try:
            resp = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables or {}},
                timeout=30,
            )
        except Exception as e:
            return {"error": str(e)}

        if resp.status_code in (401, 403):
            return {
                "error": f"Fireflies authentication failed (HTTP {resp.status_code})",
                "status_code": resp.status_code,
            }
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            error = {"error": "Fireflies rate limit exceeded", "status_code": 429}
            if retry_after:
                error["retry_after"] = retry_after
            return error

        try:
            payload = resp.json()
        except Exception:
            return {
                "error": f"Fireflies returned non-JSON response (HTTP {resp.status_code})",
                "status_code": resp.status_code,
            }

        if payload.get("errors"):
            messages = [e.get("message", "unknown error") for e in payload["errors"]]
            return {"error": "; ".join(messages)}
        return payload

    def run(
        self,
        action: str = "list_recent_meetings",
        meeting_id: Optional[str] = None,
        keywords: Optional[str] = None,
        **kwargs,
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")

        if action == "list_recent_meetings":
            return self.list_recent_meetings(**kwargs)
        elif action == "get_transcript":
            return self.get_transcript(meeting_id=meeting_id)
        elif action == "search":
            return self.search(keywords=keywords, **kwargs)
        else:
            return {"error": f"Unknown action: {action}"}

    def list_recent_meetings(
        self, limit: int = 10, after: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List recent meetings/transcripts.

        Args:
            limit: Maximum number of meetings to return.
            after: Cursor (skip offset) for pagination. Explicit paging avoids
                unbounded scans of the account history.
        """
        query = """
        query($limit: Int, $skip: Int) {
            transcripts(limit: $limit, skip: $skip) {
                id
                title
                date
                duration
                organizer_email
            }
        }
        """
        variables: Dict[str, Any] = {"limit": limit}
        if after is not None:
            try:
                variables["skip"] = int(after)
            except (TypeError, ValueError):
                return [{"error": "after must be an integer cursor"}]

        result = self._graphql(query, variables)
        if "error" in result:
            return [result]

        transcripts = result.get("data", {}).get("transcripts") or []
        return [
            {
                "id": t.get("id"),
                "title": t.get("title"),
                "date": t.get("date"),
                "duration": t.get("duration"),
                "organizer_email": t.get("organizer_email"),
            }
            for t in transcripts
        ]

    def get_transcript(self, meeting_id: str) -> Dict[str, Any]:
        """Fetch a single meeting transcript with summary and sentences."""
        if not meeting_id:
            return {"error": "meeting_id required"}

        query = """
        query($id: String!) {
            transcript(id: $id) {
                id
                title
                date
                duration
                organizer_email
                summary { overview }
                sentences {
                    text
                    speaker_name
                    start_time
                }
            }
        }
        """
        result = self._graphql(query, {"id": meeting_id})
        if "error" in result:
            return result

        transcript = result.get("data", {}).get("transcript")
        if not transcript:
            return {"error": "transcript not found"}

        summary = transcript.get("summary") or {}
        sentences = transcript.get("sentences") or []
        return {
            "id": transcript.get("id"),
            "title": transcript.get("title"),
            "date": transcript.get("date"),
            "duration": transcript.get("duration"),
            "organizer_email": transcript.get("organizer_email"),
            "summary": summary.get("overview"),
            "sentences": sentences,
            "sentence_count": len(sentences),
        }

    def search(self, keywords: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search meetings whose transcripts match the given keyword phrase."""
        if not keywords:
            return [{"error": "keywords required"}]

        query = """
        query($keyword: String, $limit: Int) {
            transcripts(keyword: $keyword, limit: $limit) {
                id
                title
                date
                organizer_email
            }
        }
        """
        result = self._graphql(query, {"keyword": keywords, "limit": limit})
        if "error" in result:
            return [result]

        transcripts = result.get("data", {}).get("transcripts") or []
        return [
            {
                "id": t.get("id"),
                "title": t.get("title"),
                "date": t.get("date"),
                "organizer_email": t.get("organizer_email"),
            }
            for t in transcripts
        ]


def list_fireflies_meetings(limit: int = 10) -> List[Dict[str, Any]]:
    """List recent Fireflies meetings."""
    return FirefliesTool().list_recent_meetings(limit=limit)
