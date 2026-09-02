"""HubSpot CRM Tool for PraisonAI Agents.

Manage HubSpot CRM — contacts, companies, deals, pipelines, and activity logging
via the HubSpot REST API v3.

Usage:
    from praisonai_tools import HubSpotTool

    hs = HubSpotTool()  # Uses HUBSPOT_ACCESS_TOKEN env var

    # Create a contact (returns the created id directly - no re-search needed)
    contact = hs.create_contact(
        email="alice@example.com",
        firstname="Alice",
        lastname="Smith",
        company="Acme Corp",
    )

    # Move a deal through the pipeline
    hs.move_deal_stage(deal_id="123", stage_id="closedwon")

Environment Variables:
    HUBSPOT_ACCESS_TOKEN: Private App access token (recommended, sent as Bearer)

Notes:
    * Activities (calls/emails/meetings/notes) use the v3 CRM object endpoints
      (``/crm/v3/objects/calls`` etc.), NOT the legacy ``/engagements/v1`` API,
      so the activity timeline links correctly to v3 contacts/deals.
    * The access token is never logged and is masked in error messages.
"""

import os
import time
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)

BASE_URL = "https://api.hubapi.com"

# HubSpot numeric association type IDs (default/unlabeled associations).
ASSOC_CONTACT_TO_COMPANY = 279
ASSOC_DEAL_TO_CONTACT = 3
ASSOC_DEAL_TO_COMPANY = 5
ASSOC_NOTE_TO_CONTACT = 202
ASSOC_NOTE_TO_DEAL = 214
ASSOC_NOTE_TO_COMPANY = 190
ASSOC_CALL_TO_CONTACT = 194
ASSOC_EMAIL_TO_CONTACT = 198
ASSOC_MEETING_TO_CONTACT = 200


class HubSpotTool(BaseTool):
    """Tool for managing HubSpot CRM objects and activities."""

    name = "hubspot"
    description = "Manage HubSpot CRM — contacts, companies, deals, pipelines, activities."

    def __init__(self, access_token: Optional[str] = None, max_retries: int = 3):
        self.access_token = access_token or os.getenv("HUBSPOT_ACCESS_TOKEN")
        self.max_retries = max_retries
        super().__init__()

    # ── HTTP client ─────────────────────────────────────────────────────
    def _mask(self, text: str) -> str:
        """Redact the access token if it ever appears in a message."""
        if self.access_token and text:
            return text.replace(self.access_token, "***")
        return text

    def _request(
        self,
        method: str,
        path: str,
        json_body: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Perform an authenticated request with 429 retry + backoff."""
        try:
            import requests
        except ImportError:
            return {"error": "requests not installed. Install with: pip install requests"}

        if not self.access_token:
            return {"error": "HUBSPOT_ACCESS_TOKEN required"}

        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.request(
                    method,
                    url,
                    headers=headers,
                    json=json_body,
                    params=params,
                    timeout=30,
                )
            except Exception as e:  # network-level failure
                return {"error": self._mask(str(e))}

            if resp.status_code == 429 and attempt < self.max_retries:
                retry_after = resp.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(delay)
                continue

            if resp.status_code == 204 or not resp.content:
                return {"success": True, "status_code": resp.status_code}

            try:
                data = resp.json()
            except ValueError:
                data = {"raw": resp.text}

            if resp.status_code >= 400:
                message = data.get("message") if isinstance(data, dict) else str(data)
                return {
                    "error": self._mask(message or f"HTTP {resp.status_code}"),
                    "status_code": resp.status_code,
                }
            return data

        return {"error": "Rate limited (429) after retries", "status_code": 429}

    # ── Core dispatch ───────────────────────────────────────────────────
    def run(self, action: str = "search_crm", **kwargs) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        dispatch = {
            "create_contact": self.create_contact,
            "get_contact": self.get_contact,
            "update_contact": self.update_contact,
            "search_contacts": self.search_contacts,
            "delete_contact": self.delete_contact,
            "list_contacts": self.list_contacts,
            "create_company": self.create_company,
            "get_company": self.get_company,
            "update_company": self.update_company,
            "search_companies": self.search_companies,
            "associate_contact_to_company": self.associate_contact_to_company,
            "create_deal": self.create_deal,
            "get_deal": self.get_deal,
            "update_deal": self.update_deal,
            "move_deal_stage": self.move_deal_stage,
            "list_deals": self.list_deals,
            "associate_deal_with_contact": self.associate_deal_with_contact,
            "associate_deal_with_company": self.associate_deal_with_company,
            "list_pipelines": self.list_pipelines,
            "get_pipeline_stages": self.get_pipeline_stages,
            "log_call": self.log_call,
            "log_email": self.log_email,
            "log_meeting": self.log_meeting,
            "create_note": self.create_note,
            "list_activities": self.list_activities,
            "search_crm": self.search_crm,
            "list_properties": self.list_properties,
            "create_property": self.create_property,
        }
        fn = dispatch.get(action)
        if not fn:
            return {"error": f"Unknown action: {action}"}
        return fn(**kwargs)

    # ── Contact Operations ──────────────────────────────────────────────
    def create_contact(
        self,
        email: str,
        firstname: Optional[str] = None,
        lastname: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        **custom_props,
    ) -> Dict[str, Any]:
        """Create a new HubSpot contact. Returns the created id directly."""
        if not email:
            return {"error": "email required"}
        props: Dict[str, Any] = {"email": email}
        for key, val in (
            ("firstname", firstname),
            ("lastname", lastname),
            ("phone", phone),
            ("company", company),
        ):
            if val is not None:
                props[key] = val
        props.update(custom_props)
        return self._request("POST", "/crm/v3/objects/contacts", {"properties": props})

    def get_contact(
        self, contact_id: str, properties: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get contact by ID with selected properties."""
        if not contact_id:
            return {"error": "contact_id required"}
        params = {"properties": ",".join(properties)} if properties else None
        return self._request("GET", f"/crm/v3/objects/contacts/{contact_id}", params=params)

    def update_contact(self, contact_id: str, **properties) -> Dict[str, Any]:
        """Update contact properties."""
        if not contact_id:
            return {"error": "contact_id required"}
        if not properties:
            return {"error": "no properties to update"}
        return self._request(
            "PATCH", f"/crm/v3/objects/contacts/{contact_id}", {"properties": properties}
        )

    def search_contacts(
        self,
        query: Optional[str] = None,
        filters: Optional[List[Dict]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search contacts by query string or filter groups."""
        return self._search("contacts", query=query, filters=filters, limit=limit)

    def delete_contact(self, contact_id: str) -> Dict[str, Any]:
        """Archive (soft-delete) a contact."""
        if not contact_id:
            return {"error": "contact_id required"}
        return self._request("DELETE", f"/crm/v3/objects/contacts/{contact_id}")

    def list_contacts(self, limit: int = 100, after: Optional[str] = None) -> Dict[str, Any]:
        """List contacts with cursor pagination. Returns {results, paging}."""
        params: Dict[str, Any] = {"limit": limit}
        if after:
            params["after"] = after
        return self._request("GET", "/crm/v3/objects/contacts", params=params)

    # ── Company Operations ──────────────────────────────────────────────
    def create_company(
        self,
        name: str,
        domain: Optional[str] = None,
        industry: Optional[str] = None,
        **custom_props,
    ) -> Dict[str, Any]:
        """Create a new company."""
        if not name:
            return {"error": "name required"}
        props: Dict[str, Any] = {"name": name}
        if domain is not None:
            props["domain"] = domain
        if industry is not None:
            props["industry"] = industry
        props.update(custom_props)
        return self._request("POST", "/crm/v3/objects/companies", {"properties": props})

    def get_company(
        self, company_id: str, properties: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get company by ID."""
        if not company_id:
            return {"error": "company_id required"}
        params = {"properties": ",".join(properties)} if properties else None
        return self._request("GET", f"/crm/v3/objects/companies/{company_id}", params=params)

    def update_company(self, company_id: str, **properties) -> Dict[str, Any]:
        """Update company properties."""
        if not company_id:
            return {"error": "company_id required"}
        if not properties:
            return {"error": "no properties to update"}
        return self._request(
            "PATCH", f"/crm/v3/objects/companies/{company_id}", {"properties": properties}
        )

    def search_companies(
        self,
        query: Optional[str] = None,
        filters: Optional[List[Dict]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search companies."""
        return self._search("companies", query=query, filters=filters, limit=limit)

    def associate_contact_to_company(
        self, contact_id: str, company_id: str
    ) -> Dict[str, Any]:
        """Create contact-company association."""
        if not contact_id or not company_id:
            return {"error": "contact_id and company_id required"}
        return self._associate(
            "contacts", contact_id, "companies", company_id, ASSOC_CONTACT_TO_COMPANY
        )

    # ── Deal Operations ─────────────────────────────────────────────────
    def create_deal(
        self,
        dealname: str,
        pipeline: str = "default",
        dealstage: Optional[str] = None,
        amount: Optional[float] = None,
        closedate: Optional[str] = None,
        **custom_props,
    ) -> Dict[str, Any]:
        """Create a new deal. Returns the created id directly."""
        if not dealname:
            return {"error": "dealname required"}
        props: Dict[str, Any] = {"dealname": dealname, "pipeline": pipeline}
        if dealstage is not None:
            props["dealstage"] = dealstage
        if amount is not None:
            props["amount"] = amount
        if closedate is not None:
            props["closedate"] = closedate
        props.update(custom_props)
        return self._request("POST", "/crm/v3/objects/deals", {"properties": props})

    def get_deal(self, deal_id: str, properties: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get deal by ID."""
        if not deal_id:
            return {"error": "deal_id required"}
        params = {"properties": ",".join(properties)} if properties else None
        return self._request("GET", f"/crm/v3/objects/deals/{deal_id}", params=params)

    def update_deal(self, deal_id: str, **properties) -> Dict[str, Any]:
        """Update deal properties."""
        if not deal_id:
            return {"error": "deal_id required"}
        if not properties:
            return {"error": "no properties to update"}
        return self._request(
            "PATCH", f"/crm/v3/objects/deals/{deal_id}", {"properties": properties}
        )

    def move_deal_stage(self, deal_id: str, stage_id: str) -> Dict[str, Any]:
        """Move deal to a specific pipeline stage."""
        if not deal_id or not stage_id:
            return {"error": "deal_id and stage_id required"}
        return self._request(
            "PATCH",
            f"/crm/v3/objects/deals/{deal_id}",
            {"properties": {"dealstage": stage_id}},
        )

    def list_deals(
        self,
        pipeline: Optional[str] = None,
        stage: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List deals, optionally filtered by pipeline and stage."""
        filters = []
        if pipeline:
            filters.append({"propertyName": "pipeline", "operator": "EQ", "value": pipeline})
        if stage:
            filters.append({"propertyName": "dealstage", "operator": "EQ", "value": stage})
        if filters:
            return self._search("deals", filters=filters, limit=limit)
        result = self._request("GET", "/crm/v3/objects/deals", params={"limit": limit})
        if isinstance(result, dict) and "error" in result:
            return [result]
        return result.get("results", []) if isinstance(result, dict) else result

    def associate_deal_with_contact(self, deal_id: str, contact_id: str) -> Dict[str, Any]:
        """Associate a deal with a contact."""
        if not deal_id or not contact_id:
            return {"error": "deal_id and contact_id required"}
        return self._associate(
            "deals", deal_id, "contacts", contact_id, ASSOC_DEAL_TO_CONTACT
        )

    def associate_deal_with_company(self, deal_id: str, company_id: str) -> Dict[str, Any]:
        """Associate a deal with a company."""
        if not deal_id or not company_id:
            return {"error": "deal_id and company_id required"}
        return self._associate(
            "deals", deal_id, "companies", company_id, ASSOC_DEAL_TO_COMPANY
        )

    # ── Pipeline Operations ─────────────────────────────────────────────
    def list_pipelines(self, object_type: str = "deals") -> List[Dict[str, Any]]:
        """List all pipelines for an object type."""
        result = self._request("GET", f"/crm/v3/pipelines/{object_type}")
        if isinstance(result, dict) and "error" in result:
            return [result]
        return result.get("results", []) if isinstance(result, dict) else result

    def get_pipeline_stages(
        self, pipeline_id: str, object_type: str = "deals"
    ) -> List[Dict[str, Any]]:
        """Get stages for a specific pipeline."""
        if not pipeline_id:
            return [{"error": "pipeline_id required"}]
        result = self._request(
            "GET", f"/crm/v3/pipelines/{object_type}/{pipeline_id}/stages"
        )
        if isinstance(result, dict) and "error" in result:
            return [result]
        return result.get("results", []) if isinstance(result, dict) else result

    # ── Activity Logging (v3 CRM objects) ───────────────────────────────
    def log_call(
        self,
        contact_id: str,
        body: str,
        duration_ms: Optional[int] = None,
        direction: str = "OUTBOUND",
    ) -> Dict[str, Any]:
        """Log a call activity on a contact (v3 /crm/v3/objects/calls)."""
        if not contact_id or not body:
            return {"error": "contact_id and body required"}
        props: Dict[str, Any] = {
            "hs_call_body": body,
            "hs_call_direction": direction,
            "hs_timestamp": self._now_ms(),
        }
        if duration_ms is not None:
            props["hs_call_duration"] = duration_ms
        return self._create_activity(
            "calls", props, contact_id, ASSOC_CALL_TO_CONTACT
        )

    def log_email(
        self,
        contact_id: str,
        subject: str,
        body: str,
        direction: str = "OUTBOUND",
    ) -> Dict[str, Any]:
        """Log an email activity (v3 /crm/v3/objects/emails)."""
        if not contact_id or not subject:
            return {"error": "contact_id and subject required"}
        props = {
            "hs_email_subject": subject,
            "hs_email_text": body,
            "hs_email_direction": (
                "EMAIL" if direction.upper() == "OUTBOUND" else "INCOMING_EMAIL"
            ),
            "hs_timestamp": self._now_ms(),
        }
        return self._create_activity(
            "emails", props, contact_id, ASSOC_EMAIL_TO_CONTACT
        )

    def log_meeting(
        self,
        contact_id: str,
        title: str,
        body: Optional[str] = None,
        start_time: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Log a meeting (v3 /crm/v3/objects/meetings)."""
        if not contact_id or not title:
            return {"error": "contact_id and title required"}
        props: Dict[str, Any] = {
            "hs_meeting_title": title,
            "hs_timestamp": start_time or self._now_ms(),
        }
        if body is not None:
            props["hs_meeting_body"] = body
        if duration_ms is not None:
            props["hs_meeting_end_time"] = None  # duration handled by end time
        return self._create_activity(
            "meetings", props, contact_id, ASSOC_MEETING_TO_CONTACT
        )

    def create_note(
        self,
        body: str,
        contact_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a note associated with a CRM object (v3 /crm/v3/objects/notes)."""
        if not body:
            return {"error": "body required"}
        associations = []
        if contact_id:
            associations.append(self._assoc_block("contacts", contact_id, ASSOC_NOTE_TO_CONTACT))
        if deal_id:
            associations.append(self._assoc_block("deals", deal_id, ASSOC_NOTE_TO_DEAL))
        if company_id:
            associations.append(self._assoc_block("companies", company_id, ASSOC_NOTE_TO_COMPANY))
        payload: Dict[str, Any] = {
            "properties": {"hs_note_body": body, "hs_timestamp": self._now_ms()}
        }
        if associations:
            payload["associations"] = associations
        return self._request("POST", "/crm/v3/objects/notes", payload)

    def list_activities(
        self,
        contact_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        activity_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List activity engagements associated with a contact or deal."""
        if not contact_id and not deal_id:
            return [{"error": "contact_id or deal_id required"}]
        from_type = "contacts" if contact_id else "deals"
        from_id = contact_id or deal_id
        types = activity_types or ["notes", "calls", "emails", "meetings"]
        activities: List[Dict[str, Any]] = []
        for to_type in types:
            result = self._request(
                "GET", f"/crm/v3/objects/{from_type}/{from_id}/associations/{to_type}"
            )
            if isinstance(result, dict) and "results" in result:
                for item in result["results"][:limit]:
                    activities.append({"type": to_type, "id": item.get("toObjectId") or item.get("id")})
        return activities[:limit]

    # ── Unified Search ──────────────────────────────────────────────────
    def search_crm(
        self,
        query: str,
        object_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Search across contacts, companies, and deals simultaneously."""
        if not query:
            return {"error": "query required"}
        types = object_types or ["contacts", "companies", "deals"]
        results: Dict[str, Any] = {}
        for object_type in types:
            results[object_type] = self._search(object_type, query=query, limit=limit)
        return results

    # ── Properties ──────────────────────────────────────────────────────
    def list_properties(self, object_type: str = "contacts") -> List[Dict[str, Any]]:
        """List all properties for a CRM object type."""
        result = self._request("GET", f"/crm/v3/properties/{object_type}")
        if isinstance(result, dict) and "error" in result:
            return [result]
        return result.get("results", []) if isinstance(result, dict) else result

    def create_property(
        self,
        object_type: str,
        name: str,
        label: str,
        field_type: str,
        group_name: str = "contactinformation",
    ) -> Dict[str, Any]:
        """Create a custom property."""
        if not name or not label:
            return {"error": "name and label required"}
        payload = {
            "name": name,
            "label": label,
            "type": "string",
            "fieldType": field_type,
            "groupName": group_name,
        }
        return self._request("POST", f"/crm/v3/properties/{object_type}", payload)

    # ── Internal helpers ────────────────────────────────────────────────
    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _assoc_block(to_type: str, to_id: str, type_id: int) -> Dict[str, Any]:
        return {
            "to": {"id": to_id},
            "types": [
                {
                    "associationCategory": "HUBSPOT_DEFINED",
                    "associationTypeId": type_id,
                }
            ],
        }

    def _associate(
        self, from_type: str, from_id: str, to_type: str, to_id: str, type_id: int
    ) -> Dict[str, Any]:
        payload = [
            {
                "associationCategory": "HUBSPOT_DEFINED",
                "associationTypeId": type_id,
            }
        ]
        return self._request(
            "PUT",
            f"/crm/v3/objects/{from_type}/{from_id}/associations/{to_type}/{to_id}",
            payload,
        )

    def _create_activity(
        self, object_type: str, props: Dict[str, Any], contact_id: str, type_id: int
    ) -> Dict[str, Any]:
        payload = {
            "properties": {k: v for k, v in props.items() if v is not None},
            "associations": [self._assoc_block("contacts", contact_id, type_id)],
        }
        return self._request("POST", f"/crm/v3/objects/{object_type}", payload)

    def _search(
        self,
        object_type: str,
        query: Optional[str] = None,
        filters: Optional[List[Dict]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {"limit": limit}
        if query:
            payload["query"] = query
        if filters:
            payload["filterGroups"] = [{"filters": filters}]
        result = self._request(
            "POST", f"/crm/v3/objects/{object_type}/search", payload
        )
        if isinstance(result, dict) and "error" in result:
            return [result]
        return result.get("results", []) if isinstance(result, dict) else result


# ── Standalone tool functions (for direct @tool-style agent use) ────────
def hubspot_search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search HubSpot contacts."""
    return HubSpotTool().search_contacts(query=query)


def hubspot_create_contact(
    email: str, firstname: str = "", lastname: str = "", company: str = ""
) -> Dict[str, Any]:
    """Create a HubSpot contact."""
    return HubSpotTool().create_contact(
        email=email, firstname=firstname, lastname=lastname, company=company
    )


def hubspot_create_deal(
    dealname: str, pipeline: str = "default", dealstage: str = "", amount: float = 0
) -> Dict[str, Any]:
    """Create a HubSpot deal."""
    return HubSpotTool().create_deal(
        dealname=dealname, pipeline=pipeline, dealstage=dealstage, amount=amount
    )


def hubspot_move_deal_stage(deal_id: str, stage_id: str) -> Dict[str, Any]:
    """Move a HubSpot deal to a new stage."""
    return HubSpotTool().move_deal_stage(deal_id=deal_id, stage_id=stage_id)


def hubspot_log_call(contact_id: str, body: str) -> Dict[str, Any]:
    """Log a call on a HubSpot contact."""
    return HubSpotTool().log_call(contact_id=contact_id, body=body)
