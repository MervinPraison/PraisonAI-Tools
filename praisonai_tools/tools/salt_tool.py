"""Salt Tool for PraisonAI Agents.

Narrow, audited operations against Salt (https://saltapp.ai) — end-to-end
encrypted chat where humans and AI agents are equal contacts, and an agent
can message, ask, invoice, and get paid. This tool talks directly to Salt's
documented REST API (there is no published Salt SDK on PyPI yet); it never
handles a Salt message's PGP ciphertext — only Salt's structured, non-E2E
surfaces: interactive "cards" (declarative buttons/sections an agent can
post into a chat) and payment requests.

Design constraint: one verb per action, same as the other narrow tools in
this package (see stripe_tool.py). No "god tool" that dumps Salt's whole
REST surface.

Usage:
    from praisonai_tools import SaltTool

    salt = SaltTool()  # reads SALT_API_KEY
    card = salt.run(
        action="create_card",
        chat_id=123,
        text="An agent needs a decision from you.",
        blocks=[
            {"type": "section", "text": "Approve the refund?"},
            {"type": "actions", "elements": [
                {"type": "button", "action_id": "approve", "label": "Approve", "style": "primary"},
                {"type": "button", "action_id": "deny", "label": "Deny", "style": "danger"},
            ]},
        ],
    )
    interactions = salt.run(action="read_card", card_id=card["resource_id"])
    request = salt.run(
        action="create_payment_request",
        chat_id=123,
        wallet_id="wallet_abc",
        receiver_id="user_456",
        amount="5.00",
        message="For the design work",
    )

Environment Variables:
    SALT_API_KEY: The agent's Salt API key (see POST /api/v1/agents or the
        root-agent form of POST /auth for how to obtain one).
    SALT_API_BASE: Override the API base URL (defaults to
        https://saltapp.ai/api/v1; useful against a self-hosted or staging
        Salt instance).

Security notes:
    * The API key is read from the environment only and never logged.
    * A card is structured data rendered by Salt's own first-party chrome —
      an agent can never express anything outside the block vocabulary Salt
      validates server-side, so a hostile string in a card renders as inert
      text, never as something a human could be tricked into approving by
      mistake.
    * A "pay"-type button inside a card is dispatched by Salt's SERVER on
      the button's type, never on this tool's say-so — this tool only ever
      creates a payment REQUEST (create_payment_request / a "pay" card
      button), never moves funds directly. Every payment still needs the
      payer's own confirmation inside the Salt app.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

DEFAULT_API_BASE = "https://saltapp.ai/api/v1"


class SaltTool(BaseTool):
    """Tool for narrow, audited Salt chat/payment operations."""

    name = "salt"
    description = (
        "Post an interactive card into a Salt chat, read back which button "
        "was tapped, and create a payment request — for an AI agent with "
        "its own Salt account talking to a human or another agent."
    )

    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        self.api_key = api_key or os.getenv("SALT_API_KEY")
        self.api_base = (api_base or os.getenv("SALT_API_BASE") or DEFAULT_API_BASE).rstrip("/")
        super().__init__()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_key(self) -> Optional[Dict[str, str]]:
        if not self.api_key:
            return {"error": "SALT_API_KEY is required"}
        return None

    @staticmethod
    def _import_requests():
        try:
            import requests
            return requests
        except ImportError:
            return None

    def _request(
        self,
        method: str,
        endpoint: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a request to Salt's REST API.

        Centralises key validation, the optional ``requests`` import, the
        HTTP call, auditable logging, and error handling.
        """
        err = self._require_key()
        if err:
            return err

        requests = self._import_requests()
        if requests is None:
            return {"error": "requests package is not installed"}

        headers = {"api-key": self.api_key}

        try:
            resp = requests.request(
                method,
                f"{self.api_base}/{endpoint}",
                headers=headers,
                json=json_body,
                params=params,
                timeout=30,
            )
            body = resp.json() if resp.content else {}
        except requests.exceptions.RequestException as e:
            logger.error("Salt request error: %s", e)
            return {"error": f"API request failed: {e}"}
        except ValueError as e:
            logger.error("Salt JSON decode error: %s", e)
            return {"error": "Failed to decode API response"}

        if resp.status_code >= 400:
            message = body.get("error") if isinstance(body, dict) else None
            if not message and isinstance(body, dict):
                message = "; ".join(body.get("errors", [])) or None
            logger.error("Salt API error: op=%s status=%s", endpoint, resp.status_code)
            return {"error": message or f"Salt API returned HTTP {resp.status_code}"}

        logger.info("Salt op=%s status=%s", endpoint, resp.status_code)
        return body if isinstance(body, dict) else {"result": body}

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def run(
        self,
        action: str = "create_card",
        chat_id: Optional[Union[int, str]] = None,
        card_id: Optional[Union[int, str]] = None,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        after: Optional[str] = None,
        wallet_id: Optional[str] = None,
        receiver_id: Optional[Union[int, str]] = None,
        amount: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Dispatch to the appropriate Salt action.

        Actions:
            create_card            — Post a blocks card into a chat (write).
            read_card               — Read a card's state and taps (read, owner-only).
            create_payment_request  — Create a payment request in a chat (write).
        """
        action = action.lower().replace("-", "_")

        if action == "create_card":
            return self.create_card(chat_id=chat_id, text=text, blocks=blocks)
        elif action == "read_card":
            return self.read_card(card_id=card_id, after=after)
        elif action == "create_payment_request":
            return self.create_payment_request(
                chat_id=chat_id,
                wallet_id=wallet_id,
                receiver_id=receiver_id,
                amount=amount,
                message=message,
            )
        else:
            return {"error": f"Unknown action: {action}"}

    # ------------------------------------------------------------------
    # Cards — structured, non-E2E chat surfaces
    # ------------------------------------------------------------------

    def create_card(
        self,
        chat_id: Optional[Union[int, str]] = None,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Post an interactive card into a chat the agent is a member of.

        Args:
            chat_id: The chat to post into.
            text: Plaintext fallback/preview shown in notification previews.
            blocks: A list of Salt block-kit blocks (``section``, ``image``,
                ``divider``, ``actions`` with ``button`` elements). See
                CARD_PROTOCOL_SPEC.md in the salt-api repo for the full
                vocabulary.
        """
        if not chat_id:
            return {"error": "chat_id is required"}
        if not blocks:
            return {"error": "blocks is required (at least one block)"}

        return self._request(
            "post",
            "cards",
            json_body={"chat_id": chat_id, "text": text, "state": {"blocks": blocks}},
        )

    def read_card(
        self, card_id: Optional[Union[int, str]] = None, after: Optional[str] = None
    ) -> Dict[str, Any]:
        """Read back a card's current state and every tap it has received.

        Only the card's OWNER may read it — this is how a stateless agent
        finds out someone tapped a button, without running a webhook
        server or holding a socket open.

        Args:
            card_id: The id returned as ``resource_id`` by ``create_card``.
            after: Optional interaction id or ISO 8601 timestamp; only
                interactions after this point are returned.
        """
        if not card_id:
            return {"error": "card_id is required"}

        params = {"after": after} if after else None
        return self._request("get", f"cards/{card_id}", params=params)

    # ------------------------------------------------------------------
    # Payment requests
    # ------------------------------------------------------------------

    def create_payment_request(
        self,
        chat_id: Optional[Union[int, str]] = None,
        wallet_id: Optional[str] = None,
        receiver_id: Optional[Union[int, str]] = None,
        amount: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a payment request (invoice bubble) in a chat.

        The request rides Salt's existing payment-request rail: the
        receiver still confirms and signs the payment themselves inside
        the Salt app. This call only asks; it never moves funds.

        Args:
            chat_id: The chat both parties share; the request's bubble is
                posted here.
            wallet_id: One of THIS agent's own receiving wallet ids (the
                money comes back to this wallet).
            receiver_id: The user id being asked to pay.
            amount: A human-decimal amount string, e.g. ``"5.00"``.
            message: Optional note shown on the request bubble.
        """
        if not chat_id:
            return {"error": "chat_id is required"}
        if not wallet_id:
            return {"error": "wallet_id is required"}
        if not receiver_id:
            return {"error": "receiver_id is required"}
        if not amount:
            return {"error": "amount is required"}

        return self._request(
            "post",
            "transfer_requests",
            json_body={
                "chat_id": chat_id,
                "wallet_id": wallet_id,
                "receiver_id": receiver_id,
                "amount": amount,
                "message": message,
            },
        )


def create_salt_card(
    chat_id: Union[int, str],
    blocks: List[Dict[str, Any]],
    text: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Post a Salt card into a chat."""
    return SaltTool(api_key=api_key).create_card(chat_id=chat_id, text=text, blocks=blocks)
