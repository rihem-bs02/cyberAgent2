"""
Neo4j Graph Database Integration
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable, AuthError
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

class AttackGraphDB:
    """Neo4j graph for attack path visualization"""
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASS", "password")
        self.driver = None
        self.connected = False
        self.nodes_created = 0
        self.relationships_created = 0
        
        if NEO4J_AVAILABLE:
            self._connect()
        else:
            logger.warning("Neo4j not available. pip install neo4j")
    
    def _connect(self):
        """Connect to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            self.driver.verify_connectivity()
            self.connected = True
            logger.success(f"Connected to Neo4j: {self.uri}")
            self._create_constraints()
        except ServiceUnavailable:
            logger.warning(f"Neo4j not available at {self.uri}")
        except AuthError:
            logger.warning(f"Neo4j auth failed for {self.user}")
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}")
    
    def _create_constraints(self):
        """Create constraints"""
        if not self.connected:
            return
        
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (h:Host) REQUIRE h.ip IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Vulnerability) REQUIRE v.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Finding) REQUIRE f.id IS UNIQUE",
        ]
        
        with self.driver.session() as session:
            for c in constraints:
                try:
                    session.run(c)
                except:
                    pass
    
    def add_host(self, ip: str, hostname: str = "", is_target: bool = False):
        """Add host"""
        if not self.connected:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (h:Host {ip: $ip})
                    SET h.hostname = $hostname,
                        h.is_target = $is_target,
                        h.last_seen = datetime()
                """, ip=ip, hostname=hostname, is_target=is_target)
                self.nodes_created += 1
        except Exception as e:
            logger.error(f"Failed to add host {ip}: {e}")
    
    def add_port(self, host_ip: str, port: int, service: str = ""):
        """Add port"""
        if not self.connected:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (h:Host {ip: $host_ip})
                    MERGE (p:Port {number: $port})
                    SET p.service = $service
                    MERGE (h)-[:HAS_PORT]->(p)
                """, host_ip=host_ip, port=port, service=service)
                self.relationships_created += 1
        except Exception as e:
            logger.error(f"Failed to add port: {e}")
    
    def add_service(self, host_ip: str, port: int, service_name: str):
        """Add service"""
        if not self.connected:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (h:Host {ip: $host_ip})
                    MATCH (p:Port {number: $port})
                    MERGE (s:Service {name: $service_name, host: $host_ip, port: $port})
                    MERGE (h)-[:RUNS_SERVICE]->(s)
                """, host_ip=host_ip, port=port, service_name=service_name)
                self.relationships_created += 1
        except Exception as e:
            logger.error(f"Failed to add service: {e}")
    
    def add_vulnerability(self, host_ip: str, vuln_id: str, name: str, severity: str, 
                          description: str = "", cve_id: str = "", cvss_score: float = 0.0):
        """Add vulnerability"""
        if not self.connected:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (h:Host {ip: $host_ip})
                    MERGE (v:Vulnerability {id: $vuln_id})
                    SET v.name = $name, v.severity = $severity,
                        v.description = $description, v.cve_id = $cve_id,
                        v.cvss_score = $cvss_score
                    MERGE (h)-[:HAS_VULNERABILITY]->(v)
                """, host_ip=host_ip, vuln_id=vuln_id, name=name,
                     severity=severity, description=description,
                     cve_id=cve_id, cvss_score=cvss_score)
                self.nodes_created += 1
                self.relationships_created += 1
        except Exception as e:
            logger.error(f"Failed to add vulnerability: {e}")
    
    def add_finding(self, finding):
        """Add finding"""
        if not self.connected:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    CREATE (f:Finding {
                        id: $id, title: $title, severity: $severity,
                        description: $description, technique_id: $technique_id,
                        timestamp: datetime($timestamp)
                    })
                    WITH f
                    MATCH (h:Host {ip: $host})
                    MERGE (f)-[:DISCOVERED_ON]->(h)
                """, id=finding.id, title=finding.title, severity=finding.severity,
                     description=finding.description, technique_id=finding.technique_id,
                     timestamp=finding.timestamp, host=finding.host)
                self.nodes_created += 1
        except Exception as e:
            logger.error(f"Failed to add finding: {e}")
    
    def add_tool_execution(self, tool_name: str, target: str, args: Dict, success: bool, execution_time: float):
        """Record tool execution"""
        if not self.connected:
            return
        
        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (t:Tool {name: $tool_name})
                    CREATE (e:Execution {
                        id: randomUUID(),
                        target: $target,
                        args: $args,
                        success: $success,
                        timestamp: datetime()
                    })
                    MERGE (t)-[:EXECUTED]->(e)
                """, tool_name=tool_name, target=target,
                     args=json.dumps(args)[:500], success=success)
        except Exception as e:
            logger.error(f"Failed to record execution: {e}")
    
    def get_attack_paths(self, target_ip: str) -> List[Dict]:
        """Get attack paths"""
        if not self.connected:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH path = (start:Host)-[:COMPROMISES*1..5]->(target:Host {ip: $ip})
                    RETURN path LIMIT 10
                """, ip=target_ip)
                
                paths = []
                for record in result:
                    paths.append({
                        "nodes": [dict(n) for n in record["path"].nodes],
                        "relationships": [dict(r) for r in record["path"].relationships]
                    })
                return paths
        except Exception as e:
            logger.error(f"Failed to get paths: {e}")
            return []
    
    def export_graph_for_visualization(self) -> Dict:
        """Export graph for visualization"""
        if not self.connected:
            return {"nodes": [], "links": []}
        
        try:
            with self.driver.session() as session:
                nodes_result = session.run("MATCH (n) RETURN n, labels(n) as labels")
                nodes = []
                for record in nodes_result:
                    node = dict(record["n"])
                    node_id = node.get("ip") or node.get("id") or node.get("name")
                    if node_id:
                        nodes.append({"id": node_id, "labels": record["labels"], "properties": node})
                
                links_result = session.run("MATCH (n)-[r]->(m) RETURN n, r, m, type(r) as t")
                links = []
                for record in links_result:
                    from_n = dict(record["n"])
                    to_n = dict(record["m"])
                    from_id = from_n.get("ip") or from_n.get("id") or from_n.get("name")
                    to_id = to_n.get("ip") or to_n.get("id") or to_n.get("name")
                    if from_id and to_id:
                        links.append({
                            "source": from_id,
                            "target": to_id,
                            "type": record["t"],
                            "properties": dict(record["r"])
                        })
                
                return {"nodes": nodes, "links": links}
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {"nodes": [], "links": []}
    
    def close(self):
        """Close connection"""
        if self.driver:
            self.driver.close()