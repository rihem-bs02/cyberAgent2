"""
Letta Memory Integration
"""

import os
import json
from typing import Dict, List, Optional
from loguru import logger

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

class LettaMemory:
    """Letta cross-campaign memory"""
    
    def __init__(self):
        self.base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
        self.agent_id = os.getenv("LETTA_AGENT_ID", "")
        self.token = os.getenv("LETTA_TOKEN", "")
        self.connected = False
        
        if REQUESTS_AVAILABLE:
            self._check_connection()
        else:
            logger.warning("Requests not available. pip install requests")
    
    def _check_connection(self):
        """Check Letta connection"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                self.connected = True
                logger.success(f"Connected to Letta: {self.base_url}")
            else:
                logger.warning(f"Letta returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"Letta not available: {e}")
    
    def create_campaign_context(self, campaign_id: str, target: str, objective: str):
        """Create campaign in memory"""
        if not self.connected:
            return
        
        try:
            payload = {
                "campaign_id": campaign_id,
                "target": target,
                "objective": objective,
                "timestamp": ""
            }
            requests.post(f"{self.base_url}/api/campaigns", json=payload, timeout=10)
        except Exception as e:
            logger.debug(f"Letta campaign creation failed: {e}")
    
    def store_action(self, campaign_id: str, step: int, tool: str, args: str, result: str):
        """Store action in memory"""
        if not self.connected:
            return
        
        try:
            payload = {
                "campaign_id": campaign_id,
                "step": step,
                "tool": tool,
                "args": args[:500],
                "result": result[:500]
            }
            requests.post(f"{self.base_url}/api/memories", json=payload, timeout=10)
        except Exception as e:
            logger.debug(f"Letta store failed: {e}")
    
    def get_recent_memories(self, campaign_id: str, limit: int = 5) -> List[Dict]:
        """Get recent memories"""
        if not self.connected:
            return []
        
        try:
            response = requests.get(
                f"{self.base_url}/api/campaigns/{campaign_id}/memories",
                params={"limit": limit},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Letta retrieval failed: {e}")
        
        return []
    
    def close(self):
        """Close (no-op for HTTP)"""
        pass