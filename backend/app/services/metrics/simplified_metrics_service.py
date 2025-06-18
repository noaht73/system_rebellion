#!/usr/bin/env python3
"""
Simplified Metrics Service

A direct, no-nonsense metrics service that combines all individual metrics services
and provides a unified interface for the WebSocket route. No complex layers, no caching
issues, just pure data.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Type

from app.core.resilience import WebSocketCircuitBreaker, get_circuit_breaker
from app.services.metrics.simplified_cpu_service import SimplifiedCPUService
from app.services.metrics.simplified_disk_service import SimplifiedDiskService
from app.services.metrics.simplified_memory_service import SimplifiedMemoryService
from app.services.metrics.simplified_network_service import SimplifiedNetworkService


class SimplifiedMetricsService:
    """
    Simplified metrics service that combines all individual metrics services.
    No complex layers or transformations, just real data.
    """

    _instance: Optional['SimplifiedMetricsService'] = None
    _lock: Optional[asyncio.Lock] = None

    def __init__(self):
        """Initializes the service and its dependencies, like circuit breakers."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Initialize circuit breakers for each sub-service
        self.cpu_circuit_breaker = get_circuit_breaker("cpu_service", max_failures=3, reset_timeout=30)
        self.memory_circuit_breaker = get_circuit_breaker("memory_service", max_failures=3, reset_timeout=30)
        self.disk_circuit_breaker = get_circuit_breaker("disk_service", max_failures=3, reset_timeout=30)
        self.network_circuit_breaker = get_circuit_breaker("network_service", max_failures=3, reset_timeout=30)

        self.logger.info("SimplifiedMetricsService initialized with circuit breakers.")

    @classmethod
    async def get_instance(cls: Type['SimplifiedMetricsService']) -> 'SimplifiedMetricsService':
        """
        Asynchronous singleton instance getter. Initialization is now handled in __init__.
        """
        if cls._instance is None:
            lock = await cls._get_lock()
            async with lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    async def _get_lock(cls):
        """Get or create the async lock"""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    async def _safe_get_metrics(self, service: Any, circuit_breaker: WebSocketCircuitBreaker, service_name: str) -> Dict[str, Any]:
        """
        Safely get metrics from a service with circuit breaker protection.

        Args:
            service: The metrics service to call.
            circuit_breaker: The circuit breaker for this service.
            service_name: Name of the service for logging.

        Returns:
            A dictionary with metrics data on success, or a dictionary
            containing an 'error' key on failure.
        """
        if not circuit_breaker.can_attempt_connection():
            self.logger.warning(f"{service_name} circuit breaker is open, skipping metrics collection.")
            return {'error': f"{service_name} circuit breaker is open"}

        try:
            metrics = await service.get_metrics()
            circuit_breaker.record_success()
            return metrics
        except Exception as e:
            circuit_breaker.record_failure()
            self.logger.error(f"Error collecting {service_name} metrics: {str(e)}", exc_info=False) # Keep logs clean
            return {'error': str(e)}

    async def get_cpu_metrics(self, force_refresh=False) -> Dict[str, Any]:
        """Get CPU metrics only. Returns the raw result from _safe_get_metrics."""
        cpu_service = await SimplifiedCPUService.get_instance()
        return await self._safe_get_metrics(cpu_service, self.cpu_circuit_breaker, "CPU")

    async def get_memory_metrics(self, force_refresh=False) -> Dict[str, Any]:
        """Get memory metrics only. Returns the raw result from _safe_get_metrics."""
        memory_service = await SimplifiedMemoryService.get_instance()
        return await self._safe_get_metrics(memory_service, self.memory_circuit_breaker, "Memory")

    async def get_disk_metrics(self, force_refresh=False) -> Dict[str, Any]:
        """Get disk metrics only. Returns the raw result from _safe_get_metrics."""
        disk_service = await SimplifiedDiskService.get_instance()
        return await self._safe_get_metrics(disk_service, self.disk_circuit_breaker, "Disk")

    async def get_network_metrics(self, force_refresh=False) -> Dict[str, Any]:
        """Get network metrics only. Returns the raw result from _safe_get_metrics."""
        network_service = await SimplifiedNetworkService.get_instance()
        return await self._safe_get_metrics(network_service, self.network_circuit_breaker, "Network")

    async def get_metrics(self, force_refresh=False) -> Dict[str, Any]:
        """
        Get comprehensive system metrics from all services. This function is designed to be
        resilient, returning a well-formed payload even if some sub-services fail.

        Args:
            force_refresh: Ignored in this implementation (no caching)

        Returns:
        A dictionary containing all system metrics, with clear error reporting.
        """
        try:
            # Create tasks for concurrent execution
            tasks = [
                self.get_cpu_metrics(force_refresh),
                self.get_memory_metrics(force_refresh),
                self.get_disk_metrics(force_refresh),
                self.get_network_metrics(force_refresh)
            ]

            # Wait for all metrics to be collected
            cpu_data, memory_data, disk_data, network_data = await asyncio.gather(*tasks)

            # Define default structures for graceful failure
            default_cpu = {'usage_percent': 0, 'top_processes': [], 'physical_cores': 0, 'logical_cores': 0}
            default_memory = {'percent': 0, 'total': 0}
            default_disk = {'percent': 0, 'total': 0}
            default_network = {'sent_rate': 0, 'recv_rate': 0, 'interfaces': []}

            # Process results, handling errors gracefully
            errors = {}

            if 'error' in cpu_data:
                errors['cpu'] = cpu_data['error']
                cpu_data = default_cpu

            if 'error' in memory_data:
                errors['memory'] = memory_data['error']
                memory_data = default_memory

            if 'error' in disk_data:
                errors['disk'] = disk_data['error']
                disk_data = default_disk

            if 'error' in network_data:
                errors['network'] = network_data['error']
                network_data = default_network

            # Combine all metrics into a single, well-structured response
            # This structure is guaranteed to be consistent, with no 'None' values
            # at the top level, which simplifies frontend handling.
            payload = {
                'timestamp': datetime.now().isoformat(),
                'has_errors': bool(errors),
                'errors': errors,
                'cpu_usage': cpu_data.get('usage_percent', 0),
                'memory_usage': memory_data.get('percent', 0),
                'disk_usage': disk_data.get('percent', 0),
                'network_sent_rate': network_data.get('sent_rate', 0),
                'network_recv_rate': network_data.get('recv_rate', 0),
                'cpu': cpu_data,
                'memory': memory_data,
                'disk': disk_data,
                'network': network_data,
                'process_count': len(cpu_data.get('top_processes', [])),
                'system_info': {
                    'hostname': 'N/A', # This info is not consistently available
                    'physical_cores': cpu_data.get('physical_cores', 0),
                    'logical_cores': cpu_data.get('logical_cores', 0),
                    'total_memory': memory_data.get('total', 0),
                    'total_disk': disk_data.get('total', 0)
                }
            }
            return payload

        except Exception as e:
            self.logger.critical(f"A critical, unhandled error occurred in get_metrics: {str(e)}", exc_info=True)
            # Return a failsafe error structure that won't crash the frontend
            return {
                'timestamp': datetime.now().isoformat(),
                'has_errors': True,
                'errors': {'critical': f"A critical error occurred in the metrics service: {str(e)}"},
                'cpu_usage': 0, 'memory_usage': 0, 'disk_usage': 0,
                'network_sent_rate': 0, 'network_recv_rate': 0,
                'cpu': {}, 'memory': {}, 'disk': {}, 'network': {},
                'process_count': 0, 'system_info': {}
            }


# Test function to run the service directly
async def test_simplified_metrics_service():
    """Test the simplified metrics service"""
    print("\n" + "="*60)
    print(" SIMPLIFIED METRICS SERVICE TEST")
    print("="*60)

    # Get timestamp
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize service
    service = await SimplifiedMetricsService.get_instance()
    print(f"Service instance: {service}")

    # Get metrics
    metrics = await service.get_metrics()
    print("\nSystem Metrics Overview:")
    print(f"CPU Usage: {metrics['cpu_usage']}%")
    print(f"Memory Usage: {metrics['memory_usage']}%")
    print(f"Disk Usage: {metrics['disk_usage']}%")
    print(f"Network Send Rate: {metrics['network_sent_rate'] / 1024:.2f} KB/s")
    print(f"Network Receive Rate: {metrics['network_recv_rate'] / 1024:.2f} KB/s")
    print(f"Process Count: {metrics['process_count']}")

    print("\nSystem Info:")
    for key, value in metrics['system_info'].items():
        if key in ['total_memory', 'total_disk']:
            print(f"  {key}: {value / (1024 * 1024 * 1024):.2f} GB")
        else:
            print(f"  {key}: {value}")

    print("\nDetailed Metrics Available:")
    print(f"CPU: {len(metrics['cpu'])} metrics")
    print(f"Memory: {len(metrics['memory'])} metrics")
    print(f"Disk: {len(metrics['disk'])} metrics")
    print(f"Network: {len(metrics['network'])} metrics")

    print("\n" + "="*60)


async def initialize_metrics_service():
    """Forces the initialization of the metrics service singleton."""
    await SimplifiedMetricsService.get_instance()

if __name__ == "__main__":
    asyncio.run(test_simplified_metrics_service())
