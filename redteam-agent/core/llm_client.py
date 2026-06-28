"""
LLM Client for Groq API
"""

import os
import json
from typing import Optional, Dict, Any
from loguru import logger

from groq import Groq

class LLMClient:
    """Groq LLM Client"""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.heavy_model = os.getenv("GROQ_MODEL_HEAVY", "llama-3.3-70b-versatile")
        self.fast_model = os.getenv("GROQ_MODEL_FAST", "qwen/qwen3-32b")
        
        if not self.api_key:
            logger.warning("GROQ_API_KEY not set!")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)
            logger.info(f"LLM Client initialized - Heavy: {self.heavy_model}, Fast: {self.fast_model}")
    
    def complete(self, system_prompt: str, user_prompt: str, 
                 max_tokens: int = 500, temperature: float = 0.1, 
                 json_mode: bool = False, use_heavy: bool = True) -> str:
        """Complete a chat completion"""
        
        if not self.client:
            return '{"thought": "LLM not configured", "tool": "done", "args": {}}'
        
        model = self.heavy_model if use_heavy else self.fast_model
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**kwargs)
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return '{"thought": "LLM error", "tool": "done", "args": {}}'