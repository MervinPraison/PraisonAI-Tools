"""Google Docs Tool for PraisonAI Agents.

Create, read and edit Google Docs via the Docs API.

Usage:
    from praisonai_tools import GoogleDocsTool

    docs = GoogleDocsTool()
    doc = docs.create_document("Weekly Summary")
    docs.insert_text(doc["document_id"], "Hello world")
    text = docs.read_document_text(doc["document_id"])

Auth:
    Shares :class:`GoogleWorkspaceAuth`. Supports Service Account
    (``GOOGLE_SERVICE_ACCOUNT_FILE``), OAuth 2.0 (``GOOGLE_CREDENTIALS_FILE``)
    and Application Default Credentials. Pass ``auth=`` to reuse a shared
    session across tools.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool
from praisonai_tools.tools._google_auth import GoogleWorkspaceAuth, resolve_auth

logger = logging.getLogger(__name__)


class GoogleDocsTool(BaseTool):
    """Tool for reading, creating and editing Google Docs."""

    name = "google_docs"
    description = "Create, read, insert, replace and export Google Docs."

    def __init__(
        self,
        auth: Optional[GoogleWorkspaceAuth] = None,
        service_account_file: Optional[str] = None,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
    ):
        self._auth = resolve_auth(
            auth,
            ["docs", "drive"],
            service_account_file=service_account_file,
            credentials_file=credentials_file,
            token_file=token_file,
        )
        self._docs = None
        self._drive = None
        super().__init__()

    @property
    def service(self):
        if self._docs is None:
            self._docs = self._auth.build_service("docs", "v1", ["docs"])
        return self._docs

    @property
    def drive_service(self):
        if self._drive is None:
            self._drive = self._auth.build_service("drive", "v3", ["drive"])
        return self._drive

    def run(self, action: str = "read", **kwargs) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        actions = {
            "create": lambda: self.create_document(title=kwargs.get("title")),
            "get": lambda: self.get_document(document_id=kwargs.get("document_id")),
            "read": lambda: self.read_document_text(document_id=kwargs.get("document_id")),
            "insert_text": lambda: self.insert_text(**kwargs),
            "replace_text": lambda: self.replace_text(**kwargs),
            "export_pdf": lambda: self.export_as_pdf(
                document_id=kwargs.get("document_id"), dest_path=kwargs.get("dest_path")
            ),
        }
        handler = actions.get(action)
        if handler:
            return handler()
        return {"error": f"Unknown action: {action}. Available: {', '.join(actions)}"}

    def create_document(self, title: str) -> Dict[str, Any]:
        """Create a new empty document."""
        if not title:
            return {"error": "title is required"}
        try:
            doc = self.service.documents().create(body={"title": title}).execute()
            return {
                "success": True,
                "document_id": doc.get("documentId"),
                "title": doc.get("title"),
            }
        except Exception as e:
            logger.error(f"Google Docs create error: {e}")
            return {"error": str(e)}

    def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get the full document resource."""
        if not document_id:
            return {"error": "document_id is required"}
        try:
            return self.service.documents().get(documentId=document_id).execute()
        except Exception as e:
            logger.error(f"Google Docs get error: {e}")
            return {"error": str(e)}

    def read_document_text(self, document_id: str) -> str:
        """Return the plain text content of a document."""
        if not document_id:
            return "Error: document_id is required"
        try:
            doc = self.service.documents().get(documentId=document_id).execute()
            return self._extract_text(doc)
        except Exception as e:
            logger.error(f"Google Docs read error: {e}")
            return f"Error: {e}"

    @staticmethod
    def _extract_text(doc: Dict[str, Any]) -> str:
        chunks: List[str] = []
        for element in doc.get("body", {}).get("content", []):
            paragraph = element.get("paragraph")
            if not paragraph:
                continue
            for run in paragraph.get("elements", []):
                text_run = run.get("textRun")
                if text_run and text_run.get("content"):
                    chunks.append(text_run["content"])
        return "".join(chunks)

    def insert_text(self, document_id: str, text: str, index: int = 1) -> Dict[str, Any]:
        """Insert ``text`` at ``index`` (1 = start of body)."""
        if not document_id or text is None:
            return {"error": "document_id and text are required"}
        try:
            requests = [{"insertText": {"location": {"index": index}, "text": text}}]
            self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()
            return {"success": True, "document_id": document_id, "inserted": len(text)}
        except Exception as e:
            logger.error(f"Google Docs insert_text error: {e}")
            return {"error": str(e)}

    def replace_text(
        self, document_id: str, find: str, replace_with: str
    ) -> Dict[str, Any]:
        """Replace all occurrences of ``find`` with ``replace_with``."""
        if not document_id or not find:
            return {"error": "document_id and find are required"}
        try:
            requests = [
                {
                    "replaceAllText": {
                        "containsText": {"text": find, "matchCase": True},
                        "replaceText": replace_with or "",
                    }
                }
            ]
            result = self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()
            replies = result.get("replies", [{}])
            occurrences = replies[0].get("replaceAllText", {}).get("occurrencesChanged", 0)
            return {"success": True, "document_id": document_id, "replaced": occurrences}
        except Exception as e:
            logger.error(f"Google Docs replace_text error: {e}")
            return {"error": str(e)}

    def export_as_pdf(self, document_id: str, dest_path: str) -> str:
        """Export a document as PDF to ``dest_path``."""
        return self._export(document_id, dest_path, "application/pdf")

    def export_as_docx(self, document_id: str, dest_path: str) -> str:
        """Export a document as a Word .docx file to ``dest_path``."""
        return self._export(
            document_id,
            dest_path,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def _export(self, document_id: str, dest_path: str, mime_type: str) -> str:
        if not document_id or not dest_path:
            return "Error: document_id and dest_path are required"
        try:
            request = self.drive_service.files().export_media(
                fileId=document_id, mimeType=mime_type
            )
            data = request.execute()
            with open(dest_path, "wb") as fh:
                fh.write(data)
            return dest_path
        except Exception as e:
            logger.error(f"Google Docs export error: {e}")
            return f"Error: {e}"


def create_google_doc(title: str) -> Dict[str, Any]:
    """Create a new Google Doc and return its id."""
    return GoogleDocsTool().create_document(title)
