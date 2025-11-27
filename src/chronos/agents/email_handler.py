"""Email handler agent for drafting and sending scheduling emails."""

from typing import Dict, Any
from datetime import datetime

from src.chronos.agents.base import BaseAgent, AgentState, AgentRole
from src.chronos.utils.prompts import ChronosPrompts


class EmailHandlerAgent(BaseAgent):
    """Agent responsible for email communication related to scheduling."""
    
    def __init__(self, llm):
        super().__init__(role=AgentRole.EMAIL_HANDLER, llm=llm, name="EmailHandler")
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Handle email-related tasks.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with email draft
        """
        self.logger.info("Handling email communication...")
        
        # Determine if email is needed
        attendees = state.extracted_entities.get("attendees", [])
        
        if not attendees:
            self.logger.info("No attendees found, skipping email")
            return state
        
        # Draft email
        email_draft = await self._draft_email(state)
        state.email_draft = email_draft
        
        self.logger.info("Email draft created")
        return state
    
    async def _draft_email(self, state: AgentState) -> str:
        """Draft a scheduling email using LLM."""
        
        # Determine email purpose
        intent_action = state.intent.get("action", "schedule")
        
        if intent_action == "schedule":
            purpose = "Schedule new meeting"
        elif intent_action == "reschedule":
            purpose = "Reschedule existing meeting"
        elif intent_action == "cancel":
            purpose = "Cancel meeting"
        else:
            purpose = "Meeting invitation"
        
        # Get event details
        event_details = self._format_event_details(state)
        
        # Get recipient(s)
        attendees = state.extracted_entities.get("attendees", [])
        recipient = attendees[0] if attendees else "team"
        
        prompt = ChronosPrompts.EMAIL_DRAFT.format(
            purpose=purpose,
            recipient=recipient,
            event_details=event_details,
            context=f"Original request: {state.user_request}",
        )
        
        email = await self.generate_response(
            prompt=prompt,
            system_prompt="You are a professional email writer. Write clear, concise, and friendly emails.",
            temperature=0.7,
        )
        
        return email.strip()
    
    def _format_event_details(self, state: AgentState) -> str:
        """Format event details for email."""
        recommendation = state.scheduling_recommendation
        entities = state.extracted_entities
        
        details = []
        
        # Title
        if entities.get("title"):
            details.append(f"Meeting: {entities['title']}")
        
        # Proposed time
        if recommendation.get("proposed_slot"):
            slot = recommendation["proposed_slot"]
            try:
                start_dt = datetime.fromisoformat(slot["start"])
                end_dt = datetime.fromisoformat(slot["end"])
                details.append(f"Time: {start_dt.strftime('%A, %B %d at %I:%M %p')} - {end_dt.strftime('%I:%M %p')}")
            except:
                details.append(f"Time: {slot.get('start', 'TBD')}")
        
        # Duration
        if entities.get("duration_minutes"):
            details.append(f"Duration: {entities['duration_minutes']} minutes")
        
        # Location
        if entities.get("location"):
            details.append(f"Location: {entities['location']}")
        
        # Description
        if entities.get("description"):
            details.append(f"Description: {entities['description']}")
        
        # Attendees
        attendees = entities.get("attendees", [])
        if len(attendees) > 1:
            others = ", ".join(attendees[1:])
            details.append(f"Other attendees: {others}")
        
        return "\n".join(details)

