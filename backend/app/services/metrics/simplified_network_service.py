#!/usr/bin/env python3
"""
Simplified Network Metrics Service

A direct, no-nonsense network metrics service that collects real-time network data
using psutil and formats it for the frontend. No complex layers, no caching
issues, just pure data.
"""

import psutil
import time
import logging
import socket
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncio


class SimplifiedNetworkService:
    """
    Simplified network metrics service that directly collects and formats network data.
    No complex layers or transformations, just real data.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SimplifiedNetworkService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.logger = logging.getLogger('SimplifiedNetworkService')
        self._last_io_counters = psutil.net_io_counters()
        self._last_io_time = time.time()
        self._initialized = True
        self.logger.info("SimplifiedNetworkService initialized as singleton")
    
    @classmethod
    async def get_instance(cls):
        """Get the singleton instance of the service"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive network metrics directly from psutil.
        No caching, no fallbacks, just real data.
        
        Returns:
            Dictionary containing network metrics formatted for the frontend
        """
        try:
            # Get network interfaces
            interfaces = []
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for interface_name, addr_list in addrs.items():
                # Get interface statistics
                if interface_name in stats:
                    isup = stats[interface_name].isup
                    speed = stats[interface_name].speed
                    mtu = stats[interface_name].mtu
                else:
                    isup = False
                    speed = 0
                    mtu = 0
                
                # Get IP address (prefer IPv4)
                address = ""
                mac_address = ""
                for addr in addr_list:
                    if addr.family == socket.AF_INET:  # IPv4
                        address = addr.address
                    elif addr.family == psutil.AF_LINK:  # MAC
                        mac_address = addr.address
                
                # If no IPv4, try IPv6
                if not address:
                    for addr in addr_list:
                        if addr.family == socket.AF_INET6:  # IPv6
                            address = addr.address
                            break
                
                interfaces.append({
                    'name': interface_name,
                    'address': address,
                    'mac_address': mac_address,
                    'isup': isup,
                    'speed': speed,
                    'mtu': mtu
                })
            
            # Get network I/O statistics
            io_counters = psutil.net_io_counters(pernic=True)
            
            # Calculate I/O rates if we have previous measurements
            bytes_sent = 0
            bytes_recv = 0
            packets_sent = 0
            packets_recv = 0
            sent_rate = 0.0
            recv_rate = 0.0
            
            current_time = time.time()
            total_io = psutil.net_io_counters()
            
            if total_io:
                bytes_sent = total_io.bytes_sent
                bytes_recv = total_io.bytes_recv
                packets_sent = total_io.packets_sent
                packets_recv = total_io.packets_recv
                
                if self._last_io_counters and self._last_io_time:
                    time_diff = current_time - self._last_io_time
                    if time_diff > 0:
                        sent_rate = (total_io.bytes_sent - self._last_io_counters.bytes_sent) / time_diff
                        recv_rate = (total_io.bytes_recv - self._last_io_counters.bytes_recv) / time_diff
            
            # Update last values for next calculation
            self._last_io_counters = total_io
            self._last_io_time = current_time
            
            # Get network connections
            connections = []
            connection_stats = {'ESTABLISHED': 0, 'LISTEN': 0, 'TIME_WAIT': 0, 'CLOSE_WAIT': 0, 'CLOSED': 0, 'OTHER': 0}
            protocol_stats = {'tcp': 0, 'udp': 0, 'tcp6': 0, 'udp6': 0}
            
            try:
                for conn in psutil.net_connections(kind='inet'):
                    # Extract connection details
                    status = conn.status if hasattr(conn, 'status') else 'UNKNOWN'
                    
                    # Update connection status counts
                    if status in connection_stats:
                        connection_stats[status] += 1
                    else:
                        connection_stats['OTHER'] += 1
                    
                    # Update protocol stats
                    if hasattr(conn, 'type'):
                        proto = {
                            socket.SOCK_STREAM: 'tcp',
                            socket.SOCK_DGRAM: 'udp'
                        }.get(conn.type, 'unknown')
                        
                        if conn.family == socket.AF_INET6:
                            proto += '6'
                        
                        if proto in protocol_stats:
                            protocol_stats[proto] += 1
                    
                    # Add connection details (limit to first 100 to avoid overwhelming)
                    if len(connections) < 100:
                        laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if hasattr(conn, 'laddr') and conn.laddr else "-"
                        raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if hasattr(conn, 'raddr') and conn.raddr else "-"
                        
                        connections.append({
                            'fd': conn.fd if hasattr(conn, 'fd') else None,
                            'pid': conn.pid if hasattr(conn, 'pid') else None,
                            'type': proto,
                            'local_address': laddr,
                            'remote_address': raddr,
                            'status': status
                        })
            except (psutil.AccessDenied, psutil.Error) as e:
                self.logger.warning(f"Limited access to network connections: {str(e)}")
            
            # Format the metrics for the frontend
            return {
                'timestamp': datetime.now().isoformat(),
                'type': 'network',
                'data': {
                    'bytes_sent': bytes_sent,
                    'bytes_recv': bytes_recv,
                    'packets_sent': packets_sent,
                    'packets_recv': packets_recv,
                    'sent_rate': sent_rate,
                    'recv_rate': recv_rate,
                    'interfaces': interfaces,
                    'connections': connections,
                    'connection_stats': connection_stats,
                    'protocol_stats': protocol_stats,
                    'latency': None,  # Would require active probing
                    'connection_quality': {
                        'packet_loss': None,  # Would require active probing
                        'jitter': None,  # Would require active probing
                        'bandwidth': sent_rate + recv_rate
                    },
                    'interface_stats': {
                        name: {
                            'bytes_sent': counters.bytes_sent,
                            'bytes_recv': counters.bytes_recv,
                            'packets_sent': counters.packets_sent,
                            'packets_recv': counters.packets_recv,
                            'errin': counters.errin,
                            'errout': counters.errout,
                            'dropin': counters.dropin,
                            'dropout': counters.dropout
                        } for name, counters in io_counters.items()
                    },
                    'dns_metrics': {},  # Would require active DNS queries
                    'internet_metrics': {},  # Would require active internet checks
                    'protocol_breakdown': {
                        'tcp': protocol_stats['tcp'] + protocol_stats['tcp6'],
                        'udp': protocol_stats['udp'] + protocol_stats['udp6'],
                        'http': 0,  # Would require deep packet inspection
                        'file_transfer': 0,  # Would require deep packet inspection
                        'other': 0
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting network metrics: {str(e)}")
            # Return minimal data structure on error
            return {
                'timestamp': datetime.now().isoformat(),
                'type': 'network',
                'data': {
                    'bytes_sent': 0,
                    'bytes_recv': 0,
                    'packets_sent': 0,
                    'packets_recv': 0,
                    'sent_rate': 0.0,
                    'recv_rate': 0.0,
                    'interfaces': [],
                    'connections': [],
                    'connection_stats': {},
                    'protocol_stats': {},
                    'latency': None,
                    'connection_quality': {},
                    'interface_stats': {},
                    'dns_metrics': {},
                    'internet_metrics': {},
                    'protocol_breakdown': {},
                    'error': str(e)
                }
            }
    
    async def get_connection_stats_by_process(self) -> Dict[str, Dict[str, Any]]:
        """
        Get network statistics grouped by process.
        This is an expensive operation and should be used sparingly.
        
        Returns:
            Dictionary mapping process IDs to connection statistics
        """
        try:
            # This is a CPU-intensive operation, run it in a separate thread
            return await asyncio.to_thread(self._get_connection_stats_by_process_sync)
        except Exception as e:
            self.logger.error(f"Error getting connection stats by process: {str(e)}")
            return {}
    
    def _get_connection_stats_by_process_sync(self) -> Dict[str, Dict[str, Any]]:
        """Synchronous implementation of get_connection_stats_by_process"""
        result = {}
        
        try:
            # Get all network connections with process information
            connections = psutil.net_connections(kind='inet')
            
            # Group connections by process ID
            process_connections = {}
            for conn in connections:
                if conn.pid is not None:
                    if conn.pid not in process_connections:
                        process_connections[conn.pid] = []
                    process_connections[conn.pid].append(conn)
            
            # Get process information for each PID
            for pid, conns in process_connections.items():
                try:
                    proc = psutil.Process(pid)
                    
                    # Count connection types
                    conn_types = {'tcp': 0, 'udp': 0, 'tcp6': 0, 'udp6': 0}
                    conn_states = {'ESTABLISHED': 0, 'LISTEN': 0, 'TIME_WAIT': 0, 'CLOSE_WAIT': 0, 'OTHER': 0}
                    
                    for conn in conns:
                        # Count by protocol
                        if hasattr(conn, 'type'):
                            proto = {
                                socket.SOCK_STREAM: 'tcp',
                                socket.SOCK_DGRAM: 'udp'
                            }.get(conn.type, 'unknown')
                            
                            if conn.family == socket.AF_INET6:
                                proto += '6'
                            
                            if proto in conn_types:
                                conn_types[proto] += 1
                        
                        # Count by state
                        status = conn.status if hasattr(conn, 'status') else 'UNKNOWN'
                        if status in conn_states:
                            conn_states[status] += 1
                        else:
                            conn_states['OTHER'] += 1
                    
                    # Add process to result
                    result[str(pid)] = {
                        'name': proc.name(),
                        'username': proc.username(),
                        'connection_count': len(conns),
                        'connection_types': conn_types,
                        'connection_states': conn_states
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
            return result
            
        except Exception as e:
            self.logger.error(f"Error in _get_connection_stats_by_process_sync: {str(e)}")
            return {}


# Test function to run the service directly
async def test_simplified_network_service():
    """Test the simplified network service"""
    print("\n" + "="*60)
    print(" SIMPLIFIED NETWORK SERVICE TEST")
    print("="*60)
    
    # Get timestamp
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize service
    service = await SimplifiedNetworkService.get_instance()
    print(f"Service instance: {service}")
    
    # Get metrics
    metrics = await service.get_metrics()
    print("\nNetwork Metrics:")
    print(f"Bytes Sent: {metrics['data']['bytes_sent'] / (1024 * 1024):.2f} MB")
    print(f"Bytes Received: {metrics['data']['bytes_recv'] / (1024 * 1024):.2f} MB")
    print(f"Send Rate: {metrics['data']['sent_rate'] / 1024:.2f} KB/s")
    print(f"Receive Rate: {metrics['data']['recv_rate'] / 1024:.2f} KB/s")
    
    print("\nNetwork Interfaces:")
    for interface in metrics['data']['interfaces']:
        print(f"  {interface['name']}: {interface['address']} (MAC: {interface['mac_address']})")
        print(f"    Status: {'Up' if interface['isup'] else 'Down'}, Speed: {interface['speed']} Mbps, MTU: {interface['mtu']}")
    
    print("\nConnection Statistics:")
    for status, count in metrics['data']['connection_stats'].items():
        print(f"  {status}: {count}")
    
    print("\nProtocol Statistics:")
    for proto, count in metrics['data']['protocol_stats'].items():
        print(f"  {proto}: {count}")
    
    print("\nActive Connections (first 5):")
    for conn in metrics['data']['connections'][:5]:
        print(f"  {conn['type']} {conn['local_address']} -> {conn['remote_address']} ({conn['status']})")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(test_simplified_network_service())
