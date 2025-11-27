"""Formatting utilities for calendar events and time expressions."""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dateutil import parser as date_parser
import parsedatetime as pdt


# Initialize parsedatetime calendar
cal = pdt.Calendar()


def format_calendar_event(event: Dict[str, Any]) -> str:
    """
    Format a calendar event for display.
    
    Args:
        event: Event dictionary
        
    Returns:
        Formatted event string
    """
    title = event.get("title", "Untitled Event")
    start = event.get("start", "TBD")
    end = event.get("end", "TBD")
    location = event.get("location", "No location")
    description = event.get("description", "")
    
    formatted = f"📅 {title}\n"
    formatted += f"🕐 {start} → {end}\n"
    formatted += f"📍 {location}\n"
    
    if description:
        formatted += f"📝 {description[:100]}{'...' if len(description) > 100 else ''}\n"
    
    return formatted


def parse_natural_time(time_str: str, reference_time: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Parse natural language time expressions.
    
    Examples:
        "tomorrow at 2pm"
        "next Monday at 10:30am"
        "in 2 hours"
        "3pm to 5pm today"
    
    Args:
        time_str: Natural language time expression
        reference_time: Reference datetime (defaults to now)
        
    Returns:
        Dictionary with parsed time information
    """
    if reference_time is None:
        reference_time = datetime.now()
    
    result = {
        "original": time_str,
        "start": None,
        "end": None,
        "duration_minutes": None,
        "all_day": False,
        "parsed": False,
    }
    
    try:
        # Try parsedatetime first for natural language
        time_struct, parse_status = cal.parse(time_str, reference_time)
        
        if parse_status in [1, 2, 3]:  # Successfully parsed
            parsed_dt = datetime(*time_struct[:6])
            result["start"] = parsed_dt.isoformat()
            result["parsed"] = True
            
            # Check for duration indicators
            duration = extract_duration(time_str)
            if duration:
                result["duration_minutes"] = duration
                result["end"] = (parsed_dt + timedelta(minutes=duration)).isoformat()
            else:
                # Default 1 hour duration
                result["duration_minutes"] = 60
                result["end"] = (parsed_dt + timedelta(hours=1)).isoformat()
        
        # Check for time ranges (e.g., "2pm to 5pm")
        if " to " in time_str.lower() or " - " in time_str:
            result.update(parse_time_range(time_str, reference_time))
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def extract_duration(text: str) -> Optional[int]:
    """
    Extract duration in minutes from text.
    
    Args:
        text: Input text
        
    Returns:
        Duration in minutes or None
    """
    # Pattern for explicit duration (e.g., "30 minutes", "1 hour", "2hrs")
    patterns = [
        (r"(\d+(?:\.\d+)?)\s*hours?", 60),
        (r"(\d+(?:\.\d+)?)\s*hrs?", 60),
        (r"(\d+(?:\.\d+)?)\s*h\b", 60),
        (r"(\d+)\s*minutes?", 1),
        (r"(\d+)\s*mins?", 1),
        (r"(\d+)\s*m\b", 1),
    ]
    
    for pattern, multiplier in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            return int(value * multiplier)
    
    return None


def parse_time_range(time_str: str, reference_time: datetime) -> Dict[str, Any]:
    """
    Parse time range expressions (e.g., "2pm to 5pm").
    
    Args:
        time_str: Time range string
        reference_time: Reference datetime
        
    Returns:
        Dictionary with start and end times
    """
    result = {}
    
    # Split on common separators
    for separator in [" to ", " - ", " till ", " until "]:
        if separator in time_str.lower():
            parts = re.split(separator, time_str, flags=re.IGNORECASE)
            if len(parts) == 2:
                try:
                    start_str, end_str = parts
                    
                    # Parse start time
                    start_struct, _ = cal.parse(start_str.strip(), reference_time)
                    start_dt = datetime(*start_struct[:6])
                    
                    # Parse end time
                    end_struct, _ = cal.parse(end_str.strip(), start_dt)
                    end_dt = datetime(*end_struct[:6])
                    
                    # If end is before start, assume it's the same day
                    if end_dt < start_dt:
                        end_dt = end_dt.replace(
                            year=start_dt.year,
                            month=start_dt.month,
                            day=start_dt.day
                        )
                    
                    result["start"] = start_dt.isoformat()
                    result["end"] = end_dt.isoformat()
                    result["duration_minutes"] = int((end_dt - start_dt).total_seconds() / 60)
                    result["parsed"] = True
                    
                except Exception:
                    pass
                
                break
    
    return result


def format_duration(minutes: int) -> str:
    """
    Format duration in a human-readable way.
    
    Args:
        minutes: Duration in minutes
        
    Returns:
        Formatted duration string
    """
    if minutes < 60:
        return f"{minutes}m"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if remaining_minutes == 0:
        return f"{hours}h"
    
    return f"{hours}h {remaining_minutes}m"


def format_datetime_relative(dt: datetime, reference: Optional[datetime] = None) -> str:
    """
    Format datetime relative to reference time.
    
    Args:
        dt: Datetime to format
        reference: Reference datetime (defaults to now)
        
    Returns:
        Relative time string
    """
    if reference is None:
        reference = datetime.now()
    
    delta = dt - reference
    
    if delta.days == 0:
        if delta.seconds < 3600:
            minutes = delta.seconds // 60
            return f"in {minutes} minute{'s' if minutes != 1 else ''}"
        hours = delta.seconds // 3600
        return f"in {hours} hour{'s' if hours != 1 else ''}"
    
    if delta.days == 1:
        return f"tomorrow at {dt.strftime('%I:%M %p')}"
    
    if delta.days == -1:
        return f"yesterday at {dt.strftime('%I:%M %p')}"
    
    if 0 < delta.days < 7:
        return f"{dt.strftime('%A at %I:%M %p')}"
    
    return dt.strftime("%B %d at %I:%M %p")


def detect_scheduling_intent(text: str) -> Dict[str, Any]:
    """
    Detect scheduling intent and extract key information.
    
    Args:
        text: Input text
        
    Returns:
        Dictionary with detected intent and extracted information
    """
    text_lower = text.lower()
    
    intent = {
        "action": None,
        "confidence": 0.0,
        "entities": {},
    }
    
    # Action patterns
    actions = {
        "schedule": [r"schedule", r"book", r"arrange", r"set up", r"plan"],
        "reschedule": [r"reschedule", r"move", r"change", r"shift"],
        "cancel": [r"cancel", r"delete", r"remove"],
        "check": [r"check", r"what'?s", r"show", r"list", r"when"],
        "find": [r"find", r"available", r"free", r"open"],
    }
    
    for action, patterns in actions.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                intent["action"] = action
                intent["confidence"] = 0.8
                break
        if intent["action"]:
            break
    
    # Extract entities
    # Email patterns
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    if emails:
        intent["entities"]["attendees"] = emails
    
    # Meeting type patterns
    meeting_types = ["meeting", "call", "interview", "sync", "standup", "review"]
    for meeting_type in meeting_types:
        if meeting_type in text_lower:
            intent["entities"]["meeting_type"] = meeting_type
            break
    
    return intent

