"""
Email Tool - Parse and extract structured data from emails.

Provides capabilities for:
- Email parsing (headers, body, attachments)
- Structured data extraction
- Privacy-safe handling with PII redaction
"""

import os
import re
import email
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
from email import policy
from email.parser import BytesParser, Parser

try:
    from .base import RecipeToolBase, RecipeToolResult
except ImportError:
    from base import RecipeToolBase, RecipeToolResult

logger = logging.getLogger(__name__)


@dataclass
class EmailAttachment:
    """Email attachment metadata."""
    filename: str
    content_type: str
    size: int
    content: Optional[bytes] = None


@dataclass
class ParsedEmail(RecipeToolResult):
    """Parsed email result."""
    subject: str = ""
    sender: str = ""
    recipients: List[str] = field(default_factory=list)
    cc: List[str] = field(default_factory=list)
    date: str = ""
    body_text: str = ""
    body_html: str = ""
    attachments: List[EmailAttachment] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExtractedData(RecipeToolResult):
    """Extracted structured data from email."""
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


class EmailTool(RecipeToolBase):
    """Email parsing and extraction tool."""
    
    def __init__(self, redact_pii: bool = True):
        self.redact_pii = redact_pii
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are available."""
        return {"email": True}  # Built-in module
    
    def _redact_pii(self, text: str) -> str:
        """Redact personally identifiable information."""
        if not self.redact_pii:
            return text
        
        # Redact email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        # Redact phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        # Redact SSN
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
        # Redact credit card numbers
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', text)
        
        return text
    
    def parse(self, email_path: str, extract_attachments: bool = False) -> ParsedEmail:
        """
        Parse an email file (.eml).
        
        Args:
            email_path: Path to .eml file
            extract_attachments: If True, include attachment content
            
        Returns:
            ParsedEmail with parsed data
        """
        if not os.path.exists(email_path):
            return ParsedEmail(success=False, error=f"Email file not found: {email_path}")
        
        with open(email_path, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)
        
        return self._parse_message(msg, extract_attachments)
    
    def parse_string(self, email_content: str, extract_attachments: bool = False) -> ParsedEmail:
        """
        Parse email from string content.
        
        Args:
            email_content: Raw email content as string
            extract_attachments: If True, include attachment content
            
        Returns:
            ParsedEmail with parsed data
        """
        msg = Parser(policy=policy.default).parsestr(email_content)
        return self._parse_message(msg, extract_attachments)
    
    def _parse_message(self, msg, extract_attachments: bool) -> ParsedEmail:
        """Parse email.message.Message object."""
        # Extract headers
        subject = str(msg.get('Subject', ''))
        sender = str(msg.get('From', ''))
        date = str(msg.get('Date', ''))
        
        # Parse recipients
        to_header = msg.get('To', '')
        recipients = [addr.strip() for addr in str(to_header).split(',')] if to_header else []
        
        cc_header = msg.get('Cc', '')
        cc = [addr.strip() for addr in str(cc_header).split(',')] if cc_header else []
        
        # Extract body
        body_text = ""
        body_html = ""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                
                if 'attachment' in content_disposition:
                    # Handle attachment
                    filename = part.get_filename() or 'attachment'
                    content = part.get_payload(decode=True) if extract_attachments else None
                    attachments.append(EmailAttachment(
                        filename=filename,
                        content_type=content_type,
                        size=len(part.get_payload(decode=True) or b''),
                        content=content,
                    ))
                elif content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode('utf-8', errors='replace')
                elif content_type == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_html = payload.decode('utf-8', errors='replace')
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                if content_type == 'text/html':
                    body_html = payload.decode('utf-8', errors='replace')
                else:
                    body_text = payload.decode('utf-8', errors='replace')
        
        # Apply PII redaction if enabled
        if self.redact_pii:
            body_text = self._redact_pii(body_text)
            body_html = self._redact_pii(body_html)
        
        # Collect headers
        headers = {key: str(value) for key, value in msg.items()}
        
        return ParsedEmail(
            success=True,
            subject=subject,
            sender=sender if not self.redact_pii else self._redact_pii(sender),
            recipients=recipients if not self.redact_pii else [self._redact_pii(r) for r in recipients],
            cc=cc if not self.redact_pii else [self._redact_pii(c) for c in cc],
            date=date,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            headers=headers,
        )
    
    def extract_fields(
        self,
        email_path: str,
        fields: List[str],
        use_llm: bool = False,
        llm_provider: str = "openai",
    ) -> ExtractedData:
        """
        Extract specific fields from email content.
        
        Args:
            email_path: Path to email file
            fields: List of field names to extract
            use_llm: Use LLM for intelligent extraction
            llm_provider: LLM provider to use
            
        Returns:
            ExtractedData with extracted fields
        """
        parsed = self.parse(email_path)
        if not parsed.success:
            return ExtractedData(success=False, error=parsed.error)
        
        if use_llm:
            return self._extract_with_llm(parsed, fields, llm_provider)
        else:
            return self._extract_basic(parsed, fields)
    
    def _extract_basic(self, parsed: ParsedEmail, fields: List[str]) -> ExtractedData:
        """Basic field extraction using regex patterns."""
        data = {}
        text = f"{parsed.subject}\n{parsed.body_text}"
        
        patterns = {
            "order_number": r'(?:order|confirmation|ref)[\s#:]*([A-Z0-9-]+)',
            "tracking_number": r'(?:tracking|shipment)[\s#:]*([A-Z0-9]+)',
            "amount": r'\$[\d,]+\.?\d*',
            "date": r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            "url": r'https?://[^\s<>"]+',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        }
        
        for field in fields:
            if field in patterns:
                matches = re.findall(patterns[field], text, re.IGNORECASE)
                data[field] = matches[0] if len(matches) == 1 else matches if matches else None
            elif field == "subject":
                data[field] = parsed.subject
            elif field == "sender":
                data[field] = parsed.sender
            elif field == "date":
                data[field] = parsed.date
        
        return ExtractedData(success=True, data=data, confidence=0.7)
    
    def _extract_with_llm(
        self,
        parsed: ParsedEmail,
        fields: List[str],
        provider: str,
    ) -> ExtractedData:
        """Extract fields using LLM."""
        try:
            from .llm_tool import LLMTool
        except ImportError:
            from llm_tool import LLMTool
        
        llm = LLMTool(provider=provider)
        
        prompt = f"""Extract the following fields from this email:
Fields to extract: {', '.join(fields)}

Email Subject: {parsed.subject}
Email Body:
{parsed.body_text[:2000]}

Return a JSON object with the extracted fields. Use null for fields not found."""
        
        schema = {field: "string or null" for field in fields}
        
        try:
            data = llm.extract_json(prompt, schema)
            return ExtractedData(success=True, data=data, confidence=0.9)
        except Exception as e:
            return ExtractedData(success=False, error=str(e))
    
    def summarize(
        self,
        email_path: str,
        llm_provider: str = "openai",
    ) -> str:
        """
        Summarize email content using LLM.
        
        Args:
            email_path: Path to email file
            llm_provider: LLM provider to use
            
        Returns:
            Summary string
        """
        parsed = self.parse(email_path)
        if not parsed.success:
            return f"Error: {parsed.error}"
        
        try:
            from .llm_tool import LLMTool
        except ImportError:
            from llm_tool import LLMTool
        
        llm = LLMTool(provider=llm_provider)
        
        prompt = f"""Summarize this email in 2-3 sentences:

Subject: {parsed.subject}
From: {parsed.sender}
Date: {parsed.date}

Body:
{parsed.body_text[:3000]}"""
        
        response = llm.complete(prompt, system="You are a helpful assistant that summarizes emails concisely.")
        return response.content


# Convenience functions
def email_parse(email_path: str, redact_pii: bool = True) -> ParsedEmail:
    """Parse email file."""
    tool = EmailTool(redact_pii=redact_pii)
    return tool.parse(email_path)


def email_extract(email_path: str, fields: List[str], use_llm: bool = False) -> Dict[str, Any]:
    """Extract fields from email."""
    tool = EmailTool()
    result = tool.extract_fields(email_path, fields, use_llm=use_llm)
    return result.data if result.success else {}


__all__ = [
    "EmailTool",
    "ParsedEmail",
    "EmailAttachment",
    "ExtractedData",
    "email_parse",
    "email_extract",
]
