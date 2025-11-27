"""Conflict resolver agent for handling scheduling conflicts."""

from typing import Dict, Any
from datetime import datetime, timedelta

from src.chronos.agents.base import BaseAgent, AgentState, AgentRole
from src.chronos.utils.prompts import ChronosPrompts


class ConflictResolverAgent(BaseAgent):
    """Agent specialized in resolving scheduling conflicts."""
    
    def __init__(self, llm):
        super().__init__(role=AgentRole.RESOLVER, llm=llm, name="ConflictResolver")
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Resolve scheduling conflicts.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with conflict resolution
        """
        self.logger.info("Resolving conflicts...")
        
        if not state.conflicts:
            self.logger.info("No conflicts to resolve")
            state.conflict_resolution = {"status": "no_conflicts"}
            return state
        
        # Analyze conflicts
        resolution = await self._generate_resolution(state)
        state.conflict_resolution = resolution
        
        self.logger.info(f"Resolution strategy: {resolution.get('strategy')}")
        return state
    
    async def _generate_resolution(self, state: AgentState) -> Dict[str, Any]:
        """Generate conflict resolution strategy using LLM."""
        
        # Prepare conflict context
        conflicts_text = self._format_conflicts(state.conflicts)
        
        # Get new event details
        new_event = {
            "title": state.extracted_entities.get("title", "New Event"),
            "duration": state.extracted_entities.get("duration_minutes", 60),
            "priority": state.extracted_entities.get("priority", "medium"),
            "proposed_time": state.scheduling_recommendation.get("proposed_slot"),
        }
        
        prompt = ChronosPrompts.CONFLICT_RESOLUTION.format(
            new_event=str(new_event),
            conflicts=conflicts_text,
            context=f"User request: {state.user_request}",
        )
        
        response = await self.generate_response(
            prompt=prompt,
            system_prompt=ChronosPrompts.SYSTEM_PROMPT,
            temperature=0.5,
        )
        
        # Determine resolution strategy
        strategy = self._determine_strategy(state.conflicts)
        
        return {
            "status": "resolved",
            "strategy": strategy,
            "reasoning": response,
            "action_required": self._get_required_actions(strategy, state),
            "alternatives": self._propose_alternatives(state),
        }
    
    def _format_conflicts(self, conflicts: list[Dict[str, Any]]) -> str:
        """Format conflicts for display."""
        if not conflicts:
            return "No conflicts detected."
        
        formatted = []
        for i, conflict in enumerate(conflicts, 1):
            if conflict["type"] == "overlap":
                formatted.append(
                    f"{i}. OVERLAP ({conflict['severity']})\n"
                    f"   {conflict['event1']['title']}: {conflict['event1']['start']} - {conflict['event1']['end']}\n"
                    f"   {conflict['event2']['title']}: {conflict['event2']['start']} - {conflict['event2']['end']}\n"
                    f"   Overlap: {conflict['overlap_minutes']} minutes"
                )
            elif conflict["type"] == "tight_schedule":
                formatted.append(
                    f"{i}. TIGHT SCHEDULE ({conflict['severity']})\n"
                    f"   Only {conflict['gap_minutes']:.0f} minutes between:\n"
                    f"   - {conflict['event1']}\n"
                    f"   - {conflict['event2']}"
                )
        
        return "\n\n".join(formatted)
    
    def _determine_strategy(self, conflicts: list[Dict[str, Any]]) -> str:
        """Determine the best resolution strategy."""
        if not conflicts:
            return "no_action"
        
        high_severity = any(c.get("severity") == "high" for c in conflicts)
        
        if high_severity:
            return "reschedule_existing"
        else:
            return "adjust_timing"
    
    def _get_required_actions(self, strategy: str, state: AgentState) -> list[str]:
        """Get list of actions needed to resolve conflicts."""
        actions = []
        
        if strategy == "reschedule_existing":
            actions.append("Notify affected participants")
            actions.append("Propose alternative times")
            actions.append("Wait for confirmation")
        
        elif strategy == "adjust_timing":
            actions.append("Adjust meeting duration")
            actions.append("Add buffer time")
        
        return actions
    
    def _propose_alternatives(self, state: AgentState) -> list[Dict[str, Any]]:
        """Propose alternative scheduling options."""
        alternatives = []
        
        # Use available slots from scheduler
        for slot in state.available_slots[1:4]:  # Skip first (already proposed)
            alternatives.append({
                "time": slot["start"],
                "score": slot["score"],
                "conflicts": 0,  # These should be conflict-free
            })
        
        return alternatives

