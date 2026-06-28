"""
Autonomous Red Team Agent with Graph + RAG + Memory
"""

import json
import os
import sys
import re
import time
import hashlib
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich import box

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.llm_client import LLMClient
from tools.tool_registry import execute_tool, get_tool_descriptions
from graph.neo4j_graph import AttackGraphDB
from knowledge.rag_knowledge import KnowledgeBase
from memory.letta_memory import LettaMemory

console = Console()

# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

# LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_HEAVY = os.getenv("GROQ_MODEL_HEAVY", "llama-3.3-70b-versatile")
GROQ_MODEL_FAST = os.getenv("GROQ_MODEL_FAST", "qwen/qwen3-32b")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "qwen")
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

# Qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant")

# Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password")

# Campaign
SAFE_MODE = os.getenv("SAFE_MODE", "true").lower() == "true"
STEALTH_LEVEL = os.getenv("STEALTH_LEVEL", "high")
MAX_THREADS = int(os.getenv("MAX_THREADS", "4"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REPORTS_DIR = os.getenv("REPORTS_DIR", "./reports")
TARGET_ENV = os.getenv("TARGET_ENV", "medflow")

# ============================================================
# CONSTANTS
# ============================================================

MAX_STEPS = 40
MAX_PARSE_FAILURES = 5
MAX_LOOP_DETECTION = 3
OBSERVATION_MAX_LENGTH = 800
RAG_QUERY_LIMIT = 3

# ============================================================
# DATA STRUCTURES
# ============================================================

class CampaignStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"

@dataclass
class Finding:
    id: str = field(default_factory=lambda: f"FIND-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    title: str = ""
    severity: str = "medium"
    host: str = ""
    port: int = 0
    service: str = ""
    description: str = ""
    technique_id: str = ""
    mitigation: str = ""
    cvss_score: float = 0.0
    evidence: str = ""
    cve_ids: List[str] = field(default_factory=list)
    affected_hosts: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    related_steps: List[int] = field(default_factory=list)

@dataclass
class AttackStep:
    step_number: int
    thought: str
    tool: str
    args: Dict[str, Any]
    observation: str
    success: bool
    target_host: str = ""
    target_port: int = 0
    execution_time: float = 0.0
    rag_context: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

# ============================================================
# AUTONOMOUS AGENT
# ============================================================

class AutonomousAgent:
    """Fully autonomous red team agent with Graph + RAG + Memory"""
    
    def __init__(self, use_graph: bool = True, use_rag: bool = True, use_memory: bool = True, safe_mode: bool = True):
        
        # Display config
        self._display_config()
        
        # Core components
        self.llm = LLMClient()
        self.kb = KnowledgeBase() if use_rag else None
        self.graph = AttackGraphDB() if use_graph else None
        self.memory = LettaMemory() if use_memory else None
        self.safe_mode = safe_mode
        
        # Campaign state
        self.target = ""
        self.objective = ""
        self.stealth = STEALTH_LEVEL
        self.campaign_id = ""
        self.status = CampaignStatus.RUNNING
        self.steps: List[AttackStep] = []
        self.findings: List[Finding] = []
        self.discovered_hosts: Set[str] = set()
        
        # Tracking
        self.tool_usage = defaultdict(int)
        self.error_count = 0
        self.parse_failures = 0
        self.rag_queries = 0
        self.start_time = 0
        
    def _display_config(self):
        """Display configuration"""
        console.print(Panel(
            f"[cyan]Target Environment:[/cyan] {TARGET_ENV}\n"
            f"[cyan]LLM Models:[/cyan] Heavy={GROQ_MODEL_HEAVY}, Fast={GROQ_MODEL_FAST}\n"
            f"[cyan]Safe Mode:[/cyan] {self.safe_mode}\n"
            f"[cyan]Stealth:[/cyan] {STEALTH_LEVEL}",
            title="[bold blue]Agent Configuration[/bold blue]"
        ))
    
    def run(self, target: str, objective: str = "", stealth: str = "high") -> dict:
        """Main execution method"""
        
        self.start_time = time.time()
        self.target = target
        self.objective = objective or f"Complete security assessment of {target}"
        self.stealth = stealth
        self.campaign_id = f"RT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Initialize graph
        if self.graph and self.graph.connected:
            self.graph.add_host(target, is_target=True)
        
        # Initialize memory
        if self.memory and self.memory.connected:
            self.memory.create_campaign_context(self.campaign_id, target, self.objective)
        
        # Display banner
        self._display_banner()
        
        # Build system prompt
        system_prompt = self._build_system_prompt()
        
        # Initialize history
        history = [{
            "role": "user",
            "content": f"Begin penetration test against {target}. Start with reconnaissance using nmap_port_scan."
        }]
        
        # Phase tracking
        phases = {
            1: ("🔍 RECONNAISSANCE", "cyan"),
            10: ("🎯 VULNERABILITY DISCOVERY", "yellow"),
            20: ("💥 EXPLOITATION", "red"),
            30: ("🔑 POST-EXPLOITATION", "magenta")
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Executing attack chain...", total=MAX_STEPS)
            
            for step_num in range(1, MAX_STEPS + 1):
                # Phase transitions
                for phase_num, (phase_name, phase_color) in phases.items():
                    if step_num == phase_num:
                        console.print(f"\n[bold {phase_color}]{phase_name} PHASE[/bold {phase_color}]")
                
                if self._should_terminate():
                    break
                
                try:
                    # Get RAG context
                    rag_context = self._get_rag_context(history)
                    
                    # Get memory context
                    memory_context = self._get_memory_context() if self.memory else ""
                    
                    # Build context
                    context = self._build_context(history, rag_context, memory_context)
                    
                    # Get LLM decision
                    raw_response = self.llm.complete(
                        system_prompt=system_prompt,
                        user_prompt=context,
                        max_tokens=500,
                        temperature=0.05,
                        json_mode=True
                    )
                    
                    # Parse response
                    parsed = self._parse_response(raw_response)
                    
                    if not parsed:
                        self._handle_parse_failure(raw_response, history)
                        continue
                    
                    thought = parsed.get("thought", "Continuing pentest")
                    tool_name = parsed.get("tool", "")
                    args = parsed.get("args", {})
                    
                    # Apply safe mode
                    if self.safe_mode:
                        args = self._apply_safe_mode(tool_name, args)
                    
                    # Extract target host
                    target_host = self._extract_host_from_args(args)
                    
                    # Validate
                    if not self._validate_tool_choice(tool_name, args, history):
                        continue
                    
                    # Display step
                    self._display_step(step_num, thought, tool_name, args)
                    
                    # Execute tool
                    execution_start = time.time()
                    
                    if tool_name == "done":
                        self.status = CampaignStatus.COMPLETED
                        console.print("[bold green]✅ Campaign completed![/bold green]")
                        break
                    
                    observation = execute_tool(tool_name, args)
                    execution_time = time.time() - execution_start
                    
                    success = self._determine_success(observation)
                    
                    # Update graph
                    if self.graph and self.graph.connected:
                        self._update_graph(tool_name, args, observation, success)
                    
                    # Update memory
                    if self.memory and self.memory.connected:
                        self.memory.store_action(
                            self.campaign_id, step_num, tool_name, 
                            json.dumps(args), observation[:500]
                        )
                    
                    # Process findings
                    if tool_name == "report_finding":
                        self._process_finding(observation, step_num)
                    
                    # Track
                    tool_key = f"{tool_name}:{json.dumps(args, sort_keys=True)[:60]}"
                    self.tool_usage[tool_key] += 1
                    self.rag_queries += 1
                    
                    # Discover new hosts
                    self._discover_hosts(observation)
                    
                    # Record step
                    step = AttackStep(
                        step_number=step_num,
                        thought=thought,
                        tool=tool_name,
                        args=args,
                        observation=observation[:OBSERVATION_MAX_LENGTH],
                        success=success,
                        target_host=target_host,
                        execution_time=execution_time,
                        rag_context=rag_context[:200] if rag_context else None
                    )
                    self.steps.append(step)
                    
                    # Display result
                    obs_short = observation[:200].replace('\n', ' ')
                    console.print(f"[bold green]📊 {obs_short}[/bold green]")
                    
                    # Update history
                    history = self._update_history(history, raw_response, observation, tool_name)
                    
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    logger.error(f"Step {step_num} failed: {e}")
                    logger.error(traceback.format_exc())
                    self.error_count += 1
                    
                    if self.error_count > 10:
                        break
        
        return self._generate_report()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt"""
        safe_note = "\nSAFE MODE: Only passive reconnaissance and scanning. No exploitation." if self.safe_mode else ""
        
        return f"""You are an autonomous penetration testing AI agent.
{safe_note}

TARGET: {self.target}
OBJECTIVE: {self.objective}
STEALTH: {self.stealth}

AVAILABLE TOOLS:
{get_tool_descriptions()}

RESPOND WITH ONLY JSON:
{{"thought": "reasoning", "tool": "tool_name", "args": {{"param": "value"}}}}

PHASES:
1. Reconnaissance: nmap_port_scan, http_probe
2. Vulnerability Discovery: search_exploits
3. Exploitation: run_command
4. Reporting: report_finding, done

Use real tool names only. No placeholders."""
    
    def _get_rag_context(self, history: List[Dict]) -> str:
        """Get RAG context"""
        if not self.kb:
            return ""
        
        try:
            recent = []
            for msg in history[-3:]:
                if msg["role"] == "user":
                    recent.append(msg["content"][:150])
            
            context = " ".join(recent) if recent else f"Pentest against {self.target}"
            results = self.kb.query(context)
            
            if results.get("results"):
                insights = [r.get("text", "")[:150] for r in results["results"][:2] if r.get("text")]
                return " | ".join(insights)
        except Exception as e:
            logger.debug(f"RAG query failed: {e}")
        
        return ""
    
    def _get_memory_context(self) -> str:
        """Get context from Letta memory"""
        if not self.memory or not self.memory.connected:
            return ""
        
        try:
            memories = self.memory.get_recent_memories(self.campaign_id, limit=3)
            if memories:
                return "Previous actions: " + " | ".join([m.get("summary", "")[:100] for m in memories])
        except Exception as e:
            logger.debug(f"Memory query failed: {e}")
        
        return ""
    
    def _build_context(self, history: List[Dict], rag_insights: str, memory_context: str) -> str:
        """Build context for LLM"""
        parts = []
        
        if rag_insights:
            parts.append(f"KNOWLEDGE BASE: {rag_insights}\n")
        
        if memory_context:
            parts.append(f"MEMORY: {memory_context}\n")
        
        parts.append(f"Progress: {len(self.steps)}/{MAX_STEPS} steps, {len(self.findings)} findings")
        parts.append(f"Hosts: {len(self.discovered_hosts)} discovered")
        
        for msg in history[-6:]:
            role = "Agent" if msg["role"] == "assistant" else "Result"
            parts.append(f"{role}: {msg['content'][:300]}")
        
        parts.append("Next action? JSON only.")
        
        return "\n\n".join(parts)
    
    def _parse_response(self, raw: str) -> Optional[Dict]:
        """Parse LLM response"""
        if not raw or not raw.strip():
            return None
        
        clean = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        
        # Strategy 1: Direct parse
        try:
            parsed = json.loads(clean)
            if isinstance(parsed, dict) and "tool" in parsed:
                return parsed
        except:
            pass
        
        # Strategy 2: Find JSON with tool key
        match = re.search(r'\{[^{}]*"tool"\s*:\s*"[^"]+"[^{}]*\}', clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        
        # Strategy 3: Extract tool name
        tool_match = re.search(r'"tool"\s*:\s*"([a-zA-Z_]+)"', raw)
        if tool_match:
            thought_match = re.search(r'"thought"\s*:\s*"([^"]{5,})"', raw)
            return {
                "thought": thought_match.group(1) if thought_match else "Continuing",
                "tool": tool_match.group(1),
                "args": {}
            }
        
        return None
    
    def _validate_tool_choice(self, tool_name: str, args: Dict, history: List[Dict]) -> bool:
        """Validate tool choice"""
        
        # Check placeholders
        if self._is_placeholder(tool_name):
            logger.warning(f"Placeholder: {tool_name}")
            history.append({
                "role": "user",
                "content": f"'{tool_name}' is placeholder. Use real tool name."
            })
            return False
        
        # Check loops
        tool_key = f"{tool_name}:{json.dumps(args, sort_keys=True)[:60]}"
        if self.tool_usage.get(tool_key, 0) >= MAX_LOOP_DETECTION:
            logger.warning(f"Loop: {tool_name}")
            history.append({
                "role": "user",
                "content": f"Used {tool_name} with same args {MAX_LOOP_DETECTION} times. Try different approach."
            })
            return False
        
        return True
    
    def _is_placeholder(self, text: str) -> bool:
        """Check for placeholder text"""
        if not text:
            return True
        
        placeholders = [
            "<", ">", "tool_name", "your reasoning", "choose", "placeholder",
            "analyze observation", "next tool action", "select tool", "decide"
        ]
        
        return any(p in text.lower() for p in placeholders)
    
    def _apply_safe_mode(self, tool_name: str, args: Dict) -> Dict:
        """Apply safe mode restrictions"""
        dangerous_tools = ["run_command", "exploit", "metasploit", "sqlmap"]
        
        if tool_name in dangerous_tools:
            logger.warning(f"Safe mode: Blocked {tool_name}")
            return {"blocked": True, "reason": "Safe mode enabled"}
        
        return args
    
    def _extract_host_from_args(self, args: Dict) -> str:
        """Extract target host from arguments"""
        host = args.get("host", args.get("url", self.target))
        if isinstance(host, str) and host.startswith("http"):
            host = host.split("//")[-1].split(":")[0].split("/")[0]
        return str(host)
    
    def _discover_hosts(self, observation: str):
        """Extract and add discovered hosts"""
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        hosts = set(re.findall(ip_pattern, observation))
        
        for host in hosts:
            if host not in self.discovered_hosts:
                self.discovered_hosts.add(host)
                if self.graph and self.graph.connected:
                    self.graph.add_host(host)
    
    def _update_graph(self, tool_name: str, args: Dict, observation: str, success: bool):
        """Update Neo4j graph"""
        host = self._extract_host_from_args(args)
        
        # Record tool execution
        self.graph.add_tool_execution(tool_name, host, args, success, 0)
        
        # Parse nmap output
        if tool_name == "nmap_port_scan":
            port_pattern = r'(\d+)/tcp\s+open\s+(\S+)'
            for port, service in re.findall(port_pattern, observation):
                self.graph.add_port(host, int(port), service=service)
                self.graph.add_service(host, int(port), service)
    
    def _process_finding(self, observation: str, step_num: int):
        """Process finding"""
        try:
            result = json.loads(observation) if isinstance(observation, str) else observation
            
            if result.get("recorded"):
                finding_data = result.get("finding", {})
                
                finding = Finding(
                    id=f"FIND-{self.campaign_id}-{len(self.findings)+1:03d}",
                    title=finding_data.get("title", "Untitled"),
                    severity=finding_data.get("severity", "medium"),
                    host=finding_data.get("host", self.target),
                    description=finding_data.get("description", ""),
                    technique_id=finding_data.get("technique_id", ""),
                    related_steps=[step_num]
                )
                
                self.findings.append(finding)
                
                # Add to graph
                if self.graph and self.graph.connected:
                    self.graph.add_finding(finding)
                
                # Display
                self._display_finding(finding)
                
        except Exception as e:
            logger.error(f"Failed to process finding: {e}")
    
    def _display_finding(self, finding: Finding):
        """Display finding"""
        sev_colors = {
            "critical": "bold red",
            "high": "red",
            "medium": "yellow",
            "low": "dim"
        }
        color = sev_colors.get(finding.severity, "white")
        
        console.print(Panel(
            f"[{color}]🔴 {finding.title}[/{color}]\n"
            f"Severity: [{color}]{finding.severity.upper()}[/{color}]\n"
            f"Host: {finding.host}",
            title="[bold red]FINDING[/bold red]",
            border_style="red" if finding.severity in ["critical", "high"] else "yellow"
        ))
    
    def _should_terminate(self) -> bool:
        """Check termination"""
        if self.status == CampaignStatus.COMPLETED:
            return True
        if self.error_count > 10:
            logger.error("Too many errors")
            self.status = CampaignStatus.FAILED
            return True
        if self.parse_failures > MAX_PARSE_FAILURES:
            logger.error("Too many parse failures")
            self.status = CampaignStatus.FAILED
            return True
        return False
    
    def _display_banner(self):
        """Display campaign banner"""
        graph_status = "✅" if (self.graph and self.graph.connected) else "❌"
        rag_status = "✅" if self.kb else "❌"
        memory_status = "✅" if (self.memory and self.memory.connected) else "❌"
        
        console.print(Panel(
            f"[bold red]⚡ AUTONOMOUS RED TEAM AGENT ⚡[/bold red]\n\n"
            f"[cyan]Target:[/cyan] {self.target}\n"
            f"[cyan]Campaign:[/cyan] {self.campaign_id}\n"
            f"[cyan]Stealth:[/cyan] {self.stealth.upper()}\n"
            f"[cyan]Safe Mode:[/cyan] {self.safe_mode}\n"
            f"[green]Graph (Neo4j):[/green] {graph_status}\n"
            f"[green]RAG (Qdrant):[/green] {rag_status}\n"
            f"[green]Memory (Letta):[/green] {memory_status}",
            title="[bold red]🔴 OPERATION STARTED 🔴[/bold red]",
            border_style="red"
        ))
    
    def _display_step(self, step_num: int, thought: str, tool: str, args: Dict):
        """Display step"""
        console.print(f"\n[dim]━━━ Step {step_num}/{MAX_STEPS} ━━━[/dim]")
        console.print(f"[bold cyan]💭 {thought[:150]}[/bold cyan]")
        console.print(f"[bold yellow]🔧 {tool}[/bold yellow] {json.dumps(args)[:80]}")
    
    def _update_history(self, history: List[Dict], response: str, observation: str, tool: str) -> List[Dict]:
        """Update history"""
        history.append({"role": "assistant", "content": response[:500]})
        history.append({
            "role": "user",
            "content": f"Result from {tool}:\n{observation[:500]}\n\nNext action? JSON only."
        })
        
        if len(history) > 16:
            history = [history[0]] + history[-14:]
        
        return history
    
    def _handle_parse_failure(self, raw: str, history: List[Dict]):
        """Handle parse failures"""
        self.parse_failures += 1
        logger.warning(f"Parse failure {self.parse_failures}/{MAX_PARSE_FAILURES}")
        
        if self.parse_failures >= MAX_PARSE_FAILURES:
            history.clear()
            history.append({
                "role": "user",
                "content": f'Respond with JSON only: {{"thought": "I will scan", "tool": "nmap_port_scan", "args": {{"host": "{self.target}"}}}}'
            })
            self.parse_failures = 0
    
    def _determine_success(self, observation: str) -> bool:
        """Check if tool succeeded"""
        if not observation:
            return False
        failure_kw = ["error", "failed", "timeout", "refused", "permission denied"]
        return not any(kw in observation.lower() for kw in failure_kw)
    
    def _generate_report(self) -> dict:
        """Generate report"""
        duration = time.time() - self.start_time
        
        # Get graph data
        graph_data = {}
        if self.graph and self.graph.connected:
            graph_data = {
                "attack_paths": self.graph.get_attack_paths(self.target),
                "visualization": self.graph.export_graph_for_visualization()
            }
        
        report = {
            "campaign_id": self.campaign_id,
            "target": self.target,
            "objective": self.objective,
            "duration_seconds": duration,
            "status": self.status.value,
            "statistics": {
                "total_steps": len(self.steps),
                "successful_steps": sum(1 for s in self.steps if s.success),
                "findings_count": len(self.findings),
                "critical_findings": sum(1 for f in self.findings if f.severity == "critical"),
                "high_findings": sum(1 for f in self.findings if f.severity == "high"),
                "hosts_discovered": len(self.discovered_hosts),
                "graph_nodes": self.graph.nodes_created if self.graph else 0,
                "graph_relationships": self.graph.relationships_created if self.graph else 0,
                "rag_queries": self.rag_queries,
                "errors": self.error_count
            },
            "findings": [asdict(f) for f in self.findings],
            "attack_timeline": [
                {
                    "step": s.step_number,
                    "tool": s.tool,
                    "host": s.target_host,
                    "success": s.success,
                    "execution_time": s.execution_time
                }
                for s in self.steps
            ],
            "graph_data": graph_data
        }
        
        # Save
        os.makedirs(REPORTS_DIR, exist_ok=True)
        report_path = f"{REPORTS_DIR}/{self.campaign_id}_report.json"
        
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save graph separately
        if graph_data.get("visualization"):
            graph_path = f"{REPORTS_DIR}/{self.campaign_id}_graph.json"
            with open(graph_path, "w") as f:
                json.dump(graph_data["visualization"], f, indent=2)
        
        # Display summary
        self._display_summary(report)
        
        return report
    
    def _display_summary(self, report: dict):
        """Display summary"""
        table = Table(title=f"🎯 Summary - {self.campaign_id}", box=box.HEAVY)
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", style="bold", width=50)
        
        stats = report["statistics"]
        
        table.add_row("Status", f"[green]{self.status.value.upper()}[/green]")
        table.add_row("Duration", f"{report['duration_seconds']:.2f}s")
        table.add_row("Steps", str(stats["total_steps"]))
        table.add_row("Findings", str(stats["findings_count"]))
        table.add_row("Critical", f"[bold red]{stats['critical_findings']}[/bold red]")
        table.add_row("High", f"[red]{stats['high_findings']}[/red]")
        table.add_row("Graph Nodes", str(stats["graph_nodes"]))
        table.add_row("Graph Edges", str(stats["graph_relationships"]))
        table.add_row("Report", f"{REPORTS_DIR}/{self.campaign_id}_report.json")
        
        console.print("\n")
        console.print(table)
        
        if self.findings:
            tree = Tree("[bold red]🔍 Findings[/bold red]")
            for f in self.findings:
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(f.severity, "⚪")
                tree.add(f"{icon} [{f.severity.upper()}] {f.title}")
            console.print(tree)
    
    def cleanup(self):
        """Cleanup"""
        if self.graph:
            self.graph.close()
        if self.memory:
            self.memory.close()
        logger.info("Agent cleanup complete")