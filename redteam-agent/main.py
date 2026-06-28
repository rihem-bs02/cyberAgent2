#!/usr/bin/env python3
"""
Red Team Autonomous Agent - Main Entry Point
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from loguru import logger

from agents.autonomous_agent import AutonomousAgent

console = Console()

def setup_logging():
    """Configure logging"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    reports_dir = os.getenv("REPORTS_DIR", "./reports")
    
    # Ensure directories exist
    os.makedirs("logs", exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    
    # Remove default logger
    logger.remove()
    
    # Console logger
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level
    )
    
    # File logger
    logger.add(
        f"logs/agent_{datetime.now().strftime('%Y%m%d')}.log",
        rotation="100 MB",
        retention="30 days",
        level="DEBUG"
    )

def display_header():
    """Display startup header"""
    console.print(Panel(
        f"""[bold red]╔══════════════════════════════════════════════╗
║     AUTONOMOUS RED TEAM AGENT v3.0          ║
║     Neo4j Graph + Qdrant RAG + Letta       ║
╚══════════════════════════════════════════════╝[/bold red]

[cyan]Configuration:[/cyan]
  LLM Provider:  Groq
  Heavy Model:   {os.getenv('GROQ_MODEL_HEAVY', 'N/A')}
  Fast Model:    {os.getenv('GROQ_MODEL_FAST', 'N/A')}
  RAG Database:  Qdrant ({os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '6333')})
  Graph DB:      Neo4j ({os.getenv('NEO4J_URI', 'bolt://localhost:7687')})
  Memory:        Letta ({os.getenv('LETTA_BASE_URL', 'N/A')})
  Safe Mode:     {os.getenv('SAFE_MODE', 'true')}
  Stealth:       {os.getenv('STEALTH_LEVEL', 'high')}
  Target Env:    {os.getenv('TARGET_ENV', 'generic')}""",
        title="[bold green]🚀 INITIALIZATION[/bold green]",
        border_style="green"
    ))

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Autonomous Red Team Agent with Graph and RAG capabilities"
    )
    
    parser.add_argument(
        "target",
        help="Target IP address or hostname"
    )
    
    parser.add_argument(
        "-o", "--objective",
        default="",
        help="Penetration testing objective"
    )
    
    parser.add_argument(
        "-s", "--stealth",
        choices=["low", "medium", "high"],
        default=os.getenv("STEALTH_LEVEL", "high"),
        help="Stealth level (default: from .env or high)"
    )
    
    parser.add_argument(
        "--no-graph",
        action="store_true",
        help="Disable Neo4j graph integration"
    )
    
    parser.add_argument(
        "--no-rag",
        action="store_true",
        help="Disable RAG knowledge base"
    )
    
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        default=os.getenv("SAFE_MODE", "true").lower() == "true",
        help="Enable safe mode (no destructive actions)"
    )
    
    return parser.parse_args()

def main():
    """Main execution function"""
    
    # Setup
    setup_logging()
    display_header()
    
    # Parse arguments
    args = parse_args()
    
    logger.info(f"Starting campaign against: {args.target}")
    logger.info(f"Objective: {args.objective or 'Auto-generated'}")
    logger.info(f"Stealth: {args.stealth}")
    logger.info(f"Safe Mode: {args.safe_mode}")
    
    # Initialize agent
    try:
        agent = AutonomousAgent(
            use_graph=not args.no_graph,
            use_rag=not args.no_rag,
            safe_mode=args.safe_mode
        )
        
        # Run campaign
        report = agent.run(
            target=args.target,
            objective=args.objective,
            stealth=args.stealth
        )
        
        # Display results
        display_results(report)
        
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Campaign interrupted by user[/bold yellow]")
        logger.warning("Campaign interrupted by user")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Fatal error: {e}[/bold red]")
        logger.error(f"Fatal error: {e}")
        logger.exception("Detailed traceback:")
        
    finally:
        if 'agent' in locals():
            agent.cleanup()
        
        console.print("\n[bold green]✅ Agent shutdown complete[/bold green]")

def display_results(report: dict):
    """Display campaign results"""
    
    if not report:
        return
    
    console.print("\n")
    
    # Summary table
    table = Table(
        title=f"🎯 Campaign Results - {report.get('campaign_id', 'N/A')}",
        box=box.HEAVY,
        show_lines=True
    )
    
    table.add_column("Metric", style="cyan", width=30)
    table.add_column("Value", style="bold", width=50)
    
    stats = report.get("statistics", {})
    
    table.add_row("Status", f"[green]{report.get('status', 'unknown').upper()}[/green]")
    table.add_row("Duration", f"{report.get('duration_seconds', 0):.2f}s")
    table.add_row("Total Steps", str(stats.get("total_steps", 0)))
    table.add_row("Successful Steps", str(stats.get("successful_steps", 0)))
    table.add_row("Findings", str(stats.get("findings_count", 0)))
    table.add_row("Critical", f"[bold red]{stats.get('critical_findings', 0)}[/bold red]")
    table.add_row("High", f"[red]{stats.get('high_findings', 0)}[/red]")
    table.add_row("Hosts Discovered", str(stats.get("hosts_discovered", 0)))
    table.add_row("Graph Nodes", str(stats.get("graph_nodes", 0)))
    table.add_row("Graph Relationships", str(stats.get("graph_relationships", 0)))
    table.add_row("RAG Queries", str(stats.get("rag_queries", 0)))
    table.add_row("Report Location", f"reports/{report.get('campaign_id', 'N/A')}_report.json")
    
    console.print(table)
    
    # Display findings
    findings = report.get("findings", [])
    if findings:
        console.print("\n[bold red]🔍 KEY FINDINGS:[/bold red]")
        for finding in findings[:5]:
            severity_color = {
                "critical": "bold red",
                "high": "red",
                "medium": "yellow",
                "low": "dim"
            }.get(finding.get("severity", ""), "white")
            
            console.print(f"  [{severity_color}]● {finding.get('title', 'Unknown')}[/{severity_color}]")

if __name__ == "__main__":
    main()