"""Google Calendar API integration."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.chronos.config import config
from src.chronos.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleCalendarIntegration:
    """Google Calendar API integration for calendar management."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ]
    
    def __init__(self):
        """Initialize Calendar integration."""
        self.creds = None
        self.service = None
        self.is_authenticated = False
    
    async def authenticate(self) -> bool:
        """Authenticate with Google Calendar API."""
        try:
            if config.google.token_file.exists():
                self.creds = Credentials.from_authorized_user_file(
                    str(config.google.token_file),
                    self.SCOPES
                )
            
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
                
                config.google.token_file.write_text(self.creds.to_json())
            
            self.service = build('calendar', 'v3', credentials=self.creds)
            self.is_authenticated = True
            logger.info("Calendar authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Calendar authentication failed: {e}")
            return False
    
    async def get_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get calendar events.
        
        Args:
            time_min: Start time (defaults to now)
            time_max: End time (defaults to 7 days from now)
            max_results: Maximum number of events
            
        Returns:
            List of event dictionaries
        """
        if not self.is_authenticated:
            await self.authenticate()
        
        if time_min is None:
            time_min = datetime.utcnow()
        if time_max is None:
            time_max = time_min + timedelta(days=7)
        
        try:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            parsed_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                parsed_events.append({
                    'id': event['id'],
                    'title': event.get('summary', 'Untitled'),
                    'start': start,
                    'end': end,
                    'location': event.get('location', ''),
                    'description': event.get('description', ''),
                    'attendees': [
                        a.get('email') for a in event.get('attendees', [])
                    ],
                    'link': event.get('htmlLink', ''),
                })
            
            logger.info(f"Retrieved {len(parsed_events)} calendar events")
            return parsed_events
            
        except HttpError as e:
            logger.error(f"Failed to retrieve events: {e}")
            return []
    
    async def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: str = "",
        location: str = "",
        attendees: List[str] = None,
    ) -> Optional[str]:
        """
        Create a calendar event.
        
        Args:
            title: Event title
            start_time: Start datetime
            end_time: End datetime
            description: Event description
            location: Event location
            attendees: List of attendee emails
            
        Returns:
            Event ID if created successfully
        """
        if not self.is_authenticated:
            await self.authenticate()
        
        event = {
            'summary': title,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
        }
        
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        try:
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            logger.info(f"Event created: {created_event['id']}")
            return created_event['id']
            
        except HttpError as e:
            logger.error(f"Failed to create event: {e}")
            return None
    
    async def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None,
    ) -> bool:
        """Update an existing event."""
        if not self.is_authenticated:
            await self.authenticate()
        
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            # Update fields
            if title:
                event['summary'] = title
            if start_time:
                event['start']['dateTime'] = start_time.isoformat()
            if end_time:
                event['end']['dateTime'] = end_time.isoformat()
            if description:
                event['description'] = description
            
            # Update event
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()
            
            logger.info(f"Event updated: {updated_event['id']}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to update event: {e}")
            return False
    
    async def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        if not self.is_authenticated:
            await self.authenticate()
        
        try:
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            logger.info(f"Event deleted: {event_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to delete event: {e}")
            return False

