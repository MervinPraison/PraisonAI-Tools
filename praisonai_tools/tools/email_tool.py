"""Email Tool for PraisonAI Agents.

Provides email sending and reading capabilities via SMTP/IMAP.
Supports multiple providers (Gmail, Outlook, custom SMTP).

Usage:
    from praisonai_tools import EmailTool
    
    # Simple usage with Gmail
    email = EmailTool(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="your@gmail.com",
        password="your-app-password"  # Use App Password, not regular password
    )
    
    # Send email
    result = email.send(
        to="recipient@example.com",
        subject="Hello",
        body="This is a test email"
    )

Environment Variables:
    EMAIL_SMTP_HOST: SMTP server hostname
    EMAIL_SMTP_PORT: SMTP server port (default: 587)
    EMAIL_USERNAME: Email username/address
    EMAIL_PASSWORD: Email password or app password
    EMAIL_IMAP_HOST: IMAP server hostname (for reading)
    EMAIL_IMAP_PORT: IMAP server port (default: 993)
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class EmailTool(BaseTool):
    """Tool for sending and reading emails.
    
    Supports SMTP for sending and IMAP for reading emails.
    Works with Gmail, Outlook, and custom SMTP/IMAP servers.
    
    Attributes:
        name: Tool identifier
        description: Tool description for LLM
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port
        imap_host: IMAP server hostname  
        imap_port: IMAP server port
        username: Email username
        password: Email password/app password
        use_tls: Whether to use TLS encryption
    """
    
    name = "email"
    description = "Send and read emails. Can send emails with attachments and read inbox messages."
    
    # Common provider configurations
    PROVIDERS = {
        "gmail": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "imap_host": "imap.gmail.com",
            "imap_port": 993,
        },
        "outlook": {
            "smtp_host": "smtp.office365.com",
            "smtp_port": 587,
            "imap_host": "outlook.office365.com",
            "imap_port": 993,
        },
        "yahoo": {
            "smtp_host": "smtp.mail.yahoo.com",
            "smtp_port": 587,
            "imap_host": "imap.mail.yahoo.com",
            "imap_port": 993,
        },
    }
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        imap_host: Optional[str] = None,
        imap_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        provider: Optional[str] = None,
        use_tls: bool = True,
        default_from: Optional[str] = None,
    ):
        """Initialize EmailTool.
        
        Args:
            smtp_host: SMTP server hostname (or use EMAIL_SMTP_HOST env var)
            smtp_port: SMTP server port (or use EMAIL_SMTP_PORT env var)
            imap_host: IMAP server hostname (or use EMAIL_IMAP_HOST env var)
            imap_port: IMAP server port (or use EMAIL_IMAP_PORT env var)
            username: Email username (or use EMAIL_USERNAME env var)
            password: Email password (or use EMAIL_PASSWORD env var)
            provider: Shortcut for common providers: "gmail", "outlook", "yahoo"
            use_tls: Whether to use TLS (default: True)
            default_from: Default sender address (defaults to username)
        """
        # Apply provider defaults if specified
        if provider and provider.lower() in self.PROVIDERS:
            config = self.PROVIDERS[provider.lower()]
            smtp_host = smtp_host or config["smtp_host"]
            smtp_port = smtp_port or config["smtp_port"]
            imap_host = imap_host or config["imap_host"]
            imap_port = imap_port or config["imap_port"]
        
        # Get from environment if not provided
        self.smtp_host = smtp_host or os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.imap_host = imap_host or os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
        self.imap_port = imap_port or int(os.getenv("EMAIL_IMAP_PORT", "993"))
        self.username = username or os.getenv("EMAIL_USERNAME")
        self.password = password or os.getenv("EMAIL_PASSWORD")
        self.use_tls = use_tls
        self.default_from = default_from or self.username
        
        super().__init__()
    
    def run(
        self,
        action: str = "send",
        to: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        html: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        folder: str = "INBOX",
        limit: int = 10,
        unread_only: bool = False,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Execute email action.
        
        Args:
            action: "send" to send email, "read" to read inbox, "search" to search
            to: Recipient email address(es), comma-separated
            subject: Email subject
            body: Plain text body
            html: HTML body (optional, takes precedence over body)
            cc: CC recipients, comma-separated
            bcc: BCC recipients, comma-separated
            attachments: List of file paths to attach
            folder: IMAP folder to read from (default: INBOX)
            limit: Maximum emails to return when reading
            unread_only: Only return unread emails
            
        Returns:
            Success message or email data
        """
        action = action.lower()
        
        if action == "send":
            return self.send(
                to=to,
                subject=subject,
                body=body,
                html=html,
                cc=cc,
                bcc=bcc,
                attachments=attachments
            )
        elif action == "read":
            return self.read(
                folder=folder,
                limit=limit,
                unread_only=unread_only
            )
        elif action == "search":
            query = kwargs.get("query", "")
            return self.search(query=query, folder=folder, limit=limit)
        else:
            return f"Unknown action: {action}. Use 'send', 'read', or 'search'."
    
    def send(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        from_addr: Optional[str] = None,
    ) -> str:
        """Send an email.
        
        Args:
            to: Recipient email address(es), comma-separated
            subject: Email subject
            body: Plain text body
            html: HTML body (optional)
            cc: CC recipients, comma-separated
            bcc: BCC recipients, comma-separated
            attachments: List of file paths to attach
            from_addr: Sender address (defaults to username)
            
        Returns:
            Success or error message
        """
        if not self.username or not self.password:
            return "Error: Email credentials not configured. Set EMAIL_USERNAME and EMAIL_PASSWORD."
        
        if not to:
            return "Error: Recipient (to) is required."
        
        if not subject:
            return "Error: Subject is required."
        
        if not body and not html:
            return "Error: Body or HTML content is required."
        
        try:
            import smtplib
        except ImportError:
            return "Error: smtplib not available."
        
        try:
            # Create message
            if html or attachments:
                msg = MIMEMultipart("alternative" if html else "mixed")
                msg.attach(MIMEText(body or "", "plain"))
                if html:
                    msg.attach(MIMEText(html, "html"))
            else:
                msg = MIMEText(body, "plain")
            
            msg["Subject"] = subject
            msg["From"] = from_addr or self.default_from
            msg["To"] = to
            
            if cc:
                msg["Cc"] = cc
            if bcc:
                msg["Bcc"] = bcc
            
            # Add attachments
            if attachments:
                for filepath in attachments:
                    if os.path.exists(filepath):
                        with open(filepath, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                "Content-Disposition",
                                f"attachment; filename={os.path.basename(filepath)}"
                            )
                            msg.attach(part)
                    else:
                        logger.warning(f"Attachment not found: {filepath}")
            
            # Build recipient list
            recipients = [addr.strip() for addr in to.split(",")]
            if cc:
                recipients.extend([addr.strip() for addr in cc.split(",")])
            if bcc:
                recipients.extend([addr.strip() for addr in bcc.split(",")])
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.default_from, recipients, msg.as_string())
            
            logger.info(f"Email sent to {to}")
            return f"Email sent successfully to {to}"
            
        except smtplib.SMTPAuthenticationError:
            return "Error: Authentication failed. Check username and password."
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return f"Error sending email: {str(e)}"
        except Exception as e:
            logger.error(f"Email error: {e}")
            return f"Error: {str(e)}"
    
    def read(
        self,
        folder: str = "INBOX",
        limit: int = 10,
        unread_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Read emails from inbox.
        
        Args:
            folder: IMAP folder to read from
            limit: Maximum number of emails to return
            unread_only: Only return unread emails
            
        Returns:
            List of email dictionaries with subject, from, date, body
        """
        if not self.username or not self.password:
            return [{"error": "Email credentials not configured."}]
        
        try:
            import imaplib
            import email
            from email.header import decode_header
        except ImportError:
            return [{"error": "imaplib not available."}]
        
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.username, self.password)
            mail.select(folder)
            
            # Search for emails
            search_criteria = "UNSEEN" if unread_only else "ALL"
            _, message_numbers = mail.search(None, search_criteria)
            
            emails = []
            message_ids = message_numbers[0].split()
            
            # Get latest emails (reverse order)
            for num in reversed(message_ids[-limit:]):
                _, msg_data = mail.fetch(num, "(RFC822)")
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Decode subject
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")
                        
                        # Decode from
                        from_addr, encoding = decode_header(msg.get("From", ""))[0]
                        if isinstance(from_addr, bytes):
                            from_addr = from_addr.decode(encoding or "utf-8")
                        
                        # Get body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()
                        
                        emails.append({
                            "subject": subject,
                            "from": from_addr,
                            "date": msg.get("Date", ""),
                            "body": body[:500] + "..." if len(body) > 500 else body
                        })
            
            mail.close()
            mail.logout()
            
            return emails
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP error: {e}")
            return [{"error": f"IMAP error: {str(e)}"}]
        except Exception as e:
            logger.error(f"Email read error: {e}")
            return [{"error": str(e)}]
    
    def search(
        self,
        query: str,
        folder: str = "INBOX",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search emails by subject or sender.
        
        Args:
            query: Search query (searches subject and from)
            folder: IMAP folder to search
            limit: Maximum results
            
        Returns:
            List of matching emails
        """
        if not self.username or not self.password:
            return [{"error": "Email credentials not configured."}]
        
        try:
            import imaplib
            import email
            from email.header import decode_header
        except ImportError:
            return [{"error": "imaplib not available."}]
        
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.username, self.password)
            mail.select(folder)
            
            # Search by subject or from
            _, subject_nums = mail.search(None, f'SUBJECT "{query}"')
            _, from_nums = mail.search(None, f'FROM "{query}"')
            
            # Combine results
            all_nums = set(subject_nums[0].split() + from_nums[0].split())
            
            emails = []
            for num in list(all_nums)[-limit:]:
                _, msg_data = mail.fetch(num, "(RFC822)")
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")
                        
                        from_addr, encoding = decode_header(msg.get("From", ""))[0]
                        if isinstance(from_addr, bytes):
                            from_addr = from_addr.decode(encoding or "utf-8")
                        
                        emails.append({
                            "subject": subject,
                            "from": from_addr,
                            "date": msg.get("Date", ""),
                        })
            
            mail.close()
            mail.logout()
            
            return emails
            
        except Exception as e:
            logger.error(f"Email search error: {e}")
            return [{"error": str(e)}]


# Convenience functions for direct use
def send_email(
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    attachments: Optional[List[str]] = None,
    provider: str = "gmail",
) -> str:
    """Send an email using environment credentials.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body text
        html: Optional HTML body
        cc: CC recipients
        bcc: BCC recipients
        attachments: List of file paths
        provider: Email provider (gmail, outlook, yahoo)
        
    Returns:
        Success or error message
    """
    tool = EmailTool(provider=provider)
    return tool.send(to=to, subject=subject, body=body, html=html, cc=cc, bcc=bcc, attachments=attachments)


def read_emails(
    folder: str = "INBOX",
    limit: int = 10,
    unread_only: bool = False,
    provider: str = "gmail",
) -> List[Dict[str, Any]]:
    """Read emails from inbox using environment credentials.
    
    Args:
        folder: IMAP folder
        limit: Max emails to return
        unread_only: Only unread emails
        provider: Email provider
        
    Returns:
        List of email dictionaries
    """
    tool = EmailTool(provider=provider)
    return tool.read(folder=folder, limit=limit, unread_only=unread_only)


def search_emails(
    query: str,
    folder: str = "INBOX",
    limit: int = 10,
    provider: str = "gmail",
) -> List[Dict[str, Any]]:
    """Search emails using environment credentials.
    
    Args:
        query: Search query
        folder: IMAP folder
        limit: Max results
        provider: Email provider
        
    Returns:
        List of matching emails
    """
    tool = EmailTool(provider=provider)
    return tool.search(query=query, folder=folder, limit=limit)
