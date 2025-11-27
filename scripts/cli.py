"""Simple CLI for Chronos agent."""

import asyncio
import argparse
from rich.console import Console
from rich.prompt import Prompt

from src.chronos.graph.workflow import create_workflow

console = Console()


async def interactive_mode():
    """Run in interactive mode."""
    console.print("[bold blue]Chronos Interactive Mode[/bold blue]")
    console.print("[dim]Type 'exit' to quit, 'help' for examples[/dim]\n")
    
    workflow = create_workflow()
    await workflow.initialize()
    
    while True:
        request = Prompt.ask("\n[bold green]You[/bold green]")
        
        if request.lower() in ["exit", "quit", "q"]:
            console.print("[yellow]Goodbye![/yellow]")
            break
        
        if request.lower() == "help":
            console.print("\n[bold]Example requests:[/bold]")
            console.print("  • Schedule a team meeting next Tuesday at 2pm")
            console.print("  • Find time for a 1-on-1 with Sarah next week")
            console.print("  • What meetings do I have tomorrow?")
            console.print("  • Cancel my 3pm meeting on Friday")
            continue
        
        console.print("\n[yellow]Chronos is thinking...[/yellow]")
        
        try:
            result = await workflow.run(
                user_request=request,
                calendar_events=[],
            )
            
            console.print(f"\n[bold blue]Chronos:[/bold blue] {result.final_response}")
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


async def single_request(request: str):
    """Process a single request."""
    console.print(f"[yellow]Processing: {request}[/yellow]\n")
    
    workflow = create_workflow()
    await workflow.initialize()
    
    try:
        result = await workflow.run(
            user_request=request,
            calendar_events=[],
        )
        
        console.print(f"\n{result.final_response}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Chronos Scheduling Agent CLI")
    parser.add_argument(
        "--request",
        "-r",
        type=str,
        help="Single scheduling request"
    )
    
    args = parser.parse_args()
    
    if args.request:
        asyncio.run(single_request(args.request))
    else:
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()

