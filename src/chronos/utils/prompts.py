"""Prompt templates for Chronos agent."""

from typing import Dict, Any


class ChronosPrompts:
    """Collection of prompts for different agent tasks."""
    
    SYSTEM_PROMPT = """You are Chronos, an advanced autonomous scheduling assistant powered by state-of-the-art AI.

Your capabilities:
- Intelligent calendar management and scheduling
- Natural language understanding of time and dates
- Conflict detection and resolution
- Priority-based scheduling
- Context-aware meeting suggestions
- Email integration for scheduling

Your personality:
- Professional yet friendly
- Proactive in suggesting optimizations
- Clear in communication
- Respectful of user's time and preferences

Always:
1. Confirm before making changes
2. Explain your reasoning
3. Provide alternatives when conflicts exist
4. Be concise but thorough"""

    CALENDAR_ANALYSIS = """Analyze the following calendar events and provide insights:

Events:
{events}

Current Time: {current_time}

Tasks:
1. Identify scheduling conflicts
2. Suggest optimization opportunities
3. Flag overbooked periods
4. Recommend breaks or buffer time

Provide your analysis in a structured format."""

    SCHEDULING_REQUEST = """Process the following scheduling request:

User Request: "{request}"
Current Calendar State:
{calendar_state}

Available Time Slots:
{available_slots}

Tasks:
1. Parse the request to extract:
   - Event title
   - Duration
   - Preferred time/date
   - Priority level
   - Attendees (if any)
   
2. Find suitable time slots
3. Consider conflicts and priorities
4. Propose the best option(s)

Respond with your recommendation and reasoning."""

    CONFLICT_RESOLUTION = """Resolve the following scheduling conflict:

New Event: {new_event}
Conflicting Events:
{conflicts}

Context:
{context}

Tasks:
1. Analyze priority levels
2. Consider flexibility of each event
3. Propose resolution strategies:
   - Reschedule options
   - Duration adjustments
   - Alternative times
   
4. Recommend the optimal solution

Provide your recommendation with clear reasoning."""

    EMAIL_DRAFT = """Draft a scheduling-related email:

Purpose: {purpose}
Recipient: {recipient}
Event Details:
{event_details}

Context: {context}

Create a professional, friendly email that:
1. Clearly states the purpose
2. Provides all necessary details
3. Includes call-to-action if needed
4. Maintains appropriate tone

Email:"""

    TIME_PARSING = """Parse natural language time expressions into structured format:

Input: "{time_expression}"

Extract:
- Date (YYYY-MM-DD)
- Time (HH:MM)
- Duration (minutes)
- Recurrence (if applicable)
- Timezone

Output as JSON."""

    PREFERENCE_LEARNING = """Learn from user feedback on scheduling:

Scheduled Event:
{scheduled_event}

User Feedback: {feedback}
Feedback Type: {feedback_type} (positive/negative)

Tasks:
1. Identify patterns in preferences
2. Extract scheduling constraints
3. Update preference model
4. Suggest policy adjustments

Analysis:"""

    @staticmethod
    def format_events(events: list[Dict[str, Any]]) -> str:
        """Format events for display in prompts."""
        if not events:
            return "No events scheduled."
        
        formatted = []
        for idx, event in enumerate(events, 1):
            formatted.append(
                f"{idx}. {event.get('title', 'Untitled')}\n"
                f"   Time: {event.get('start', 'TBD')} - {event.get('end', 'TBD')}\n"
                f"   Location: {event.get('location', 'Not specified')}\n"
                f"   Priority: {event.get('priority', 'Medium')}"
            )
        return "\n\n".join(formatted)
    
    @staticmethod
    def format_calendar_state(state: Dict[str, Any]) -> str:
        """Format calendar state information."""
        return f"""Date: {state.get('date', 'Unknown')}
Total Events: {state.get('event_count', 0)}
Busy Hours: {state.get('busy_hours', 0)}h
Free Hours: {state.get('free_hours', 0)}h
Peak Busy: {state.get('peak_busy', 'Unknown')}
Next Available: {state.get('next_available', 'Unknown')}"""

