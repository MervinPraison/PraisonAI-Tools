"""AWS SES Tool for PraisonAI Agents.

Send emails via AWS SES.

Usage:
    from praisonai_tools import AWSSESTool
    
    ses = AWSSESTool()
    ses.send_email(to="user@example.com", subject="Hello", body="Hi!")

Environment Variables:
    AWS_ACCESS_KEY_ID: AWS access key
    AWS_SECRET_ACCESS_KEY: AWS secret key
    AWS_REGION: AWS region
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class AWSSESTool(BaseTool):
    """Tool for AWS SES email."""
    
    name = "aws_ses"
    description = "Send emails via AWS SES."
    
    def __init__(self, region: Optional[str] = None):
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self._client = None
        super().__init__()
    
    @property
    def client(self):
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise ImportError("boto3 not installed")
            self._client = boto3.client("ses", region_name=self.region)
        return self._client
    
    def run(
        self,
        action: str = "send",
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        if action == "send":
            return self.send_email(to=to, subject=subject, body=body, **kwargs)
        return {"error": f"Unknown action: {action}"}
    
    def send_email(self, to: str, subject: str, body: str, from_email: str = None) -> Dict[str, Any]:
        """Send email."""
        if not to or not subject or not body:
            return {"error": "to, subject, and body are required"}
        
        try:
            resp = self.client.send_email(
                Source=from_email or os.getenv("AWS_SES_FROM_EMAIL", to),
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Text": {"Data": body}},
                },
            )
            return {"success": True, "message_id": resp.get("MessageId")}
        except Exception as e:
            logger.error(f"SES send_email error: {e}")
            return {"error": str(e)}


def ses_send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Send email via SES."""
    return AWSSESTool().send_email(to=to, subject=subject, body=body)
