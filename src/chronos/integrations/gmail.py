"""Gmail API integration for email handling."""

import base64
from email.mime.text import MIMEText
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.chronos.config import config
from src.chronos.utils.logger import get_logger

logger = get_logger(__name__)


class GmailIntegration:
    """Gmail API integration for sending scheduling emails."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly'
    ]
    
    def __init__(self):
        """Initialize Gmail integration."""
        self.creds = None
        self.service = None
        self.is_authenticated = False
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Gmail API.
        
        Returns:
            True if authentication successful
        """
        try:
            # Check if token.json exists
            if config.google.token_file.exists():
                self.creds = Credentials.from_authorized_user_file(
                    str(config.google.token_file),
                    self.SCOPES
                )
            
            # Refresh or create new credentials
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not config.google.credentials_file.exists():
                        logger.error("credentials.json not found")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(config.google.credentials_file),
                        self.SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                
                # Save credentials
                config.google.token_file.write_text(self.creds.to_json())
            
            # Build service
            self.service = build('gmail', 'v1', credentials=self.creds)
            self.is_authenticated = True
            logger.info("Gmail authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send an email via Gmail.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            cc: CC recipients
            bcc: BCC recipients
            
        Returns:
            True if sent successfully
        """
        if not self.is_authenticated:
            await self.authenticate()
        
        try:
            message = MIMEText(body)
            message['To'] = to
            message['Subject'] = subject
            
            if cc:
                message['Cc'] = ', '.join(cc)
            
            if bcc:
                message['Bcc'] = ', '.join(bcc)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send message
            send_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"Email sent successfully. Message ID: {send_message['id']}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def get_recent_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent emails.
        
        Args:
            max_results: Maximum number of emails to retrieve
            
        Returns:
            List of email dictionaries
        """
        if not self.is_authenticated:
            await self.authenticate()
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata'
                ).execute()
                
                headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
                
                emails.append({
                    'id': msg['id'],
                    'from': headers.get('From', ''),
                    'subject': headers.get('Subject', ''),
                    'date': headers.get('Date', ''),
                })
            
            return emails
            
        except HttpError as e:
            logger.error(f"Failed to retrieve emails: {e}")
            return []
    
    async def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
    ) -> Optional[str]:
        """
        Create an email draft.
        
        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            
        Returns:
            Draft ID if created successfully
        """
        if not self.is_authenticated:
            await self.authenticate()
        
        try:
            message = MIMEText(body)
            message['To'] = to
            message['Subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            draft = self.service.users().drafts().create(
                userId='me',
                body={
                    'message': {
                        'raw': raw_message
                    }
                }
            ).execute()
            
            logger.info(f"Draft created successfully. Draft ID: {draft['id']}")
            return draft['id']
            
        except HttpError as e:
            logger.error(f"Failed to create draft: {e}")
            return None

