"""FastAPI application for Chronos autonomous scheduling agent."""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json

from src.chronos.graph.workflow import ChronosWorkflow, create_workflow
from src.chronos.integrations.gmail import GmailIntegration
from src.chronos.integrations.calendar import GoogleCalendarIntegration
from src.chronos.config import config
from src.chronos.utils.logger import get_logger

logger = get_logger(__name__)


# Request/Response models
class SchedulingRequest(BaseModel):
    """Request model for scheduling."""
    request: str
    user_id: Optional[str] = None
    include_calendar: bool = True


class SchedulingResponse(BaseModel):
    """Response model for scheduling."""
    success: bool
    response: str
    recommendation: Optional[Dict[str, Any]] = None
    conflicts: List[Dict[str, Any]] = []
    email_draft: Optional[str] = None
    metadata: Dict[str, Any] = {}


class CalendarEvent(BaseModel):
    """Calendar event model."""
    title: str
    start: str
    end: str
    description: Optional[str] = ""
    location: Optional[str] = ""
    attendees: List[str] = []


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    model_loaded: bool


# Global instances
workflow: Optional[ChronosWorkflow] = None
gmail: Optional[GmailIntegration] = None
calendar_api: Optional[GoogleCalendarIntegration] = None


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="Chronos Autonomous Scheduling Agent",
        description="AI-powered autonomous agent for intelligent scheduling using LangGraph, Llama 3, and DPO",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup."""
        global workflow, gmail, calendar_api
        
        logger.info("Starting Chronos API server...")
        
        # Initialize workflow
        logger.info("Initializing workflow...")
        workflow = create_workflow()
        await workflow.initialize()
        
        # Initialize integrations
        logger.info("Initializing integrations...")
        gmail = GmailIntegration()
        calendar_api = GoogleCalendarIntegration()
        
        logger.info("✅ Chronos API server ready!")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        global workflow
        
        logger.info("Shutting down Chronos API server...")
        
        if workflow and workflow.llm:
            await workflow.llm.cleanup()
        
        logger.info("Shutdown complete")
    
    @app.get("/", response_model=HealthResponse)
    async def root():
        """Root endpoint with health check."""
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            model_loaded=workflow is not None and workflow.llm.is_initialized
        )
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint."""
        return HealthResponse(
            status="healthy" if workflow and workflow.llm.is_initialized else "initializing",
            version="1.0.0",
            model_loaded=workflow is not None and workflow.llm.is_initialized
        )
    
    @app.post("/schedule", response_model=SchedulingResponse)
    async def schedule(request: SchedulingRequest):
        """
        Process a scheduling request.
        
        Args:
            request: Scheduling request details
            
        Returns:
            Scheduling response with recommendation
        """
        if not workflow:
            raise HTTPException(status_code=503, detail="Workflow not initialized")
        
        try:
            # Get calendar events if requested
            calendar_events = []
            if request.include_calendar and calendar_api:
                try:
                    calendar_events = await calendar_api.get_events()
                except Exception as e:
                    logger.warning(f"Failed to fetch calendar: {e}")
            
            # Run workflow
            final_state = await workflow.run(
                user_request=request.request,
                calendar_events=calendar_events,
                user_id=request.user_id,
            )
            
            # Prepare response
            response = SchedulingResponse(
                success=final_state.success,
                response=final_state.final_response,
                recommendation=final_state.scheduling_recommendation,
                conflicts=final_state.conflicts,
                email_draft=final_state.email_draft,
                metadata={
                    "iterations": final_state.iterations,
                    "agent_history": final_state.agent_history,
                    "errors": final_state.errors,
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Scheduling failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/schedule/stream")
    async def schedule_stream(request: SchedulingRequest):
        """
        Stream scheduling workflow execution.
        
        Args:
            request: Scheduling request
            
        Returns:
            Server-sent events stream
        """
        if not workflow:
            raise HTTPException(status_code=503, detail="Workflow not initialized")
        
        async def event_generator():
            try:
                calendar_events = []
                if request.include_calendar and calendar_api:
                    try:
                        calendar_events = await calendar_api.get_events()
                    except:
                        pass
                
                async for state_update in workflow.stream(
                    user_request=request.request,
                    calendar_events=calendar_events,
                    user_id=request.user_id,
                ):
                    # Send state update as SSE
                    yield f"data: {json.dumps(state_update)}\n\n"
                    await asyncio.sleep(0)
                
            except Exception as e:
                logger.error(f"Stream failed: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
    
    @app.get("/calendar/events")
    async def get_calendar_events(days: int = 7):
        """
        Get calendar events for the next N days.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of calendar events
        """
        if not calendar_api:
            raise HTTPException(status_code=503, detail="Calendar API not initialized")
        
        try:
            events = await calendar_api.get_events()
            return {"events": events}
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/calendar/create")
    async def create_calendar_event(event: CalendarEvent):
        """Create a new calendar event."""
        if not calendar_api:
            raise HTTPException(status_code=503, detail="Calendar API not initialized")
        
        try:
            from datetime import datetime
            
            start = datetime.fromisoformat(event.start)
            end = datetime.fromisoformat(event.end)
            
            event_id = await calendar_api.create_event(
                title=event.title,
                start_time=start,
                end_time=end,
                description=event.description,
                location=event.location,
                attendees=event.attendees,
            )
            
            return {"success": True, "event_id": event_id}
            
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/email/send")
    async def send_email(
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None
    ):
        """Send an email via Gmail."""
        if not gmail:
            raise HTTPException(status_code=503, detail="Gmail API not initialized")
        
        try:
            success = await gmail.send_email(
                to=to,
                subject=subject,
                body=body,
                cc=cc
            )
            
            return {"success": success}
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/stats")
    async def get_stats():
        """Get system statistics."""
        return {
            "workflow_initialized": workflow is not None,
            "model_loaded": workflow.llm.is_initialized if workflow else False,
            "model_name": workflow.llm.model_name if workflow else "unknown",
            "gmail_connected": gmail.is_authenticated if gmail else False,
            "calendar_connected": calendar_api.is_authenticated if calendar_api else False,
        }
    
    return app


# For running with uvicorn
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.chronos.api.app:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        log_level=config.api.log_level,
    )

