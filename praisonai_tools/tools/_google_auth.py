"""Shared Google Workspace authentication for PraisonAI tools.

Provides :class:`GoogleWorkspaceAuth`, a single credential/service factory that
every Google Workspace tool can share so an agent authenticates once and reuses
the same token across Gmail, Drive, Docs, Slides, Tasks, Chat, etc.

Three auth modes are attempted, in order:

1. **Service Account** (``GOOGLE_SERVICE_ACCOUNT_FILE``) — server-safe, no
   browser. Optionally impersonate a user via ``subject`` (domain-wide
   delegation).
2. **OAuth 2.0** (``GOOGLE_CREDENTIALS_FILE`` + ``GOOGLE_TOKEN_FILE``) — browser
   once, token cached and shared by all tools.
3. **Application Default Credentials** — GCP environments (Cloud Run, GCE, …).

The Google client libraries are imported lazily so importing this module (and
the tools that use it) never requires the optional ``google-workspace`` extra
until a request is actually made.

Environment Variables:
    GOOGLE_SERVICE_ACCOUNT_FILE: Path to service_account.json (mode 1)
    GOOGLE_CREDENTIALS_FILE: Path to OAuth client credentials.json (mode 2)
    GOOGLE_TOKEN_FILE: Path to cached OAuth token (default
        ``~/.praisonai/google_token.json``)
    GOOGLE_WORKSPACE_SUBJECT: Optional user email to impersonate (service
        account domain-wide delegation)
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_INSTALL_HINT = (
    "Google Workspace tools require the optional dependencies. Install with: "
    "pip install 'praisonai-tools[google-workspace]' (or pip install "
    "google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2)"
)

# Per-service OAuth scopes. Combined for the set of services a tool needs so a
# single token covers every service the agent touches.
SCOPES: Dict[str, List[str]] = {
    "gmail": ["https://www.googleapis.com/auth/gmail.modify"],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
    "drive": ["https://www.googleapis.com/auth/drive"],
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "docs": ["https://www.googleapis.com/auth/documents"],
    "slides": ["https://www.googleapis.com/auth/presentations"],
    "tasks": ["https://www.googleapis.com/auth/tasks"],
    "chat": ["https://www.googleapis.com/auth/chat.messages"],
}

_DEFAULT_TOKEN_FILE = os.path.join("~", ".praisonai", "google_token.json")


class GoogleWorkspaceAuth:
    """Shared authentication/service factory for Google Workspace tools."""

    def __init__(
        self,
        services: Optional[List[str]] = None,
        service_account_file: Optional[str] = None,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
        subject: Optional[str] = None,
    ):
        self.services = list(services) if services else []
        self.service_account_file = service_account_file or os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_FILE"
        )
        self.credentials_file = credentials_file or os.getenv(
            "GOOGLE_CREDENTIALS_FILE", "credentials.json"
        )
        self.token_file = os.path.expanduser(
            token_file or os.getenv("GOOGLE_TOKEN_FILE", _DEFAULT_TOKEN_FILE)
        )
        self.subject = subject or os.getenv("GOOGLE_WORKSPACE_SUBJECT")
        self._credentials = None
        self._service_cache: Dict[str, object] = {}

    # ------------------------------------------------------------------
    # Scope resolution
    # ------------------------------------------------------------------
    def scopes_for(self, services: Optional[List[str]] = None) -> List[str]:
        """Return the combined, de-duplicated scopes for ``services``."""
        requested = services or self.services
        if not requested:
            raise ValueError("No Google Workspace services requested for auth.")

        combined: List[str] = []
        for name in requested:
            key = name.lower()
            if key not in SCOPES:
                raise ValueError(
                    f"Unknown Google Workspace service: {name!r}. "
                    f"Known: {', '.join(sorted(SCOPES))}"
                )
            for scope in SCOPES[key]:
                if scope not in combined:
                    combined.append(scope)
        return combined

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------
    def get_credentials(self, services: Optional[List[str]] = None):
        """Return credentials with the combined scopes for ``services``.

        Credentials are cached on the instance so repeated tool calls reuse the
        same authorised session.
        """
        if self._credentials is not None:
            return self._credentials

        scopes = self.scopes_for(services)

        # Mode 1: Service Account (server-safe, no browser).
        if self.service_account_file:
            self._credentials = self._service_account_credentials(scopes)
            return self._credentials

        # Mode 2: OAuth 2.0 with a shared, cached token.
        if os.path.exists(self.credentials_file) or os.path.exists(self.token_file):
            self._credentials = self._oauth_credentials(scopes)
            return self._credentials

        # Mode 3: Application Default Credentials (GCP environments).
        self._credentials = self._default_credentials(scopes)
        return self._credentials

    def _service_account_credentials(self, scopes: List[str]):
        try:
            from google.oauth2 import service_account
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ImportError(_INSTALL_HINT) from exc

        if not os.path.exists(self.service_account_file):
            raise ValueError(
                f"Service account file not found: {self.service_account_file}"
            )

        creds = service_account.Credentials.from_service_account_file(
            self.service_account_file, scopes=scopes
        )
        if self.subject:
            creds = creds.with_subject(self.subject)
        logger.info("Google auth: using service account (no browser).")
        return creds

    def _oauth_credentials(self, scopes: List[str]):
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ImportError(_INSTALL_HINT) from exc

        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as exc:  # RefreshError and friends
                    raise RuntimeError(
                        "Google OAuth token refresh failed; delete "
                        f"{self.token_file} and re-authenticate. ({exc})"
                    ) from exc
            else:
                if not os.path.exists(self.credentials_file):
                    raise ValueError(
                        f"OAuth credentials file not found: {self.credentials_file}. "
                        "Set GOOGLE_CREDENTIALS_FILE or GOOGLE_SERVICE_ACCOUNT_FILE."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, scopes
                )
                creds = flow.run_local_server(port=0)
            self._write_token(creds)
        logger.info("Google auth: using OAuth 2.0 (shared token).")
        return creds

    def _default_credentials(self, scopes: List[str]):
        try:
            import google.auth
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ImportError(_INSTALL_HINT) from exc

        try:
            creds, _ = google.auth.default(scopes=scopes)
        except Exception as exc:
            raise ValueError(
                "No Google credentials found. Provide GOOGLE_SERVICE_ACCOUNT_FILE, "
                "GOOGLE_CREDENTIALS_FILE, or run in a GCP environment with "
                f"Application Default Credentials. ({exc})"
            ) from exc
        logger.info("Google auth: using Application Default Credentials.")
        return creds

    def _write_token(self, creds) -> None:
        try:
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, "w", encoding="utf-8") as fh:
                fh.write(creds.to_json())
        except OSError as exc:  # pragma: no cover - best effort
            logger.warning("Could not cache Google token at %s: %s", self.token_file, exc)

    # ------------------------------------------------------------------
    # Service factory
    # ------------------------------------------------------------------
    def build_service(
        self,
        api: str,
        version: str,
        services: Optional[List[str]] = None,
    ):
        """Build (and cache) a Google API client for ``api``/``version``."""
        cache_key = f"{api}:{version}"
        cached = self._service_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ImportError(_INSTALL_HINT) from exc

        creds = self.get_credentials(services)
        service = build(api, version, credentials=creds, cache_discovery=False)
        self._service_cache[cache_key] = service
        return service


def resolve_auth(
    auth: Optional[GoogleWorkspaceAuth],
    services: List[str],
    **kwargs,
) -> GoogleWorkspaceAuth:
    """Return ``auth`` if provided, else build a new one for ``services``.

    Lets each tool accept an optional shared ``auth=`` while still working
    standalone.
    """
    if auth is not None:
        return auth
    return GoogleWorkspaceAuth(services=services, **kwargs)
