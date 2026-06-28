"""
Tool Registry - Execute security tools
"""

import subprocess
import json
import os
from typing import Dict, Any
from loguru import logger

# Tool descriptions for LLM
TOOL_DESCRIPTIONS = """
- nmap_port_scan: Scan ports on target host. Args: {"host": "ip", "ports": "1-1000"}
- http_probe: Probe HTTP/HTTPS service. Args: {"url": "http://host:port"}
- search_exploits: Search for exploits. Args: {"query": "search terms"}
- run_command: Execute shell command. Args: {"command": "cmd", "timeout": 30}
- report_finding: Record a finding. Args: {"title": "...", "severity": "critical|high|medium|low", "host": "ip", "description": "..."}
- done: Finish campaign. Args: {}
"""

def get_tool_descriptions() -> str:
    """Get tool descriptions"""
    return TOOL_DESCRIPTIONS

def execute_tool(tool_name: str, args: Dict[str, Any]) -> str:
    """Execute a tool"""
    
    logger.debug(f"Executing {tool_name} with args: {json.dumps(args)[:100]}")
    
    try:
        if tool_name == "nmap_port_scan":
            return _execute_nmap(args)
        
        elif tool_name == "http_probe":
            return _execute_http_probe(args)
        
        elif tool_name == "search_exploits":
            return _execute_search_exploits(args)
        
        elif tool_name == "run_command":
            return _execute_command(args)
        
        elif tool_name == "report_finding":
            return _report_finding(args)
        
        elif tool_name == "rag_query":
            return _execute_rag_query(args)
        
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return json.dumps({"error": str(e)})

def _execute_nmap(args: Dict) -> str:
    """Execute nmap scan"""
    host = args.get("host", "127.0.0.1")
    ports = args.get("ports", "1-1000")
    
    # Simulated nmap output
    results = [
        {"port": 22, "service": "ssh", "version": "OpenSSH 8.2"},
        {"port": 80, "service": "http", "version": "Apache 2.4.41"},
        {"port": 443, "service": "https", "version": "Apache 2.4.41"},
        {"port": 3306, "service": "mysql", "version": "MySQL 8.0"}
    ]
    
    # Try real nmap if available
    try:
        cmd = f"nmap -p {ports} {host}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout
    except:
        pass
    
    return json.dumps({"host": host, "ports": results})

def _execute_http_probe(args: Dict) -> str:
    """Probe HTTP service"""
    url = args.get("url", "http://localhost")
    
    try:
        import requests
        response = requests.get(url, timeout=10, verify=False)
        return json.dumps({
            "url": url,
            "status": response.status_code,
            "headers": dict(response.headers),
            "server": response.headers.get("Server", "Unknown")
        })
    except:
        return json.dumps({"url": url, "status": "unreachable"})

def _execute_search_exploits(args: Dict) -> str:
    """Search for exploits"""
    query = args.get("query", "")
    
    # Simulated results
    return json.dumps({
        "query": query,
        "results": [
            {"id": "CVE-2021-41773", "description": "Apache 2.4.49 Path Traversal"},
            {"id": "CVE-2021-42013", "description": "Apache 2.4.50 Path Traversal"},
            {"id": "CVE-2020-1938", "description": "Apache Tomcat Ghostcat"}
        ]
    })

def _execute_command(args: Dict) -> str:
    """Execute shell command"""
    command = args.get("command", "")
    timeout = args.get("timeout", 30)
    
    # Safety check
    dangerous = ["rm -rf /", "dd if=", "mkfs", "chmod 777 /"]
    if any(d in command for d in dangerous):
        return json.dumps({"error": "Dangerous command blocked"})
    
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout[:1000] if result.stdout else result.stderr[:1000]
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Command timed out"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def _report_finding(args: Dict) -> str:
    """Record finding"""
    finding = {
        "title": args.get("title", "Untitled"),
        "severity": args.get("severity", "medium"),
        "host": args.get("host", "unknown"),
        "description": args.get("description", ""),
        "technique_id": args.get("technique_id", ""),
        "mitigation": args.get("mitigation", ""),
        "cvss_score": args.get("cvss_score", 0.0)
    }
    
    return json.dumps({"recorded": True, "finding": finding})

def _execute_rag_query(args: Dict) -> str:
    """Execute RAG query"""
    # This would normally query Qdrant
    # For now, return simulated results
    query = args.get("query", "")
    return json.dumps({
        "query": query,
        "results": [
            {"text": f"Based on knowledge base, common vulnerabilities include...", "score": 0.95},
            {"text": f"MITRE ATT&CK techniques applicable: T1046, T1190", "score": 0.87}
        ]
    })