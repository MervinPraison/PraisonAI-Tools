"""Google Slides Tool for PraisonAI Agents.

Create and manage Google Slides presentations via the Slides API.

Usage:
    from praisonai_tools import GoogleSlidesTool

    slides = GoogleSlidesTool()
    deck = slides.create_presentation("Q2 Review")
    slides.add_slide(deck["presentation_id"])

Auth:
    Shares :class:`GoogleWorkspaceAuth` (Service Account / OAuth / ADC). Pass
    ``auth=`` to reuse a shared session across tools.
"""

import logging
import uuid
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool
from praisonai_tools.tools._google_auth import GoogleWorkspaceAuth, resolve_auth

logger = logging.getLogger(__name__)


class GoogleSlidesTool(BaseTool):
    """Tool for creating and managing Google Slides presentations."""

    name = "google_slides"
    description = "Create presentations, add slides, insert text and export to PDF."

    def __init__(
        self,
        auth: Optional[GoogleWorkspaceAuth] = None,
        service_account_file: Optional[str] = None,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
    ):
        self._auth = resolve_auth(
            auth,
            ["slides", "drive"],
            service_account_file=service_account_file,
            credentials_file=credentials_file,
            token_file=token_file,
        )
        self._slides = None
        self._drive = None
        super().__init__()

    @property
    def service(self):
        if self._slides is None:
            self._slides = self._auth.build_service("slides", "v1", ["slides"])
        return self._slides

    @property
    def drive_service(self):
        if self._drive is None:
            self._drive = self._auth.build_service("drive", "v3", ["drive"])
        return self._drive

    def run(self, action: str = "get", **kwargs) -> Union[str, Dict[str, Any]]:
        action = action.lower().replace("-", "_")
        actions = {
            "create": lambda: self.create_presentation(title=kwargs.get("title")),
            "get": lambda: self.get_presentation(
                presentation_id=kwargs.get("presentation_id")
            ),
            "add_slide": lambda: self.add_slide(**kwargs),
            "insert_text": lambda: self.insert_text_in_slide(**kwargs),
            "export_pdf": lambda: self.export_as_pdf(
                presentation_id=kwargs.get("presentation_id"),
                dest_path=kwargs.get("dest_path"),
            ),
        }
        handler = actions.get(action)
        if handler:
            return handler()
        return {"error": f"Unknown action: {action}. Available: {', '.join(actions)}"}

    def create_presentation(self, title: str) -> Dict[str, Any]:
        """Create a new presentation."""
        if not title:
            return {"error": "title is required"}
        try:
            deck = self.service.presentations().create(body={"title": title}).execute()
            return {
                "success": True,
                "presentation_id": deck.get("presentationId"),
                "title": deck.get("title"),
            }
        except Exception as e:
            logger.error(f"Google Slides create error: {e}")
            return {"error": str(e)}

    def get_presentation(self, presentation_id: str) -> Dict[str, Any]:
        """Get the presentation resource."""
        if not presentation_id:
            return {"error": "presentation_id is required"}
        try:
            return self.service.presentations().get(
                presentationId=presentation_id
            ).execute()
        except Exception as e:
            logger.error(f"Google Slides get error: {e}")
            return {"error": str(e)}

    def add_slide(self, presentation_id: str, layout: str = "BLANK") -> Dict[str, Any]:
        """Add a slide using a predefined layout (e.g. BLANK, TITLE_AND_BODY)."""
        if not presentation_id:
            return {"error": "presentation_id is required"}
        try:
            slide_id = f"slide_{uuid.uuid4().hex[:8]}"
            requests = [
                {
                    "createSlide": {
                        "objectId": slide_id,
                        "slideLayoutReference": {"predefinedLayout": layout},
                    }
                }
            ]
            self.service.presentations().batchUpdate(
                presentationId=presentation_id, body={"requests": requests}
            ).execute()
            return {"success": True, "presentation_id": presentation_id, "slide_id": slide_id}
        except Exception as e:
            logger.error(f"Google Slides add_slide error: {e}")
            return {"error": str(e)}

    def insert_text_in_slide(
        self, presentation_id: str, slide_id: str, text: str
    ) -> Dict[str, Any]:
        """Add a text box to ``slide_id`` and insert ``text`` into it."""
        if not presentation_id or not slide_id or text is None:
            return {"error": "presentation_id, slide_id and text are required"}
        try:
            box_id = f"text_{uuid.uuid4().hex[:8]}"
            requests = [
                {
                    "createShape": {
                        "objectId": box_id,
                        "shapeType": "TEXT_BOX",
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {
                                "width": {"magnitude": 3000000, "unit": "EMU"},
                                "height": {"magnitude": 1000000, "unit": "EMU"},
                            },
                            "transform": {
                                "scaleX": 1,
                                "scaleY": 1,
                                "translateX": 500000,
                                "translateY": 500000,
                                "unit": "EMU",
                            },
                        },
                    }
                },
                {"insertText": {"objectId": box_id, "text": text}},
            ]
            self.service.presentations().batchUpdate(
                presentationId=presentation_id, body={"requests": requests}
            ).execute()
            return {"success": True, "slide_id": slide_id, "text_box_id": box_id}
        except Exception as e:
            logger.error(f"Google Slides insert_text error: {e}")
            return {"error": str(e)}

    def export_as_pdf(self, presentation_id: str, dest_path: str) -> str:
        """Export the presentation as PDF to ``dest_path``."""
        if not presentation_id or not dest_path:
            return "Error: presentation_id and dest_path are required"
        try:
            request = self.drive_service.files().export_media(
                fileId=presentation_id, mimeType="application/pdf"
            )
            data = request.execute()
            with open(dest_path, "wb") as fh:
                fh.write(data)
            return dest_path
        except Exception as e:
            logger.error(f"Google Slides export error: {e}")
            return f"Error: {e}"


def create_google_presentation(title: str) -> Dict[str, Any]:
    """Create a new Google Slides presentation."""
    return GoogleSlidesTool().create_presentation(title)
