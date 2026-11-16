"""HubSpot CRM contacts tool (create / get / search). Uses HUBSPOT_ACCESS_TOKEN."""

import os
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

from praisonai_tools.tools.base import BaseTool

BASE_URL = "https://api.hubapi.com"
MAX_RETRY_DELAY_SECONDS = 60


class HubSpotTool(BaseTool):
    """Tool for managing HubSpot CRM contacts."""

    name = "hubspot"
    description = "Manage HubSpot CRM contacts — create, get, search."

    def __init__(self, access_token: Optional[str] = None, max_retries: int = 3):
        self.access_token = access_token or os.getenv("HUBSPOT_ACCESS_TOKEN")
        self.max_retries = max_retries
        super().__init__()

    def _request(self, method: str, path: str, json_body: Optional[Dict] = None,
                 params: Optional[Dict] = None) -> Dict[str, Any]:
        """Authenticated request with 429 retry; the token is masked in errors."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. Install with: pip install requests"}
        if not self.access_token:
            return {"error": "HUBSPOT_ACCESS_TOKEN required"}
        def mask(s):
            return (s or "").replace(self.access_token, "***")
        headers = {"Authorization": f"Bearer {self.access_token}"}
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.request(method, f"{BASE_URL}{path}", headers=headers,
                                        json=json_body, params=params, timeout=30)
            except Exception as e:
                return {"error": mask(str(e))}
            if resp.status_code == 429 and attempt < self.max_retries:
                ra = resp.headers.get("Retry-After") or ""  # may be an HTTP-date or negative
                delay = float(ra) if ra.replace(".", "", 1).isdigit() else 2 ** attempt
                time.sleep(min(delay, MAX_RETRY_DELAY_SECONDS))
                continue
            try:
                data = resp.json() if resp.content else {}
            except ValueError:
                data = None  # malformed JSON
            if resp.status_code >= 400:
                msg = data.get("message") if isinstance(data, dict) else None
                return {"error": mask(msg or f"HTTP {resp.status_code}"),
                        "status_code": resp.status_code}
            return data if data is not None else {"error": "Invalid JSON response"}
        return {"error": "Rate limited (429) after retries", "status_code": 429}

    def run(self, action: str = "search_contacts", **kwargs) -> Union[Dict, List[Dict]]:
        fn = {"create_contact": self.create_contact, "get_contact": self.get_contact,
              "search_contacts": self.search_contacts}.get(action.lower().replace("-", "_"))
        return fn(**kwargs) if fn else {"error": f"Unknown action: {action}"}

    def create_contact(self, email: str, firstname: Optional[str] = None,
                       lastname: Optional[str] = None, phone: Optional[str] = None,
                       company: Optional[str] = None) -> Dict[str, Any]:
        """Create a contact. Returns the created object (with id) directly."""
        if not email:
            return {"error": "email required"}
        props = {k: v for k, v in {"email": email, "firstname": firstname, "lastname": lastname,
                                   "phone": phone, "company": company}.items() if v is not None}
        return self._request("POST", "/crm/v3/objects/contacts", {"properties": props})

    def get_contact(self, contact_id: str, properties: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get a contact by ID, optionally with selected properties."""
        if not contact_id:
            return {"error": "contact_id required"}
        params = {"properties": ",".join(properties)} if properties else None
        return self._request("GET", f"/crm/v3/objects/contacts/{quote(str(contact_id), safe='')}", params=params)

    def search_contacts(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search contacts by free-text query."""
        result = self._request("POST", "/crm/v3/objects/contacts/search", {"query": query, "limit": limit})
        return [result] if "error" in result else result.get("results", [])


def hubspot_create_contact(email: str, firstname: Optional[str] = None, lastname: Optional[str] = None,
                           company: Optional[str] = None) -> Dict[str, Any]:
    """Create a HubSpot contact."""
    return HubSpotTool().create_contact(email=email, firstname=firstname, lastname=lastname, company=company)


def hubspot_search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search HubSpot contacts."""
    return HubSpotTool().search_contacts(query=query)
