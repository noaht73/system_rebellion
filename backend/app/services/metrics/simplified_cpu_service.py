#!/usr/bin/env python3
"""
Simplified CPU Metrics Service

A direct, no-nonsense service for fetching detailed CPU metrics.
"""
import asyncio
import psutil
import logging
from typing import Dict, Any, List, Optional, Type

class SimplifiedCPUService:
    """
    Provides detailed CPU metrics using psutil.
    """
    _instance: Optional['SimplifiedCPUService'] = None
    _lock: Optional[asyncio.Lock] = None

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Set a non-blocking interval for CPU usage calculation
        psutil.cpu_percent(interval=None)

    @classmethod
    async def get_instance(cls: Type['SimplifiedCPUService']) -> 'SimplifiedCPUService':
        """
        Asynchronous singleton instance getter.
        """
        if cls._instance is None:
            if cls._lock is None:
                cls._lock = asyncio.Lock()
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def get_top_processes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Gets a list of the top CPU-consuming processes.
        """
        processes = []
        try:
            # Sort processes by CPU usage
            sorted_procs = sorted(psutil.process_iter(['pid', 'name', 'username', 'cpu_percent']),
                                  key=lambda p: p.info['cpu_percent'],
                                  reverse=True)
            for proc in sorted_procs[:limit]:
                try:
                    # proc.info is already populated by the iterator
                    p_info = proc.info
                    processes.append({
                        'pid': p_info['pid'],
                        'name': p_info['name'],
                        'username': p_info['username'],
                        'cpu_percent': round(p_info['cpu_percent'], 2)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process might have terminated or access is denied
                    continue
        except Exception as e:
            self.logger.error(f"Could not retrieve top processes: {e}", exc_info=False)
        return processes

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Asynchronously fetches all relevant CPU metrics.
        """
        try:
            # Get CPU usage over a short interval to get a meaningful reading
            usage_percent = psutil.cpu_percent(interval=0.1)

            top_processes = await self.get_top_processes()

            return {
                "usage_percent": usage_percent,
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "top_processes": top_processes
            }
        except Exception as e:
            self.logger.error(f"An error occurred while fetching CPU metrics: {e}", exc_info=True)
            # Return a default error structure
            return {
                "error": "Failed to retrieve CPU metrics",
                "details": str(e)
            }
