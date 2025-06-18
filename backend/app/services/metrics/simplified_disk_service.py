#!/usr/bin/env python3
"""
Simplified Disk Metrics Service
"""
import asyncio
import psutil
import logging
from typing import Dict, Any, Optional, Type

class SimplifiedDiskService:
    _instance: Optional['SimplifiedDiskService'] = None
    _lock: Optional[asyncio.Lock] = None

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @classmethod
    async def get_instance(cls: Type['SimplifiedDiskService']) -> 'SimplifiedDiskService':
        if cls._instance is None:
            if cls._lock is None:
                cls._lock = asyncio.Lock()
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def get_metrics(self) -> Dict[str, Any]:
        try:
            usage = psutil.disk_usage('/')
            return {
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent
            }
        except Exception as e:
            self.logger.error(f"An error occurred while fetching disk metrics: {e}", exc_info=True)
            return {
                "error": "Failed to retrieve disk metrics",
                "details": str(e)
            }
