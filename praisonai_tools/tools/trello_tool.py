"""Trello Tool for PraisonAI Agents.

Manage Trello boards, lists, and cards.

Usage:
    from praisonai_tools import TrelloTool
    
    trello = TrelloTool()
    boards = trello.list_boards()

Environment Variables:
    TRELLO_API_KEY: Trello API key
    TRELLO_TOKEN: Trello token
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class TrelloTool(BaseTool):
    """Tool for managing Trello boards."""
    
    name = "trello"
    description = "Manage Trello boards, lists, and cards."
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        token: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("TRELLO_API_KEY")
        self.token = token or os.getenv("TRELLO_TOKEN")
        self.base_url = "https://api.trello.com/1"
        super().__init__()
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed"}
        
        if not self.api_key or not self.token:
            return {"error": "TRELLO_API_KEY and TRELLO_TOKEN required"}
        
        params = {"key": self.api_key, "token": self.token}
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == "GET":
                resp = requests.get(url, params=params, timeout=10)
            elif method == "POST":
                resp = requests.post(url, params=params, json=data, timeout=10)
            elif method == "PUT":
                resp = requests.put(url, params=params, json=data, timeout=10)
            elif method == "DELETE":
                resp = requests.delete(url, params=params, timeout=10)
            else:
                return {"error": f"Unknown method: {method}"}
            
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def run(
        self,
        action: str = "list_boards",
        board_id: Optional[str] = None,
        list_id: Optional[str] = None,
        card_id: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_boards":
            return self.list_boards()
        elif action == "get_board":
            return self.get_board(board_id=board_id)
        elif action == "list_lists":
            return self.list_lists(board_id=board_id)
        elif action == "list_cards":
            return self.list_cards(list_id=list_id)
        elif action == "create_card":
            return self.create_card(list_id=list_id, name=name, **kwargs)
        elif action == "get_card":
            return self.get_card(card_id=card_id)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_boards(self) -> List[Dict[str, Any]]:
        """List all boards."""
        result = self._request("GET", "members/me/boards")
        if isinstance(result, dict) and "error" in result:
            return [result]
        return [{"id": b["id"], "name": b["name"], "url": b["url"]} for b in result]
    
    def get_board(self, board_id: str) -> Dict[str, Any]:
        """Get board details."""
        if not board_id:
            return {"error": "board_id required"}
        return self._request("GET", f"boards/{board_id}")
    
    def list_lists(self, board_id: str) -> List[Dict[str, Any]]:
        """List all lists in a board."""
        if not board_id:
            return [{"error": "board_id required"}]
        result = self._request("GET", f"boards/{board_id}/lists")
        if isinstance(result, dict) and "error" in result:
            return [result]
        return [{"id": lst["id"], "name": lst["name"]} for lst in result]
    
    def list_cards(self, list_id: str) -> List[Dict[str, Any]]:
        """List all cards in a list."""
        if not list_id:
            return [{"error": "list_id required"}]
        result = self._request("GET", f"lists/{list_id}/cards")
        if isinstance(result, dict) and "error" in result:
            return [result]
        return [{"id": c["id"], "name": c["name"], "desc": c.get("desc", "")} for c in result]
    
    def create_card(self, list_id: str, name: str, desc: str = None) -> Dict[str, Any]:
        """Create a card."""
        if not list_id or not name:
            return {"error": "list_id and name required"}
        
        data = {"idList": list_id, "name": name}
        if desc:
            data["desc"] = desc
        
        result = self._request("POST", "cards", data)
        if "error" in result:
            return result
        return {"success": True, "id": result.get("id"), "name": result.get("name")}
    
    def get_card(self, card_id: str) -> Dict[str, Any]:
        """Get card details."""
        if not card_id:
            return {"error": "card_id required"}
        return self._request("GET", f"cards/{card_id}")


def list_trello_boards() -> List[Dict[str, Any]]:
    """List Trello boards."""
    return TrelloTool().list_boards()
