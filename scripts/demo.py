"""Demo script for Chronos agent."""

import asyncio
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from src.chronos.graph.workflow import create_workflow

console = Console()


def create_mock_calendar_events():
    """Create mock calendar events for demo."""
    now = datetime.now()
    
    events = [
        {
            "id": "1",
            "title": "Engineering Standup",
            "start": (now + timedelta(days=1, hours=10)).isoformat(),
            "end": (now + timedelta(days=1, hours=10, minutes=30)).isoformat(),
            "location": "Zoom",
            "description": "Daily team sync",
        },
        {
            "id": "2",
            "title": "Product Review",
            "start": (now + timedelta(days=1, hours=14)).isoformat(),
            "end": (now + timedelta(days=1, hours=15)).isoformat(),
            "location": "Conference Room A",
            "description": "Q4 product review with stakeholders",
        },
        {
            "id": "3",
            "title": "1-on-1 with Manager",
            "start": (now + timedelta(days=2, hours=11)).isoformat(),
            "end": (now + timedelta(days=2, hours=11, minutes=30)).isoformat(),
            "location": "Zoom",
            "description": "Weekly sync",
        },
    ]
    
    return events


async def run_demo():
    """Run interactive demo."""
    console.print(Panel.fit(
        "[bold blue]🤖 Chronos Autonomous Scheduling Agent[/bold blue]\n"
        "[dim]Powered by LangGraph, Llama 3, and DPO[/dim]",
        border_style="blue"
    ))
    
    console.print("\n[yellow]Initializing agent...[/yellow]")
    
    # Create workflow
    workflow = create_workflow()
    await workflow.initialize()
    
    console.print("[green]✓ Agent initialized![/green]\n")
    
    # Mock calendar
    calendar_events = create_mock_calendar_events()
    
    console.print(f"[cyan]📅 Loaded {len(calendar_events)} calendar events[/cyan]\n")
    
    # Demo requests
    demo_requests = [
        "Schedule a team meeting for next Tuesday afternoon",
        "Find time for a client demo next week",
        "Book 30 minutes for code review tomorrow",
    ]
    
    console.print("[bold]Demo Requests:[/bold]")
    for i, req in enumerate(demo_requests, 1):
        console.print(f"  {i}. {req}")
    
    console.print("\n[bold]Select a request (1-3) or type your own:[/bold] ", end="")
    user_input = input().strip()
    
    if user_input.isdigit() and 1 <= int(user_input) <= len(demo_requests):
        request = demo_requests[int(user_input) - 1]
    else:
        request = user_input
    
    console.print(f"\n[yellow]Processing: '{request}'[/yellow]\n")
    
    # Run workflow
    try:
        result = await workflow.run(
            user_request=request,
            calendar_events=calendar_events,
        )
        
        # Display results
        console.print(Panel(
            result.final_response,
            title="[bold green]✓ Response[/bold green]",
            border_style="green"
        ))
        
        # Show recommendation
        if result.scheduling_recommendation:
            rec = result.scheduling_recommendation
            console.print("\n[bold]📋 Scheduling Recommendation:[/bold]")
            
            if rec.get("proposed_slot"):
                slot = rec["proposed_slot"]
                console.print(f"  • Time: {slot.get('start', 'TBD')}")
                console.print(f"  • Confidence: {rec.get('confidence', 0) * 100:.0f}%")
            
            if rec.get("alternatives"):
                console.print(f"\n[dim]  {len(rec['alternatives'])} alternative options available[/dim]")
        
        # Show conflicts
        if result.conflicts:
            console.print(f"\n[yellow]⚠️  Detected {len(result.conflicts)} conflict(s)[/yellow]")
        
        # Show email draft
        if result.email_draft:
            console.print("\n[bold]📧 Email Draft:[/bold]")
            console.print(Panel(
                result.email_draft,
                border_style="blue"
            ))
        
        # Metadata
        console.print(f"\n[dim]Agent iterations: {result.iterations}[/dim]")
        console.print(f"[dim]Agents used: {', '.join(result.agent_history)}[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
    
    console.print("\n[green]Demo complete![/green]")


if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")

