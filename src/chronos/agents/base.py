"""Base agent class and shared state management."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.chronos.models.llama import LlamaModel
from src.chronos.utils.logger import get_logger

logger = get_logger(__name__)


class AgentRole(Enum):
    """Agent role types."""
    SCHEDULER = "scheduler"
    ANALYZER = "analyzer"
    RESOLVER = "resolver"
    EMAIL_HANDLER = "email_handler"
    COORDINATOR = "coordinator"


@dataclass
class AgentState:
    """Shared state between agents in the workflow."""
    
    # Input
    user_request: str = ""
    user_id: Optional[str] = None
    
    # Calendar data
    calendar_events: List[Dict[str, Any]] = field(default_factory=list)
    available_slots: List[Dict[str, Any]] = field(default_factory=list)
    
    # Parsed information
    intent: Dict[str, Any] = field(default_factory=dict)
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    parsed_time: Dict[str, Any] = field(default_factory=dict)
    
    # Analysis results
    calendar_analysis: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Decisions
    scheduling_recommendation: Dict[str, Any] = field(default_factory=dict)
    conflict_resolution: Dict[str, Any] = field(default_factory=dict)
    
    # Email handling
    email_draft: Optional[str] = None
    email_sent: bool = False
    
    # Metadata
    current_agent: Optional[str] = None
    agent_history: List[str] = field(default_factory=list)
    iterations: int = 0
    max_iterations: int = 10
    errors: List[str] = field(default_factory=list)
    
    # Final result
    success: bool = False
    final_response: str = ""
    action_taken: Optional[Dict[str, Any]] = None
    
    # Timestamps
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        logger.error(f"Agent error: {error}")
    
    def set_current_agent(self, agent_name: str) -> None:
        """Set the current active agent."""
        self.current_agent = agent_name
        self.agent_history.append(agent_name)
        logger.info(f"Agent activated: {agent_name}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "user_request": self.user_request,
            "intent": self.intent,
            "calendar_events_count": len(self.calendar_events),
            "conflicts_count": len(self.conflicts),
            "recommendation": self.scheduling_recommendation,
            "success": self.success,
            "final_response": self.final_response,
            "agent_history": self.agent_history,
            "iterations": self.iterations,
            "errors": self.errors,
        }


class BaseAgent(ABC):
    """Base class for all agents in the Chronos system."""
    
    def __init__(
        self,
        role: AgentRole,
        llm: LlamaModel,
        name: Optional[str] = None,
    ):
        """
        Initialize the agent.
        
        Args:
            role: Agent's role in the system
            llm: Language model for reasoning
            name: Agent name (defaults to role name)
        """
        self.role = role
        self.llm = llm
        self.name = name or role.value
        self.logger = get_logger(f"agent.{self.name}")
    
    @abstractmethod
    async def process(self, state: AgentState) -> AgentState:
        """
        Process the current state and return updated state.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state
        """
        pass
    
    async def invoke(self, state: AgentState) -> AgentState:
        """
        Invoke the agent with state management.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state
        """
        self.logger.info(f"Agent {self.name} invoked")
        state.set_current_agent(self.name)
        state.iterations += 1
        
        try:
            updated_state = await self.process(state)
            self.logger.info(f"Agent {self.name} completed successfully")
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Agent {self.name} failed: {e}")
            state.add_error(f"{self.name}: {str(e)}")
            return state
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        """
        Generate a response using the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Generated response text
        """
        response = await self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content
    
    def log_state(self, state: AgentState, message: str = "") -> None:
        """
        Log current state information.
        
        Args:
            state: Current state
            message: Optional message
        """
        self.logger.debug(
            f"{message} | "
            f"Iteration: {state.iterations} | "
            f"Errors: {len(state.errors)} | "
            f"Success: {state.success}"
        )

