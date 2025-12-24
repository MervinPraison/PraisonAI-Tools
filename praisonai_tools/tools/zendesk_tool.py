"""Zendesk Tool for PraisonAI Agents.

Manage Zendesk tickets and users.

Usage:
    from praisonai_tools import ZendeskTool
    
    zendesk = ZendeskTool()
    tickets = zendesk.list_tickets()

Environment Variables:
    ZENDESK_SUBDOMAIN: Zendesk subdomain
    ZENDESK_EMAIL: Zendesk user email
    ZENDESK_API_TOKEN: Zendesk API token
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ZendeskTool(BaseTool):
    """Tool for Zendesk support operations."""
    
    name = "zendesk"
    description = "Manage Zendesk tickets and users."
    
    def __init__(
        self,
        subdomain: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.subdomain = subdomain or os.getenv("ZENDESK_SUBDOMAIN")
        self.email = email or os.getenv("ZENDESK_EMAIL")
        self.api_token = api_token or os.getenv("ZENDESK_API_TOKEN")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                from zenpy import Zenpy
            except ImportError:
                raise ImportError("zenpy not installed. Install with: pip install zenpy")
            
            if not all([self.subdomain, self.email, self.api_token]):
                raise ValueError("ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, and ZENDESK_API_TOKEN required")
            
            self._client = Zenpy(
                subdomain=self.subdomain,
                email=self.email,
                token=self.api_token,
            )
        return self._client
    
    def run(
        self,
        action: str = "list_tickets",
        ticket_id: Optional[int] = None,
        subject: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "list_tickets":
            return self.list_tickets(**kwargs)
        elif action == "get_ticket":
            return self.get_ticket(ticket_id=ticket_id)
        elif action == "create_ticket":
            return self.create_ticket(subject=subject, **kwargs)
        elif action == "update_ticket":
            return self.update_ticket(ticket_id=ticket_id, **kwargs)
        elif action == "search_tickets":
            return self.search_tickets(query=kwargs.get("query"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def list_tickets(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List tickets."""
        try:
            tickets = []
            for ticket in self.client.tickets(limit=limit):
                tickets.append({
                    "id": ticket.id,
                    "subject": ticket.subject,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "created_at": str(ticket.created_at),
                })
                if len(tickets) >= limit:
                    break
            return tickets
        except Exception as e:
            logger.error(f"Zendesk list_tickets error: {e}")
            return [{"error": str(e)}]
    
    def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        """Get ticket details."""
        if not ticket_id:
            return {"error": "ticket_id is required"}
        
        try:
            ticket = self.client.tickets(id=ticket_id)
            return {
                "id": ticket.id,
                "subject": ticket.subject,
                "description": ticket.description,
                "status": ticket.status,
                "priority": ticket.priority,
                "requester_id": ticket.requester_id,
                "created_at": str(ticket.created_at),
                "updated_at": str(ticket.updated_at),
            }
        except Exception as e:
            logger.error(f"Zendesk get_ticket error: {e}")
            return {"error": str(e)}
    
    def create_ticket(self, subject: str, description: str = None, priority: str = "normal") -> Dict[str, Any]:
        """Create a ticket."""
        if not subject:
            return {"error": "subject is required"}
        
        try:
            from zenpy.lib.api_objects import Ticket
            
            ticket = Ticket(
                subject=subject,
                description=description or subject,
                priority=priority,
            )
            result = self.client.tickets.create(ticket)
            return {
                "success": True,
                "id": result.ticket.id,
                "subject": result.ticket.subject,
            }
        except Exception as e:
            logger.error(f"Zendesk create_ticket error: {e}")
            return {"error": str(e)}
    
    def update_ticket(self, ticket_id: int, status: str = None, priority: str = None) -> Dict[str, Any]:
        """Update a ticket."""
        if not ticket_id:
            return {"error": "ticket_id is required"}
        
        try:
            ticket = self.client.tickets(id=ticket_id)
            if status:
                ticket.status = status
            if priority:
                ticket.priority = priority
            self.client.tickets.update(ticket)
            return {"success": True, "id": ticket_id}
        except Exception as e:
            logger.error(f"Zendesk update_ticket error: {e}")
            return {"error": str(e)}
    
    def search_tickets(self, query: str) -> List[Dict[str, Any]]:
        """Search tickets."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            tickets = []
            for ticket in self.client.search(query, type="ticket"):
                tickets.append({
                    "id": ticket.id,
                    "subject": ticket.subject,
                    "status": ticket.status,
                })
            return tickets[:20]
        except Exception as e:
            logger.error(f"Zendesk search_tickets error: {e}")
            return [{"error": str(e)}]


def list_zendesk_tickets(limit: int = 20) -> List[Dict[str, Any]]:
    """List Zendesk tickets."""
    return ZendeskTool().list_tickets(limit=limit)
