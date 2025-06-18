#!/usr/bin/env python3
"""
Simplified Memory Metrics Service
"""
import asyncio
import psutil
import logging
from typing import Dict, Any, Optional, Type

class SimplifiedMemoryService:
    _instance: Optional['SimplifiedMemoryService'] = None
    _lock: Optional[asyncio.Lock] = None

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @classmethod
    async def get_instance(cls: Type['SimplifiedMemoryService']) -> 'SimplifiedMemoryService':
        if cls._instance is None:
            if cls._lock is None:
                cls._lock = asyncio.Lock()
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def get_metrics(self) -> Dict[str, Any]:
        try:
            mem = psutil.virtual_memory()
            return {
                "total": mem.total,
                "available": mem.available,
                "percent": mem.percent,
                "used": mem.used,
                "free": mem.free
            }
        except Exception as e:
            self.logger.error(f"An error occurred while fetching memory metrics: {e}", exc_info=True)
            return {
                "error": "Failed to retrieve memory metrics",
                "details": str(e)
            }
