"""Main LangGraph workflow for Chronos autonomous scheduling agent."""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig

from src.chronos.agents.base import AgentState
from src.chronos.agents.scheduler import SchedulerAgent
from src.chronos.agents.analyzer import CalendarAnalyzerAgent
from src.chronos.agents.resolver import ConflictResolverAgent
from src.chronos.agents.email_handler import EmailHandlerAgent
from src.chronos.models.llama import LlamaModel
from src.chronos.utils.logger import get_logger

logger = get_logger(__name__)


class ChronosWorkflow:
    """
    LangGraph-based workflow for autonomous scheduling.
    
    This workflow orchestrates multiple specialized agents:
    1. CalendarAnalyzer - Analyzes current calendar state
    2. Scheduler - Proposes scheduling options
    3. ConflictResolver - Resolves conflicts if any
    4. EmailHandler - Drafts communication emails
    """
    
    def __init__(self, llm: Optional[LlamaModel] = None):
        """
        Initialize the Chronos workflow.
        
        Args:
            llm: Language model instance (creates new one if not provided)
        """
        self.llm = llm or LlamaModel()
        
        # Initialize agents
        self.analyzer_agent = CalendarAnalyzerAgent(self.llm)
        self.scheduler_agent = SchedulerAgent(self.llm)
        self.resolver_agent = ConflictResolverAgent(self.llm)
        self.email_agent = EmailHandlerAgent(self.llm)
        
        # Build graph
        self.graph = self._build_graph()
        self.compiled_graph = None
        
        logger.info("Chronos workflow initialized")
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph state graph.
        
        Returns:
            Configured StateGraph
        """
        # Create graph with AgentState
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyzer", self._analyzer_node)
        workflow.add_node("scheduler", self._scheduler_node)
        workflow.add_node("resolver", self._resolver_node)
        workflow.add_node("email", self._email_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Define the workflow flow
        workflow.set_entry_point("analyzer")
        
        # Analyzer -> Scheduler (always)
        workflow.add_edge("analyzer", "scheduler")
        
        # Scheduler -> Conditional routing
        workflow.add_conditional_edges(
            "scheduler",
            self._route_after_scheduler,
            {
                "resolver": "resolver",
                "email": "email",
                "finalize": "finalize",
            }
        )
        
        # Resolver -> Email (always)
        workflow.add_edge("resolver", "email")
        
        # Email -> Finalize
        workflow.add_edge("email", "finalize")
        
        # Finalize -> END
        workflow.add_edge("finalize", END)
        
        logger.info("Workflow graph built successfully")
        return workflow
    
    async def _analyzer_node(self, state: AgentState) -> AgentState:
        """Analyzer agent node."""
        logger.info("Executing Analyzer node")
        return await self.analyzer_agent.invoke(state)
    
    async def _scheduler_node(self, state: AgentState) -> AgentState:
        """Scheduler agent node."""
        logger.info("Executing Scheduler node")
        return await self.scheduler_agent.invoke(state)
    
    async def _resolver_node(self, state: AgentState) -> AgentState:
        """Conflict resolver agent node."""
        logger.info("Executing Resolver node")
        return await self.resolver_agent.invoke(state)
    
    async def _email_node(self, state: AgentState) -> AgentState:
        """Email handler agent node."""
        logger.info("Executing Email node")
        return await self.email_agent.invoke(state)
    
    async def _finalize_node(self, state: AgentState) -> AgentState:
        """Finalize the workflow and prepare response."""
        logger.info("Finalizing workflow")
        
        # Generate final response
        if state.scheduling_recommendation:
            recommendation = state.scheduling_recommendation
            slot = recommendation.get("proposed_slot")
            
            if slot:
                response = f"✅ I've found a great time slot for you!\n\n"
                response += f"📅 Proposed Time: {slot.get('start', 'TBD')}\n"
                response += f"⏱️ Duration: {state.extracted_entities.get('duration_minutes', 60)} minutes\n"
                
                if state.conflicts:
                    response += f"\n⚠️ Note: {len(state.conflicts)} conflict(s) detected. "
                    response += "I've proposed a resolution strategy.\n"
                
                if state.email_draft:
                    response += f"\n📧 I've drafted an email to notify attendees.\n"
                
                response += f"\n{recommendation.get('reasoning', '')}"
                
                state.success = True
            else:
                response = "❌ I couldn't find a suitable time slot. Please provide more details or try a different time range."
                state.success = False
        else:
            response = "❌ Unable to process scheduling request. Please try again."
            state.success = False
        
        state.final_response = response
        state.completed_at = state.started_at  # Update timestamp
        
        logger.info(f"Workflow completed. Success: {state.success}")
        return state
    
    def _route_after_scheduler(self, state: AgentState) -> str:
        """
        Route to appropriate next node after scheduler.
        
        Args:
            state: Current agent state
            
        Returns:
            Next node name
        """
        # Check if there are conflicts
        if state.conflicts:
            logger.info("Routing to resolver due to conflicts")
            return "resolver"
        
        # Check if email is needed
        if state.extracted_entities.get("attendees"):
            logger.info("Routing to email handler")
            return "email"
        
        # No conflicts or emails needed
        logger.info("Routing directly to finalize")
        return "finalize"
    
    async def initialize(self) -> None:
        """Initialize the workflow and compile the graph."""
        logger.info("Initializing Chronos workflow...")
        
        # Initialize LLM
        if not self.llm.is_initialized:
            await self.llm.initialize()
        
        # Compile graph
        self.compiled_graph = self.graph.compile()
        
        logger.info("Workflow initialization complete")
    
    async def run(
        self,
        user_request: str,
        calendar_events: list[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        config: Optional[RunnableConfig] = None,
    ) -> AgentState:
        """
        Run the workflow with a user request.
        
        Args:
            user_request: User's scheduling request
            calendar_events: Current calendar events
            user_id: Optional user identifier
            config: Optional LangGraph configuration
            
        Returns:
            Final agent state
        """
        if not self.compiled_graph:
            await self.initialize()
        
        # Create initial state
        initial_state = AgentState(
            user_request=user_request,
            calendar_events=calendar_events or [],
            user_id=user_id,
        )
        
        logger.info(f"Running workflow for request: {user_request}")
        
        try:
            # Execute the workflow
            final_state = await self.compiled_graph.ainvoke(initial_state, config=config)
            
            logger.info(f"Workflow completed successfully")
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            initial_state.add_error(str(e))
            initial_state.final_response = f"❌ Error: {str(e)}"
            return initial_state
    
    async def stream(
        self,
        user_request: str,
        calendar_events: list[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ):
        """
        Stream workflow execution (yields state updates).
        
        Args:
            user_request: User's scheduling request
            calendar_events: Current calendar events
            user_id: Optional user identifier
            
        Yields:
            State updates as the workflow progresses
        """
        if not self.compiled_graph:
            await self.initialize()
        
        initial_state = AgentState(
            user_request=user_request,
            calendar_events=calendar_events or [],
            user_id=user_id,
        )
        
        logger.info(f"Streaming workflow for request: {user_request}")
        
        async for state in self.compiled_graph.astream(initial_state):
            yield state


def create_workflow(llm: Optional[LlamaModel] = None) -> ChronosWorkflow:
    """
    Factory function to create a Chronos workflow.
    
    Args:
        llm: Optional LLM instance
        
    Returns:
        Configured ChronosWorkflow
    """
    return ChronosWorkflow(llm=llm)

