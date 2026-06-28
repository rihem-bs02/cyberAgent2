"""
Utility functions
"""

import re
import os
from datetime import datetime

def safe_filename(filename: str) -> str:
    """Create safe filename"""
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)

def format_timestamp() -> str:
    """Get formatted timestamp"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def parse_ip(text: str) -> list:
    """Extract IP addresses from text"""
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    return list(set(re.findall(ip_pattern, text)))

def ensure_dir(path: str):
    """Ensure directory exists"""
    os.makedirs(path, exist_ok=True)