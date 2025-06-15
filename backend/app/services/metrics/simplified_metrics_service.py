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
from typing import Dict, Any, Optional


from app.core.resilience import get_circuit_breaker, reset_circuit_breaker

from app.services.metrics.simplified_cpu_service import SimplifiedCPUService
from app.services.metrics.simplified_memory_service import SimplifiedMemoryService
from app.services.metrics.simplified_disk_service import SimplifiedDiskService
from app.services.metrics.simplified_network_service import SimplifiedNetworkService


class SimplifiedMetricsService:
    """
    Simplified metrics service that combines all individual metrics services.
    No complex layers or transformations, just real data.
    """
    
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimplifiedMetricsService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.logger = logging.getLogger('SimplifiedMetricsService')
        self._initialized = True
        
        self.cpu_circuit_breaker = get_circuit_breaker(
        name="simplified_cpu_metrics", 
        max_failures=3,
        reset_timeout=15,
        exponential_backoff_factor=1.5
    )
    
        self.memory_circuit_breaker = get_circuit_breaker(
        name="simplified_memory_metrics", 
        max_failures=3,
        reset_timeout=15,
        exponential_backoff_factor=1.5
    )
    
        self.disk_circuit_breaker = get_circuit_breaker(
        name="simplified_disk_metrics", 
        max_failures=3,
        reset_timeout=15,
        exponential_backoff_factor=1.5
    )
    
        self.network_circuit_breaker = get_circuit_breaker(
        name="simplified_network_metrics", 
        max_failures=3,
        reset_timeout=15,
        exponential_backoff_factor=1.5
    )
    
        self.logger.info("SimplifiedMetricsService initialized as singleton with circuit breakers")
    
    @classmethod
    async def get_instance(cls):
        """Get the singleton instance of the service"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def _get_lock(self):
        """Get or create the async lock"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
    
    async def _safe_get_metrics(self, service, circuit_breaker, service_name):
        """
        Safely get metrics from a service with circuit breaker protection
        
        Args:
            service: The metrics service to call
            circuit_breaker: The circuit breaker for this service
            service_name: Name of the service for logging
        
            Returns:
            Dictionary with metrics data or empty dict on error
        """
        # Check if circuit breaker allows the call
        if not circuit_breaker.can_attempt_connection():
            self.logger.warning(f"{service_name} circuit breaker is open, skipping metrics collection")
            return {'data': {}, 'error': f"{service_name} circuit breaker open"}
    
        try:
            metrics = await service.get_metrics()
            # Record success in circuit breaker
            circuit_breaker.record_success()
            return metrics
        except Exception as e:
            # Record failure in circuit breaker
            circuit_breaker.record_failure()
            self.logger.error(f"Error collecting {service_name} metrics: {str(e)}")
            return {'data': {}, 'error': str(e)}
        
    async def get_cpu_metrics(self, force_refresh=False) -> Dict[str, Any]:
        """Get CPU metrics only"""
        cpu_service = await SimplifiedCPUService.get_instance()
        result = await self._safe_get_metrics(cpu_service, self.cpu_circuit_breaker, "CPU")
        return result.get('data', {})

    async def get_memory_metrics(self, force_refresh=False) -> Dict[str, Any]:
        """Get memory metrics only"""
        memory_service = await SimplifiedMemoryService.get_instance()
        result = await self._safe_get_metrics(memory_service, self.memory_circuit_breaker, "Memory")
        return result.get('data', {})

    async def get_disk_metrics(self, force_refresh=False) -> Dict[str, Any]:
        """Get disk metrics only"""
        disk_service = await SimplifiedDiskService.get_instance()
        result = await self._safe_get_metrics(disk_service, self.disk_circuit_breaker, "Disk")
        return result.get('data', {})

    async def get_network_metrics(self, force_refresh=False) -> Dict[str, Any]:
        """Get network metrics only"""
        network_service = await SimplifiedNetworkService.get_instance()
        result = await self._safe_get_metrics(network_service, self.network_circuit_breaker, "Network")
        return result.get('data', {})
        
    async def get_metrics(self, force_refresh=False) -> Dict[str, Any]:
        """
        Get comprehensive system metrics from all services.
        
        Args:
            force_refresh: Ignored in this implementation (no caching)
        
        Returns:
        Dictionary containing all system metrics
        """
        try:
            # Create tasks for concurrent execution
            cpu_task = asyncio.create_task(self.get_cpu_metrics(force_refresh))
            memory_task = asyncio.create_task(self.get_memory_metrics(force_refresh))
            disk_task = asyncio.create_task(self.get_disk_metrics(force_refresh))
            network_task = asyncio.create_task(self.get_network_metrics(force_refresh))
            
            # Wait for all metrics to be collected
            cpu_data, memory_data, disk_data, network_data = await asyncio.gather(
                cpu_task, memory_task, disk_task, network_task
            )
            
            # No need to extract data, as our get_*_metrics methods already return the data directly
            # Track if we have any errors
            errors = {}
            
            # Check for errors in each metrics result
            if isinstance(cpu_data, dict) and 'error' in cpu_data:
                errors['cpu'] = cpu_data['error']
            if isinstance(memory_data, dict) and 'error' in memory_data:
                errors['memory'] = memory_data['error']
            if isinstance(disk_data, dict) and 'error' in disk_data:
                errors['disk'] = disk_data['error']
            if isinstance(network_data, dict) and 'error' in network_data:
                errors['network'] = network_data['error']
                
            # Determine if we have any errors
            has_errors = len(errors) > 0
            
            # Combine all metrics into a single response
            result = {
                'timestamp': datetime.now().isoformat(),
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
                    'hostname': network_data.get('interfaces', [{}])[0].get('name', 'unknown') if network_data.get('interfaces') else 'unknown',
                    'physical_cores': cpu_data.get('physical_cores', 0),
                    'logical_cores': cpu_data.get('logical_cores', 0),
                    'total_memory': memory_data.get('total', 0),
                    'total_disk': disk_data.get('total', 0)
                }
            }
            
            # Add error information if any
            if has_errors:
                result['has_errors'] = True
                result['errors'] = errors
                
            return result
                
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {str(e)}")
            # Return minimal data structure on error
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_usage': 0,
                'memory_usage': 0,
                'disk_usage': 0,
                'network_sent_rate': 0,
                'network_recv_rate': 0,
                'cpu': {},
                'memory': {},
                'disk': {},
                'network': {},
                'process_count': 0,
                'system_info': {},
                'error': str(e),
                'has_errors': True
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


if __name__ == "__main__":
    asyncio.run(test_simplified_metrics_service())
