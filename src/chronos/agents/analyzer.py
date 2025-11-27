"""Calendar analyzer agent for understanding calendar state and patterns."""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from src.chronos.agents.base import BaseAgent, AgentState, AgentRole
from src.chronos.utils.prompts import ChronosPrompts


class CalendarAnalyzerAgent(BaseAgent):
    """Agent that analyzes calendar state and provides insights."""
    
    def __init__(self, llm):
        super().__init__(role=AgentRole.ANALYZER, llm=llm, name="CalendarAnalyzer")
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Analyze calendar and provide insights.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with calendar analysis
        """
        self.logger.info("Analyzing calendar state...")
        
        # Perform analysis
        analysis = {
            "metrics": self._calculate_metrics(state.calendar_events),
            "patterns": self._identify_patterns(state.calendar_events),
            "conflicts": self._detect_conflicts(state.calendar_events),
            "recommendations": await self._generate_insights(state),
        }
        
        state.calendar_analysis = analysis
        state.conflicts = analysis["conflicts"]
        
        self.logger.info(f"Analysis complete: {len(analysis['conflicts'])} conflicts found")
        return state
    
    def _calculate_metrics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate calendar metrics."""
        if not events:
            return {
                "total_events": 0,
                "busy_hours": 0,
                "free_hours": 8,
                "utilization": 0.0,
            }
        
        total_duration = 0
        for event in events:
            if "start" in event and "end" in event:
                try:
                    start = datetime.fromisoformat(event["start"])
                    end = datetime.fromisoformat(event["end"])
                    total_duration += (end - start).seconds / 3600
                except:
                    pass
        
        working_hours = 8
        utilization = min(total_duration / working_hours, 1.0) if working_hours > 0 else 0
        
        return {
            "total_events": len(events),
            "busy_hours": round(total_duration, 2),
            "free_hours": max(working_hours - total_duration, 0),
            "utilization": round(utilization * 100, 1),
        }
    
    def _identify_patterns(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify scheduling patterns."""
        patterns = {
            "peak_hours": [],
            "common_durations": [],
            "frequent_attendees": [],
            "meeting_distribution": defaultdict(int),
        }
        
        hour_counts = defaultdict(int)
        duration_counts = defaultdict(int)
        
        for event in events:
            if "start" in event:
                try:
                    start = datetime.fromisoformat(event["start"])
                    hour_counts[start.hour] += 1
                    
                    if "end" in event:
                        end = datetime.fromisoformat(event["end"])
                        duration = int((end - start).seconds / 60)
                        duration_counts[duration] += 1
                    
                    # Day of week
                    day_name = start.strftime("%A")
                    patterns["meeting_distribution"][day_name] += 1
                except:
                    pass
        
        # Top 3 peak hours
        if hour_counts:
            patterns["peak_hours"] = sorted(
                hour_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
        
        # Common durations
        if duration_counts:
            patterns["common_durations"] = sorted(
                duration_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
        
        return patterns
    
    def _detect_conflicts(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect scheduling conflicts."""
        conflicts = []
        
        # Sort events by start time
        sorted_events = sorted(
            [e for e in events if "start" in e and "end" in e],
            key=lambda x: x["start"]
        )
        
        for i, event1 in enumerate(sorted_events):
            try:
                start1 = datetime.fromisoformat(event1["start"])
                end1 = datetime.fromisoformat(event1["end"])
                
                for event2 in sorted_events[i+1:]:
                    start2 = datetime.fromisoformat(event2["start"])
                    end2 = datetime.fromisoformat(event2["end"])
                    
                    # Check for overlap
                    if start1 < end2 and end1 > start2:
                        conflicts.append({
                            "type": "overlap",
                            "severity": "high",
                            "event1": {
                                "title": event1.get("title", "Untitled"),
                                "start": event1["start"],
                                "end": event1["end"],
                            },
                            "event2": {
                                "title": event2.get("title", "Untitled"),
                                "start": event2["start"],
                                "end": event2["end"],
                            },
                            "overlap_minutes": int((min(end1, end2) - max(start1, start2)).seconds / 60),
                        })
            except:
                continue
        
        # Check for back-to-back meetings (< 5 min gap)
        for i in range(len(sorted_events) - 1):
            try:
                end1 = datetime.fromisoformat(sorted_events[i]["end"])
                start2 = datetime.fromisoformat(sorted_events[i+1]["start"])
                
                gap_minutes = (start2 - end1).seconds / 60
                if 0 < gap_minutes < 5:
                    conflicts.append({
                        "type": "tight_schedule",
                        "severity": "medium",
                        "event1": sorted_events[i].get("title", "Untitled"),
                        "event2": sorted_events[i+1].get("title", "Untitled"),
                        "gap_minutes": gap_minutes,
                    })
            except:
                continue
        
        return conflicts
    
    async def _generate_insights(self, state: AgentState) -> str:
        """Generate AI-powered calendar insights."""
        
        events_text = ChronosPrompts.format_events(state.calendar_events[:10])
        
        prompt = ChronosPrompts.CALENDAR_ANALYSIS.format(
            events=events_text,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        
        insights = await self.generate_response(
            prompt=prompt,
            system_prompt=ChronosPrompts.SYSTEM_PROMPT,
            temperature=0.6,
        )
        
        return insights

