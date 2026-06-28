"""
Qdrant RAG Knowledge Base
"""

import os
import json
import hashlib
from typing import Dict, Any
from loguru import logger

class KnowledgeBase:
    """Qdrant RAG - Singleton pattern"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        from tools.tool_registry import execute_tool
        
        self.execute_tool = execute_tool
        self.qdrant_path = os.getenv("QDRANT_PATH", "./qdrant")
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        self.query_cache = {}
        self.query_count = 0
        self._initialized = True
        
        logger.info(f"Knowledge Base: Qdrant at {self.qdrant_host}:{self.qdrant_port}")
    
    def query(self, context: str, query_type: str = "general") -> Dict[str, Any]:
        """Query RAG"""
        cache_key = hashlib.md5(f"{context[:100]}:{query_type}".encode()).hexdigest()
        
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]
        
        try:
            results = self.execute_tool("rag_query", {
                "qdrant_path": self.qdrant_path,
                "query": context,
                "top_k": 3
            })
            
            if isinstance(results, str):
                try:
                    parsed = json.loads(results)
                except:
                    parsed = {"results": [{"text": results[:200]}]}
            else:
                parsed = results
            
            self.query_cache[cache_key] = parsed
            self.query_count += 1
            
            return parsed
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {"results": []}