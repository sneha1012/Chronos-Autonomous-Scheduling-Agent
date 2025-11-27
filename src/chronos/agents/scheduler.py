"""Scheduler agent for creating and managing calendar events."""

import json
from typing import Dict, Any
from datetime import datetime, timedelta

from src.chronos.agents.base import BaseAgent, AgentState, AgentRole
from src.chronos.utils.prompts import ChronosPrompts
from src.chronos.utils.formatting import parse_natural_time, detect_scheduling_intent


class SchedulerAgent(BaseAgent):
    """Agent responsible for scheduling logic and event creation."""
    
    def __init__(self, llm):
        super().__init__(role=AgentRole.SCHEDULER, llm=llm, name="Scheduler")
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Process scheduling request and generate recommendations.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with scheduling recommendation
        """
        self.logger.info("Processing scheduling request...")
        
        # Step 1: Detect intent if not already done
        if not state.intent:
            state.intent = detect_scheduling_intent(state.user_request)
            self.logger.info(f"Detected intent: {state.intent}")
        
        # Step 2: Parse time expressions
        if not state.parsed_time:
            state.parsed_time = parse_natural_time(state.user_request)
            self.logger.info(f"Parsed time: {state.parsed_time}")
        
        # Step 3: Extract event details using LLM
        event_details = await self._extract_event_details(state)
        state.extracted_entities = event_details
        
        # Step 4: Find suitable time slots
        suitable_slots = await self._find_time_slots(state)
        state.available_slots = suitable_slots
        
        # Step 5: Generate scheduling recommendation
        recommendation = await self._generate_recommendation(state)
        state.scheduling_recommendation = recommendation
        
        self.logger.info(f"Scheduling recommendation: {recommendation}")
        return state
    
    async def _extract_event_details(self, state: AgentState) -> Dict[str, Any]:
        """Extract event details from user request using LLM."""
        
        prompt = f"""Extract structured event information from this scheduling request:

Request: "{state.user_request}"

Extract the following in JSON format:
- title: (event title/summary)
- duration_minutes: (estimated duration)
- priority: (high/medium/low)
- attendees: (list of email addresses if mentioned)
- location: (physical or virtual location)
- description: (additional context)
- preferences: (any timing preferences mentioned)

Respond with ONLY valid JSON, no additional text."""
        
        response = await self.generate_response(
            prompt=prompt,
            system_prompt="You are a precise information extraction assistant. Always respond with valid JSON.",
            temperature=0.3,
        )
        
        try:
            # Clean response and parse JSON
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            details = json.loads(response)
            return details
        except Exception as e:
            self.logger.warning(f"Failed to parse event details: {e}")
            return {
                "title": "Meeting",
                "duration_minutes": 60,
                "priority": "medium",
                "attendees": [],
                "location": "",
                "description": state.user_request,
            }
    
    async def _find_time_slots(self, state: AgentState) -> list[Dict[str, Any]]:
        """Find available time slots based on calendar and preferences."""
        
        # Get current events
        events = state.calendar_events
        
        # Determine search window
        if state.parsed_time.get("start"):
            try:
                start_time = datetime.fromisoformat(state.parsed_time["start"])
            except:
                start_time = datetime.now()
        else:
            start_time = datetime.now()
        
        # Search for next 7 days
        end_search = start_time + timedelta(days=7)
        
        # Get duration
        duration_minutes = state.extracted_entities.get("duration_minutes", 60)
        
        # Find gaps in calendar
        available_slots = []
        current_time = start_time.replace(hour=9, minute=0, second=0)  # Start at 9 AM
        
        while current_time < end_search:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            # Check if slot overlaps with existing events
            is_free = True
            for event in events:
                event_start = datetime.fromisoformat(event.get("start", ""))
                event_end = datetime.fromisoformat(event.get("end", ""))
                
                if (current_time < event_end and slot_end > event_start):
                    is_free = False
                    break
            
            if is_free and 9 <= current_time.hour < 17:  # Within working hours
                available_slots.append({
                    "start": current_time.isoformat(),
                    "end": slot_end.isoformat(),
                    "score": self._calculate_slot_score(current_time, state),
                })
            
            # Move to next slot (30-minute increments)
            current_time += timedelta(minutes=30)
        
        # Sort by score and return top 5
        available_slots.sort(key=lambda x: x["score"], reverse=True)
        return available_slots[:5]
    
    def _calculate_slot_score(self, slot_time: datetime, state: AgentState) -> float:
        """Calculate desirability score for a time slot."""
        score = 100.0
        
        # Prefer earlier in the week
        score -= slot_time.weekday() * 5
        
        # Prefer mid-morning (10-11 AM) or early afternoon (2-3 PM)
        hour = slot_time.hour
        if 10 <= hour <= 11 or 14 <= hour <= 15:
            score += 20
        elif hour < 9 or hour > 16:
            score -= 30
        
        # Avoid Mondays and Fridays slightly
        if slot_time.weekday() == 0:  # Monday
            score -= 5
        elif slot_time.weekday() == 4:  # Friday
            score -= 10
        
        # Priority boost for urgent requests
        priority = state.extracted_entities.get("priority", "medium")
        if priority == "high":
            # Prefer sooner for high priority
            days_away = (slot_time.date() - datetime.now().date()).days
            score -= days_away * 10
        
        return score
    
    async def _generate_recommendation(self, state: AgentState) -> Dict[str, Any]:
        """Generate final scheduling recommendation using LLM."""
        
        # Format calendar state
        calendar_state = ChronosPrompts.format_calendar_state({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "event_count": len(state.calendar_events),
            "busy_hours": sum((datetime.fromisoformat(e["end"]) - 
                             datetime.fromisoformat(e["start"])).seconds / 3600 
                            for e in state.calendar_events if "start" in e and "end" in e),
            "free_hours": 8,
        })
        
        # Format available slots
        slots_text = "\n".join([
            f"{i+1}. {slot['start']} (Score: {slot['score']:.1f})"
            for i, slot in enumerate(state.available_slots)
        ])
        
        prompt = ChronosPrompts.SCHEDULING_REQUEST.format(
            request=state.user_request,
            calendar_state=calendar_state,
            available_slots=slots_text,
        )
        
        response = await self.generate_response(
            prompt=prompt,
            system_prompt=ChronosPrompts.SYSTEM_PROMPT,
            temperature=0.5,
        )
        
        # Create recommendation structure
        best_slot = state.available_slots[0] if state.available_slots else None
        
        recommendation = {
            "proposed_slot": best_slot,
            "reasoning": response,
            "alternatives": state.available_slots[1:3] if len(state.available_slots) > 1 else [],
            "event_details": state.extracted_entities,
            "confidence": 0.9 if best_slot else 0.3,
        }
        
        return recommendation

