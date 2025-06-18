#REFACTORED CODE AS AT 9 MAY 2025
# core/optimization/resource_monitor.py

import psutil
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
import asyncio
import logging
import socket
import time
import subprocess
from functools import lru_cache
from collections import Counter
import os

class ResourceMonitor:
    """
    tSystem Resource Monitor
    
    Watches your system resources like a hawk... 
    if hawks were interested in CPU usage and had a thing for metrics.
    
    Warning: May cause sudden urges to optimize everything in sight.
    """

    def __init__(self):
        self.logger = logging.getLogger('ResourceMonitor')
        self.is_monitoring = False
        self.monitoring_interval = 5  # seconds
        self.last_metrics: Optional[Dict] = None
        
        # Sir Hawkington's Distinguished Cache of Previous Measurements
        self._last_net_io_time = datetime.now()
        self._last_net_io = {}
        self._cache = {}
        
        # The Meth Snail's Cache Expiry Timeline
        self._cache_ttl = {
            'connection_quality': 60,  # Connection quality changes slowly
            'dns_metrics': 300,        # DNS metrics are fairly stable
            'internet_metrics': 120,   # Internet metrics change occasionally
            'interfaces': 30,          # Network interfaces rarely change
        }
        
        # CPU tracking
        self._last_cpu_percent = 0.0
        self._last_cpu_check = 0.0

    async def initialize(self):
        """Initialize the monitor (boot up the surveillance)"""
        self.logger.info("Resource Monitor powering up... beep boop")
        self.is_monitoring = True
        self.last_metrics = {}
        self._cache = {}  # Clear Sir Hawkington's memory banks
        # Initialize CPU reading
        self._last_cpu_percent = psutil.cpu_percent(interval=0.1)
        self._last_cpu_check = time.time()

    async def collect_metrics(self) -> Dict:
        """Collect current system metrics with timeout protection"""
        try:
            # Create overall metrics collection task with timeout
            return await asyncio.wait_for(self._collect_metrics_with_priority(), timeout=5.0)
        except asyncio.TimeoutError:
            self.logger.error("Complete metrics collection timed out")
            # Return minimal metrics
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_usage': self._last_cpu_percent,
                'memory_usage': self._get_memory_usage(),
                'disk_usage': self._get_disk_usage(),
                'timeout_occurred': True,
                'network': {
                    "io_stats": {
                        "bytes_sent": {},
                        "bytes_recv": {},
                        "sent_rate": {},
                        "recv_rate": {}
                    }
                }
            }
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {str(e)}")
            # Return minimal metrics on any error
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'cpu_usage': self._last_cpu_percent,
                'memory_usage': self._get_memory_usage(),
                'disk_usage': self._get_disk_usage()
            }

    async def _collect_metrics_with_priority(self) -> Dict:
        """Collect metrics in priority order"""
        # Essential metrics - fast and lightweight
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu_usage': await self._get_cpu_usage(),
            'memory_usage': self._get_memory_usage(),
            'disk_usage': self._get_disk_usage(),
        }
        
        # Process count - fast but requires list creation
        try:
            # Add a short timeout for process count (should be fast but can be slower on heavily loaded systems)
            process_count = await asyncio.wait_for(
                asyncio.to_thread(lambda: len(list(psutil.process_iter()))), 
                timeout=0.5
            )
            metrics['process_count'] = process_count
        except (asyncio.TimeoutError, Exception) as e:
            self.logger.warning(f"Failed to get process count: {str(e)}")
            metrics['process_count'] = {}
            
        # Standard metrics - network basics (moderate cost)
        try:
            # Network stats can be expensive, so we run it in a thread with timeout
            basic_network = await asyncio.wait_for(
                asyncio.to_thread(self._get_basic_network_stats),
                timeout=1.0
            )
            metrics['network'] = basic_network
        except (asyncio.TimeoutError, Exception) as e:
            self.logger.warning(f"Failed to collect basic network stats: {str(e)}")
            metrics['network'] = {
                "io_stats": {
                    "bytes_sent": {},
                    "bytes_recv": {},
                    "sent_rate": {},
                    "recv_rate": {}
                }
            }
            
        # Try to get additional metrics (lightweight)
        try:
            additional = await asyncio.wait_for(
                self._get_additional_metrics(),
                timeout=1.0
            )
            metrics['additional'] = additional
        except (asyncio.TimeoutError, Exception) as e:
            self.logger.warning(f"Failed to collect additional metrics: {str(e)}")
            metrics['additional'] = {}
            
        # Enhanced network metrics (expensive operations)
        try:
            network_enhanced = await self._get_throttled_network_metrics()
            # Merge with existing network data
            if 'network' in metrics:
                metrics['network'].update(network_enhanced)
            else:
                metrics['network'] = network_enhanced
        except Exception as e:
            self.logger.info(f"Skipping enhanced network metrics: {str(e)}")
            
        self.last_metrics = metrics
        return metrics

    async def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage - non-blocking version"""
        try:
            # Only get a new reading if it's been more than 1 second since last check
            # This prevents excessive CPU usage readings which can be expensive
            current_time = time.time()
            if current_time - self._last_cpu_check >= 1.0:
                # Get instant reading (non-blocking)
                new_percent = psutil.cpu_percent(interval=None)
                if new_percent > 0:
                    self._last_cpu_percent = new_percent
                self._last_cpu_check = current_time
                
            return self._last_cpu_percent
        except Exception as e:
            self.logger.error(f"CPU metric error: {str(e)}")
            return self._last_cpu_percent or {}

    def _get_memory_usage(self) -> float:
        """Get memory usage percentage"""
        try:
            return psutil.virtual_memory().percent
        except Exception as e:
            self.logger.error(f"Memory metric error: {str(e)}")
            return {}

    def _get_disk_usage(self) -> float:
        """Get disk usage percentage"""
        try:
            return psutil.disk_usage('/').percent
        except Exception as e:
            self.logger.error(f"Disk metric error: {str(e)}")
            return {}

    def _format_bytes(self, bytes_value: float) -> str:
        """Format bytes to human-readable format with Sir Hawkington's elegance"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024
        return f"{bytes_value:.2f} PB"

    def _check_cache(self, key: str) -> Tuple[bool, Any]:
        """Check if data exists in The Meth Snail's cache"""
        if key in self._cache:
            timestamp, data = self._cache[key]
            ttl = self._cache_ttl.get(key, 60)  # Default TTL: 60 seconds
            if time.time() - timestamp < ttl:
                return True, data
        return False, None

    def _update_cache(self, key: str, data: Any) -> None:
        """Update Sir Hawkington's distinguished cache"""
        self._cache[key] = (time.time(), data)

    async def _run_command(self, command: List[str], timeout: int = 2) -> Tuple[int, str, str]:
        """Run command asynchronously with strict timeout"""
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for process with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                return process.returncode, stdout.decode('utf-8', errors='ignore'), stderr.decode('utf-8', errors='ignore')
            except asyncio.TimeoutError:
                # Try to terminate the process if it times out
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    process.kill()
                
                return 124, "", f"Timeout after {timeout}s"
        except Exception as e:
            self.logger.warning(f"Command failed: {' '.join(command)}: {str(e)}")
            return 1, "", str(e)
    async def _command_exists(self, command: str) -> bool:
        """Check if a command exists on the system with The Hamsters' diligence"""
        try:
            code, _, _ = await self._run_command(["which", command], timeout=1)
            return code == 0
        except Exception:
            return False

    async def _get_throttled_network_metrics(self) -> Dict[str, Any]:
        """Get enhanced network metrics with throttling"""
        result = {}
        
        # Check for cached connection quality
        cached, data = self._check_cache('connection_quality')
        if cached:
            result["connection_quality"] = data
        else:
            try:
                # Short timeout for connection quality
                connection_quality = await asyncio.wait_for(
                    self._get_connection_quality(),
                    timeout=2.0
                )
                result["connection_quality"] = connection_quality
                self._update_cache('connection_quality', connection_quality)
            except (asyncio.TimeoutError, Exception) as e:
                self.logger.info(f"Skipping connection quality metrics: {str(e)}")
        
        # Check for cached DNS metrics
        cached, data = self._check_cache('dns_metrics')
        if cached:
            result["dns_metrics"] = data
        else:
            try:
                # Short timeout for DNS metrics
                dns_metrics = await asyncio.wait_for(
                    self._get_dns_metrics(),
                    timeout=2.0
                )
                result["dns_metrics"] = dns_metrics
                self._update_cache('dns_metrics', dns_metrics)
            except (asyncio.TimeoutError, Exception) as e:
                self.logger.info(f"Skipping DNS metrics: {str(e)}")
        
        # Check for cached internet metrics
        cached, data = self._check_cache('internet_metrics')
        if cached:
            result["internet_metrics"] = data
        else:
            try:
                # Short timeout for internet metrics
                internet_metrics = await asyncio.wait_for(
                    self._get_internet_metrics(),
                    timeout=3.0
                )
                result["internet_metrics"] = internet_metrics
                self._update_cache('internet_metrics', internet_metrics)
            except (asyncio.TimeoutError, Exception) as e:
                self.logger.info(f"Skipping internet metrics: {str(e)}")
        
        # Network connections and interfaces are less expensive, but still throttle them
        try:
            # Get connections with timeout
            connections = await asyncio.wait_for(
                asyncio.to_thread(self._get_network_connections),
                timeout=1.0
            )
            result["connections"] = connections
        except (asyncio.TimeoutError, Exception) as e:
            self.logger.info(f"Skipping network connections: {str(e)}")
        
        # Check for cached interface data
        cached, data = self._check_cache('interfaces')
        if cached:
            interfaces, interface_stats = data
            result["interfaces"] = interfaces
            result["interface_stats"] = interface_stats
        else:
            try:
                # Get interfaces with timeout
                interfaces_data = await asyncio.wait_for(
                    asyncio.to_thread(self._get_network_interfaces),
                    timeout=1.0
                )
                interfaces, interface_stats = interfaces_data
                result["interfaces"] = interfaces
                result["interface_stats"] = interface_stats
                self._update_cache('interfaces', interfaces_data)
            except (asyncio.TimeoutError, Exception) as e:
                self.logger.info(f"Skipping network interfaces: {str(e)}")
        
        return result

    def _get_basic_network_stats(self) -> Dict[str, Any]:
        """Get basic network I/O stats - The Quantum Shadow People's domain"""
        try:
            net_io = psutil.net_io_counters()
            current_time = time.time()
            uptime = max(1, current_time - psutil.boot_time())  # Avoid division by zero
            
            # Calculate rates based on uptime (long-term average)
            sent_rate_avg = net_io.bytes_sent / uptime
            recv_rate_avg = net_io.bytes_recv / uptime
            
            # Calculate instantaneous rates if we have previous measurements
            if self._last_net_io and self._last_net_io_time:
                time_delta = current_time - self._last_net_io_time
                if time_delta > 0:  # Avoid division by zero
                    sent_rate = (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_delta
                    recv_rate = (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_delta
                else:
                    sent_rate = sent_rate_avg
                    recv_rate = recv_rate_avg
            else:
                sent_rate = sent_rate_avg
                recv_rate = recv_rate_avg
            
            # Update last values for next calculation
            self._last_net_io = net_io
            self._last_net_io_time = current_time
            
            # Calculate total rates
            total_rate = sent_rate + recv_rate            
            return {
                "io_stats": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                    "dropin": net_io.dropin,
                    "dropout": net_io.dropout,
                    "sent_rate": sent_rate,
                    "recv_rate": recv_rate,
                    "total_rate": total_rate,
                    "bytes_sent_formatted": self._format_bytes(net_io.bytes_sent),
                    "bytes_recv_formatted": self._format_bytes(net_io.bytes_recv),
                    "sent_rate_formatted": f"{self._format_bytes(sent_rate)}/s",
                    "recv_rate_formatted": f"{self._format_bytes(recv_rate)}/s",
                    "total_rate_formatted": f"{self._format_bytes(total_rate)}/s"
                },
                "total_usage_mb": (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024
            }
        except Exception as e:
            self.logger.error(f"Error getting basic network stats: {str(e)}")
            return {
                "io_stats": {
                    "bytes_sent": {},
                    "bytes_recv": {},
                    "sent_rate": {},
                    "recv_rate": {},
                    "bytes_sent_formatted": "{} B",
                    "bytes_recv_formatted": "{} B",
                    "total_rate_formatted": "{} B/s"
                },
                "total_usage_mb": {}
            }

    def _get_network_connections(self) -> List[Dict[str, Any]]:
        """Get network connections - Sir Hawkington's connection registry"""
        connections = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                try:
                    # Format addresses with The Stick's precision
                    laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
                    raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
                    
                    # Get process name with The Hamsters' diligence
                    process_name = "Unknown"
                    if conn.pid:
                        try:
                            process = psutil.Process(conn.pid)
                            process_name = process.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    # Add connection to the registry
                    connections.append({
                        "type": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                        "laddr": laddr,
                        "raddr": raddr,
                        "status": conn.status,
                        "pid": conn.pid,
                        "process_name": process_name
                    })
                except Exception as e:
                    self.logger.debug(f"Error processing connection: {str(e)}")
                    continue
        except (psutil.AccessDenied, PermissionError) as e:
            self.logger.warning(f"Permission denied when accessing network connections: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error collecting network connections: {str(e)}")
        
        return connections

    def _get_network_interfaces(self) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """Get network interfaces and stats - The Hamsters' domain"""
        interfaces = []
        interface_stats = {}
        
        try:
            # Get network interfaces
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            net_io_counters = psutil.net_io_counters(pernic=True)
            
            # Process each interface with The Hamsters' thoroughness
            for name, addrs in net_if_addrs.items():
                try:
                    # Extract addresses
                    ip_address = None
                    mac_address = None
                    for addr in addrs:
                        if addr.family == socket.AF_INET:
                            ip_address = addr.address
                        elif addr.family == psutil.AF_LINK:
                            mac_address = addr.address
                    
                    # Get interface stats
                    is_up = False
                    speed = ""
                    mtu = ""
                    if name in net_if_stats:
                        is_up = net_if_stats[name].isup
                        speed = net_if_stats[name].speed
                        mtu = net_if_stats[name].mtu
                    
                    # Add interface to list
                    interfaces.append({
                        "name": name,
                        "address": ip_address,
                        "mac_address": mac_address,
                        "isup": is_up,
                        "speed": speed,
                        "mtu": mtu
                    })
                    
                    # Get interface I/O stats
                    if name in net_io_counters:
                        counter = net_io_counters[name]
                        interface_stats[name] = {
                            "bytes_sent": counter.bytes_sent,
                            "bytes_recv": counter.bytes_recv,
                            "packets_sent": counter.packets_sent,
                            "packets_recv": counter.packets_recv,
                            "errin": counter.errin,
                            "errout": counter.errout,
                            "dropin": counter.dropin,
                            "dropout": counter.dropout
                        }
                except Exception as e:
                    self.logger.debug(f"Error processing interface {name}: {str(e)}")
                    continue
            
            return interfaces, interface_stats
            
        except Exception as e:
            self.logger.error(f"Error collecting interface info: {str(e)}")
            return [], {}

    def _get_protocol_breakdown(self) -> Dict[str, int]:
        """Get protocol breakdown from connections - The Meth Snail's specialty"""
        protocol_counts = {"tcp": "", "udp": "", "http": "", "https": "", "dns": ""}
        
        try:
            # Count TCP/UDP from connections
            for conn in psutil.net_connections(kind='inet'):
                try:
                    if conn.type == socket.SOCK_STREAM:
                        protocol_counts["tcp"] += 1
                        # Check for HTTP/HTTPS based on port
                        if hasattr(conn, 'raddr') and conn.raddr:
                            if conn.raddr.port == 80:
                                protocol_counts["http"] += 1
                            elif conn.raddr.port == 443:
                                protocol_counts["https"] += 1
                        if hasattr(conn, 'laddr') and conn.laddr:
                            if conn.laddr.port == 80:
                                protocol_counts["http"] += 1
                            elif conn.laddr.port == 443:
                                protocol_counts["https"] += 1
                    elif conn.type == socket.SOCK_DGRAM:
                        protocol_counts["udp"] += 1
                        # Check for DNS based on port
                        if (hasattr(conn, 'raddr') and conn.raddr and conn.raddr.port == 53) or \
                           (hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == 53):
                            protocol_counts["dns"] += 1
                except (AttributeError, Exception) as e:
                    continue
            
            # Calculate percentages
            total_connections = sum(protocol_counts.values())
            if total_connections > 0:
                return {k: int((v / total_connections) * 100) for k, v in protocol_counts.items()}
            
            # Ensure at least 1% for visualization
            for protocol in protocol_counts:
                protocol_counts[protocol] = max(1, protocol_counts[protocol])
                
            return protocol_counts
            
        except Exception as e:
            self.logger.error(f"Error collecting protocol breakdown: {str(e)}")
            return {"tcp": "", "udp": "", "http": "", "https": "", "dns": ""}
 
    async def _get_connection_quality(self) -> Dict[str, Any]:
        """Get connection quality metrics - The Stick's domain of precise measurements"""
        # Default values for connection quality (more realistic defaults)
        quality_data = {
            "average_latency": "",  # 25.5ms average latency
            "min_latency": "",     # 20ms minimum latency
            "max_latency": "",     # 35ms maximum latency
            "jitter": "",           # 2.5ms jitter
            "packet_loss_percent": "",  # 0.5% packet loss
            "connection_stability": "",  # 95% stability score
            "overall_score": "",    # 90/100 overall score
            "gateway_latency": "",   # 1.2ms gateway latency
            "dns_latency": "",      # 10.5ms DNS latency
            "internet_latency": ""  # 25.5ms internet latency
        }
        
        # The Stick only proceeds with ping if it's available
        if not await self._command_exists('ping'):
            self.logger.warning("The Stick is dismayed: ping command not found for connection quality assessment")
            return quality_data
            
        try:
            # The Stick selects distinguished targets for quality assessment
            targets = ["8.8.8.8", "1.1.1.1"]  # Reduced target list for efficiency
            latencies = []
            packet_loss = ""
            ping_count = 2  # Reduced ping count
            
            # The Stick methodically tests each target
            for target in targets:
                try:
                    code, stdout, _ = await self._run_command(
                        ["ping", "-c", str(ping_count), "-W", "1", target],
                        timeout=2  # Reduced timeout
                    )
                    
                    # Extract latency from ping output
                    if code == 0:
                        # Parse ping output to get min/avg/max/mdev
                        stats_line = stdout.strip().split("\n")[-1]
                        if "min/avg/max" in stats_line:
                            # Extract values from line like: rtt min/avg/max/mdev = 20.442/22.129/25.427/1.987 ms
                            values = stats_line.split("=")[1].strip().split("/")
                            latencies.append({
                                "min": float(values[0]),
                                "avg": float(values[1]),
                                "max": float(values[2]),
                                "mdev": float(values[3].split()[0])  # Remove 'ms' suffix
                            })
                        
                        # Check for packet loss with The Stick's unparalleled attention to detail
                        for line in stdout.strip().split("\n"):
                            if "packet loss" in line:
                                loss_pct = float(line.split("%")[0].split()[-1])
                                packet_loss += loss_pct / len(targets)
                                break
                except Exception as e:
                    self.logger.debug(f"The Stick is disappointed: Ping to {target} failed: {str(e)}")
                    packet_loss += 100 / len(targets)  # Count as 100% loss for this target
            
            # The Stick calculates aggregate metrics with mathematical precision
            if latencies:
                min_latency = min(l["min"] for l in latencies)
                max_latency = max(l["max"] for l in latencies)
                avg_latency = sum(l["avg"] for l in latencies) / len(latencies)
                jitter = sum(l["mdev"] for l in latencies) / len(latencies)
                
                # The Stick's proprietary stability algorithm
                stability = max(0, 100 - (packet_loss * 0.8) - (jitter * 2))
                
                # The Stick's holistic quality assessment
                overall_score = max(0, 100 - (avg_latency * 0.5) - (packet_loss * 0.8) - (jitter * 2))
                
                quality_data = {
                    "average_latency": "",
                    "min_latency": "",
                    "max_latency": "",
                    "jitter": "",
                    "packet_loss_percent": "",
                    "connection_stability": "",
                    "overall_score": round(overall_score, 1)
                }
            
        except Exception as e:
            self.logger.error(f"The Stick has encountered a regulatory violation: {str(e)}")
            
        return quality_data

    async def _get_dns_metrics(self) -> Dict[str, Any]:
        """Get DNS metrics - The Quantum Shadow People's reconnaissance mission"""
        # Default DNS metrics for The Quantum Shadow People's baseline
        dns_data = {
            "query_time_ms": "",
            "success_rate": "",
            "cache_hit_ratio": "",
            "last_failures": ""
        }
        
        # The Quantum Shadow People only proceed if dig is available
        if not await self._command_exists('dig'):
            self.logger.warning("The Quantum Shadow People cannot find 'dig' tool for DNS metrics")
            return dns_data
            
        try:
            # The Quantum Shadow People's target DNS infrastructure - reduced for efficiency
            dns_servers = ["8.8.8.8"]
            domains = ["google.com", "github.com"]
            query_times = []
            success_count = 0
            total_queries = len(dns_servers) * len(domains)
            
            # The Quantum Shadow People perform interdimensional DNS queries
            for server in dns_servers:
                for domain in domains:
                    try:
                        code, stdout, stderr = await self._run_command(
                            ["dig", "@"+server, domain, "+stats", "+noall", "+answer"],
                            timeout=2  # Reduced timeout
                        )
                        
                        # The Quantum Shadow People validate query success
                        if code == 0 and stdout.strip():
                            success_count += 1
                            
                            # Extract query time with quantum precision
                            output = stdout + stderr  # Combine outputs to check both
                            for line in output.strip().split("\n"):
                                if "Query time:" in line:
                                    time_ms = float(line.split(":")[1].strip().split()[0])
                                    query_times.append(time_ms)
                                    break
                    except Exception as e:
                        self.logger.debug(f"The Quantum Shadow People's DNS query to {server} for {domain} failed: {str(e)}")
            
            # The Quantum Shadow People calculate metrics with probabilistic uncertainty
            if query_times:
                avg_query_time = sum(query_times) / len(query_times)
            else:
                avg_query_time = 0
                
            success_rate = success_count / total_queries if total_queries > 0 else 0
            
            # The Quantum Shadow People's cache hit ratio estimation
            cache_hit_ratio = 0.5  # Quantum default state
            if len(query_times) >= 2:
                # Sort query times and compare first half vs second half
                sorted_times = sorted(query_times)
                half = len(sorted_times) // 2
                if half > 0:
                    first_half_avg = sum(sorted_times[:half]) / half
                    second_half_avg = sum(sorted_times[half:]) / (len(sorted_times) - half)
                    if first_half_avg > 0:
                        # Quantum entanglement formula for cache ratio
                        time_ratio = second_half_avg / first_half_avg
                        cache_hit_ratio = max(0, min(1, 1 - time_ratio))
            
            dns_data = {
                "query_time_ms": round(avg_query_time, 1),
                "success_rate": round(success_rate, 2),
                "cache_hit_ratio": round(cache_hit_ratio, 2),
                "last_failures": total_queries - success_count
            }
            
        except Exception as e:
            self.logger.error(f"The Quantum Shadow People's dimensional rift encountered an anomaly: {str(e)}")
            
        return dns_data

    async def _get_internet_metrics(self) -> Dict[str, Any]:
        """Get internet connectivity metrics - The Meth Snail's cosmic journey"""
        # The Meth Snail's baseline internet metrics
        internet_data = {
            "gateway_latency_ms": "",
            "internet_latency_ms": "",
            "hop_count": "",
            "isp_performance_score": ""
        }    
        try:
            # The Meth Snail searches for the network gateway
            gateway_ip = await self._get_default_gateway()
            
            # The Meth Snail measures gateway latency with cosmic precision
            gateway_latency = ""
            if gateway_ip:
                code, stdout, _ = await self._run_command(
                    ["ping", "-c", "2", "-W", "1", gateway_ip],  # Reduced ping count
                    timeout=2 
                )
                if code == 0:
                    # Extract average latency from the cosmic ping
                    for line in stdout.strip().split("\n"):
                        if "min/avg/max" in line:
                            try:
                                gateway_latency = float(line.split("/")[1])
                                break
                            except (ValueError, IndexError):
                                pass
            
            # The Meth Snail travels the cosmic internet - reduced number of targets
            internet_targets = ["google.com"]
            internet_latencies = []
            
            for target in internet_targets:
                code, stdout, _ = await self._run_command(
                    ["ping", "-c", "2", "-W", "1", target],  # Reduced ping count
                    timeout=3  # Reduced timeout
                )
                if code == 0:
                    for line in stdout.strip().split("\n"):
                        if "min/avg/max" in line:
                            try:
                                avg_latency = float(line.split("/")[1])
                                internet_latencies.append(avg_latency)
                                break
                            except (ValueError, IndexError):
                                pass
            
            # The Meth Snail calculates average internet latency
            internet_latency = sum(internet_latencies) / len(internet_latencies) if internet_latencies else 0
            
            # The Meth Snail counts hops in the cosmic traceroute - only if we have time
            hop_count = 0
            # Skip traceroute as it's too slow - we'll estimate hop count instead
            # based on latency difference between gateway and internet
            if gateway_latency > 0 and internet_latency > 0:
                # Rough estimate: 1 hop per 10ms latency difference plus a base of 3
                latency_diff = max(0, internet_latency - gateway_latency)
                hop_count = 3 + int(latency_diff / 10)
            
            # The Meth Snail's cosmic ISP performance formula
            isp_score = 100  # Start at cosmic perfection
            if gateway_latency > 0:
                # The Meth Snail's gateway latency penalty
                isp_score -= min(30, gateway_latency * 3)
            
            if internet_latency > 0:
                # The Meth Snail's internet latency penalty
                isp_score -= min(40, (internet_latency - 20) / 2)
            
            if hop_count > 0:
                # The Meth Snail's hop count penalty
                isp_score -= min(20, max(0, hop_count - 8) * 2)
            
            # The Meth Snail ensures the score stays within the cosmic range
            isp_score = max(0, min(100, isp_score))
            
            internet_data = {
                "gateway_latency_ms": "",
                "internet_latency_ms": "",
                "hop_count": "",
                "isp_performance_score": ""
            }
            
        except Exception as e:
            self.logger.error(f"The Meth Snail's cosmic journey was interrupted: {str(e)}")
            
        return internet_data

    async def _get_default_gateway(self) -> Optional[str]:
        """Get the default gateway IP - The Meth Snail's router discovery"""
        gateway_ip = None
        try:
            # The Meth Snail uses standard commands for router discovery
            if await self._command_exists('ip'):
                code, stdout, _ = await self._run_command(
                    ["ip", "route", "show", "default"],
                    timeout=1  # Reduced timeout
                )
                if code == 0:
                    route_output = stdout.strip()
                    if route_output:
                        # Parse output like: default via 192.168.1.1 dev wlp2s0 proto dhcp metric 600
                        parts = route_output.split()
                        if len(parts) > 2 and parts[0] == "default" and parts[1] == "via":
                            gateway_ip = parts[2]
            
            # The Meth Snail has alternative methods for router discovery
            if not gateway_ip and await self._command_exists('route'):
                code, stdout, _ = await self._run_command(
                    ["route", "-n"],
                    timeout=1  # Reduced timeout
                )
                if code == 0:
                    for line in stdout.strip().split('\n'):
                        if line.startswith('0.0.0.0'):
                            parts = line.split()
                            if len(parts) >= 2:
                                gateway_ip = parts[1]
                                break
                    
        except Exception as e:
            self.logger.warning(f"The Meth Snail couldn't find the default gateway: {str(e)}")
            
        return gateway_ip

    async def _get_additional_metrics(self) -> Dict:
        """Get additional system metrics - The Hamsters' supplementary research"""
        try:
            # Run CPU temperature check in thread to avoid blocking
            cpu_temp = await asyncio.to_thread(self._get_cpu_temperature)
            
            # Run python process count in thread
            python_count = await asyncio.to_thread(self._count_python_processes)
            
            # Get load average and uptime - these are usually fast
            load_avg = self._get_load_average()
            uptime = self._get_system_uptime()
            
            # The Hamsters diligently collect additional system insights
            return {
                'swap_usage': psutil.swap_memory().percent,
                'cpu_temperature': cpu_temp,
                'active_python_processes': python_count,
                'load_average': load_avg,
                'uptime': uptime
            }
        except Exception as e:
            self.logger.error(f"The Hamsters encountered a metrics collection issue: {str(e)}")
            return {}

    def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature if available - Sir Hawkington's thermal oversight"""
        try:
            # Sir Hawkington checks various temperature sensors
            temps = psutil.sensors_temperatures()
            
            # Check for common temperature sensor names across platforms
            for sensor_name in ['coretemp', 'k10temp', 'cpu_thermal', 'acpitz']:
                if temps and sensor_name in temps and temps[sensor_name]:
                    # Return the first core's temperature
                    return temps[sensor_name][0].current
                    
            # Sir Hawkington couldn't find temperature sensors
            return None
        except Exception as e:
            self.logger.debug(f"Sir Hawkington's thermal monocle malfunctioned: {str(e)}")
            return None

    def _count_python_processes(self) -> int:
        """Count number of Python processes - The Meth Snail's python census"""
        try:
            # The Meth Snail carefully counts all python processes
            python_count = 0
            for p in psutil.process_iter(['name', 'cmdline']):
                try:
                    # Check if 'python' appears in the process name
                    if 'python' in p.info['name'].lower():
                        python_count += 1
                    # Also check command line for python interpreters
                    elif p.info['cmdline'] and any('python' in cmd.lower() for cmd in p.info['cmdline']):
                        python_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # The Meth Snail methodically ignores vanishing processes
                    continue
                    
            return python_count
        except Exception as e:
            self.logger.debug(f"The Meth Snail's python census was disrupted: {str(e)}")
            return 0

    def _get_load_average(self) -> List[float]:
        """Get system load average - The Quantum Shadow People's workload analysis"""
        try:
            # The Quantum Shadow People analyze system load
            # Normalize by CPU count to get per-core load
            cpu_count = psutil.cpu_count() or 1  # Avoid division by zero
            return [x / cpu_count * 100 for x in psutil.getloadavg()]
        except Exception as e:
            self.logger.debug(f"The Quantum Shadow People's load analysis failed: {str(e)}")
            return [0.0, 0.0, 0.0]
            
    def _get_system_uptime(self) -> int:
        """Get system uptime in seconds - The Hamsters' uptime chronometer"""
        try:
            # The Hamsters measure system uptime with precision
            return int(time.time() - psutil.boot_time())
        except Exception as e:
            self.logger.debug(f"The Hamsters' chronometer malfunctioned: {str(e)}")
            return 0

    async def start_monitoring(self):
        """Start continuous monitoring with error handling and backoff"""
        self.logger.info("Sir Hawkington commences the distinguished monitoring vigil")
        self.is_monitoring = True
        retry_delay = 1
        last_success = time.time()
        
        while self.is_monitoring:
            try:
                metrics = await self.collect_metrics()
                self.last_metrics = metrics
                
                # Reset backoff on success
                retry_delay = 1
                last_success = time.time()
                
            except Exception as e:
                # Calculate time since last success
                time_since_success = time.time() - last_success
                
                self.logger.error(
                    f"Monitoring error after {time_since_success:.1f}s: {str(e)}"
                )
                
                # Use exponential backoff with a maximum retry delay
                backoff_delay = min(retry_delay, 30)
                self.logger.info(f"Backing off for {backoff_delay}s before retry")
                await asyncio.sleep(backoff_delay)
                retry_delay *= 2
            
            # Regular interval between collections
            await asyncio.sleep(self.monitoring_interval)

    async def stop_monitoring(self):
        """Stop monitoring - Sir Hawkington retires to his perch"""
        self.logger.info("Sir Hawkington gracefully concludes his monitoring duties")
        self.is_monitoring = False

    async def get_status(self) -> Dict:
        """Get current monitoring status - The Meth Snail's status report"""
        # The Meth Snail delivers a detailed status report
        status = {
            'is_monitoring': self.is_monitoring,
            'monitoring_interval': self.monitoring_interval,
            'cache_size': len(self._cache),
            'system_uptime': self._get_system_uptime(),
        }
        
        # Add last update time if available
        if self.last_metrics and 'timestamp' in self.last_metrics:
            status['last_update'] = self.last_metrics['timestamp']
        
        # Add monitoring duration if active
        if self.is_monitoring and self.last_metrics and 'timestamp' in self.last_metrics:
            start_time = self.last_metrics['timestamp']
            if isinstance(start_time, str):
                try:
                    start_time = datetime.fromisoformat(start_time)
                except (ValueError, TypeError):
                    start_time = None
                    
            if isinstance(start_time, datetime):
                status['monitoring_duration'] = (datetime.now() - start_time).total_seconds()
        
        return status

    async def cleanup(self):
        """Cleanup monitor resources - The farewell ceremony"""
        self.logger.info("Resource Monitor powering down... *sad beep*")
        self.logger.info("Sir Hawkington hangs up his aristocratic monitoring monocle")
        self.logger.info("The Meth Snail retreats to the cosmic void of system hibernation")
        self.is_monitoring = False
        self._cache.clear()

 # Reduced timeout            total_rate
# #REFACTORED CODE AS AT 9 MAY 2025
# # core/optimization/resource_monitor.py

# import psutil
# from typing import Dict, Any, List, Optional, Tuple, Callable
# from datetime import datetime
# import asyncio
# import logging
# import socket
# import time
# import subprocess
# from functools import lru_cache
# from collections import Counter
# import os

# class ResourceMonitor:
#     """
#     System Resource Monitor
    
#     Watches your system resources like a hawk... 
#     if hawks were interested in CPU usage and had a thing for metrics.
    
#     Warning: May cause sudden urges to optimize everything in sight.
#     """

#     def __init__(self):
#         self.logger = logging.getLogger('ResourceMonitor')
#         self.is_monitoring = False
#         self.monitoring_interval = 5  # seconds
#         self.last_metrics: Optional[Dict] = None
        
#         # Sir Hawkington's Distinguished Cache of Previous Measurements
#         self._last_net_io_time = 0
#         self._last_net_io = None
#         self._cache = {}
        
#         # The Meth Snail's Cache Expiry Timeline
#         self._cache_ttl = {
#             'connection_quality': 60,  # Connection quality changes slowly
#             'dns_metrics': 300,        # DNS metrics are fairly stable
#             'internet_metrics': 120,   # Internet metrics change occasionally
#             'interfaces': 30,          # Network interfaces rarely change
#         }

#     async def initialize(self):
#         """Initialize the monitor (boot up the surveillance)"""
#         self.logger.info("Resource Monitor powering up... beep boop")
#         self.is_monitoring = False
#         self.last_metrics = None
#         self._cache = {}  # Clear Sir Hawkington's memory banks

#     def _throttled(self, cache_key: str, ttl_seconds: int):
#         """Decorator to throttle expensive operations"""
#         def decorator(func):
#             async def wrapper(*args, **kwargs):
#                 # Check cache first
#                 now = time.time()
#                 cache_entry = self._cache.get(cache_key)
                
#                 if cache_entry and (now - cache_entry[0]) < ttl_seconds:
#                     return cache_entry[1]
                    
#                 # Execute function and cache result
#                 result = await func(*args, **kwargs)
#                 self._cache[cache_key] = (now, result)
#                 return result
#             return wrapper
#         return decorator
    
#     @_throttled('connection_quality', 300)  # Refresh every 5 minutes
#     def _get_connection_quality(self) -> Dict[str, Any]:
#         """Get connection quality metrics including latency and packet loss"""
#         try:
#             # Measure latency to a reliable server
#             latency = self._measure_latency()
            
#             # Get packet loss information
#             net_io = psutil.net_io_counters()
#             total_packets = net_io.packets_sent + net_io.packets_recv
            
#             # This is a simplified example - in a real app you'd track this over time
#             packet_loss = 0.0  # This would be calculated based on sent/received metrics
            
#             return {
#                 'latency_ms': latency,
#                 'packet_loss_percent': packet_loss,
#                 'connection_strength': self._estimate_connection_strength(latency, packet_loss)
#             }
#         except Exception as e:
#             self.logger.error(f"Error getting connection quality: {str(e)}")
#             return {
#                 'latency_ms': None,
#                 'packet_loss_percent': None,
#                 'connection_strength': 'unknown'
#             }
    
#     def _measure_latency(self) -> float:
#         """Measure network latency in milliseconds"""
#         # This is a placeholder - in a real implementation, you might ping a server
#         # or use a more sophisticated method to measure latency
#         try:
#             # Using a simple socket connection to measure latency
#             import socket
#             import time
            
#             start = time.time()
#             # Try connecting to a reliable server (e.g., Google DNS)
#             socket.create_connection(("8.8.8.8", 53), timeout=1)
#             return (time.time() - start) * 1000  # Convert to milliseconds
#         except Exception as e:
#             self.logger.warning(f"Could not measure latency: {str(e)}")
#             return float('inf')
    
#     def _estimate_connection_strength(self, latency: float, packet_loss: float) -> str:
#         """Estimate connection strength based on latency and packet loss"""
#         if latency is None or packet_loss is None:
#             return 'unknown'
            
#         if latency > 500 or packet_loss > 10:  # High latency or packet loss
#             return 'poor'
#         elif latency > 200 or packet_loss > 5:  # Moderate latency or packet loss
#             return 'fair'
#         else:
#             return 'good'
    
#     @_throttled('internet_metrics', 300)  # Refresh every 5 minutes
#     def _get_internet_metrics(self) -> Dict[str, Any]:
#         """Get internet metrics"""
#         return {}
    
#     def _check_internet_connectivity(self, host: str = "8.8.8.8", port: int = 53, timeout: int = 3) -> bool:
#         """Check if there is an active internet connection"""
#         import socket
#         try:
#             socket.setdefaulttimeout(timeout)
#             socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
#             return True
#         except (socket.error, socket.timeout):
#             return False
        
#     # async def collect_metrics(self) -> Dict:
#     #     """Collect current system metrics"""
#     #     try:
#     #         # Convert process iterator to list before getting length
#     #         process_count = len(list(psutil.process_iter()))

#     #         # Sir Hawkington prepares to survey the network landscape
#     #         self.logger.info("About to collect network metrics")
#     #         network_data = self._get_network_usage()
#     #         self.logger.info(f"Network metrics collected: {network_data.keys()}")

#     #         # The Meth Snail's Comprehensive Metrics Package
#     #         metrics = {
#     #             'timestamp': datetime.now(),
#     #             'cpu_usage': await self._get_cpu_usage(),
#     #             'memory_usage': self._get_memory_usage(),
#     #             'disk_usage': self._get_disk_usage(),
#     #             'network': network_data,
#     #             'process_count': process_count,
#     #             'additional': await self._get_additional_metrics()
#     #         }
            
#     #         # Sir Hawkington verifies the metrics collection
#     #         self.logger.info(f"Final metrics structure keys: {metrics.keys()}")
#     #         self.logger.info(f"Network data included: {'network' in metrics}")
            
#     #         self.last_metrics = metrics
#     #         return metrics

#     #     except Exception as e:
#     #         self.logger.error(f"Error collecting metrics: {str(e)}")
#     #         raise


# Collapse
# async def collect_metrics(self) -> Dict:
#     """Collect current system metrics with timeout protection"""
#     try:
#         # Create a task with timeout
#         async def _collect_metrics_impl():
#             metrics = {
#                 'timestamp': datetime.now(),
#                 'cpu_usage': await self._get_cpu_usage(),
#                 'memory_usage': self._get_memory_usage(),
#                 'disk_usage': self._get_disk_usage(),
#                 'process_count': len(list(psutil.process_iter()))
#             }
            
#             # Add network data with separate timeout
#             try:
#                 network_data = await asyncio.wait_for(
#                     asyncio.to_thread(self._get_network_usage), 
#                     timeout=2.0
#                 )
#                 metrics['network'] = network_data
#             except asyncio.TimeoutError:
#                 self.logger.warning("Network metrics collection timed out")
#                 metrics['network'] = {"io_stats": {"bytes_sent": 0, "bytes_recv": 0}}
                
#             # Add additional metrics with separate timeout
#             try:
#                 additional = await asyncio.wait_for(
#                     self._get_additional_metrics(), 
#                     timeout=1.0
#                 )
#                 metrics['additional'] = additional
#             except asyncio.TimeoutError:
#                 self.logger.warning("Additional metrics collection timed out")
#                 metrics['additional'] = {}
                
#             return metrics
            
#         return await asyncio.wait_for(_collect_metrics_impl(), timeout=5.0)
#     except asyncio.TimeoutError:
#         self.logger.error("Complete metrics collection timed out")
#         # Return minimal metrics
#         return {
#             'timestamp': datetime.now(),
#             'cpu_usage': 0,
#             'memory_usage': self._get_memory_usage(),
#             'disk_usage': 0,
#             'timeout_occurred': True,
#             'network': {"io_stats": {"bytes_sent": 0, "bytes_recv": 0}}
#         }
#     except Exception as e:
#         self.logger.error(f"Error collecting metrics: {str(e)}")
#         # Return minimal metrics on any error
#         return {
#             'timestamp': datetime.now(),
#             'error': str(e),
#             'cpu_usage': 0,
#             'memory_usage': 0,
#             'disk_usage': 0
#         }
#     # async def _get_cpu_usage(self) -> float:
#     #     """Get CPU usage percentage"""
#     #     try:
#     #         # CPU usage needs a small interval to calculate
#     #         return psutil.cpu_percent(interval=1)
#     #     except Exception as e:
#     #         self.logger.error(f"CPU metric error: {str(e)}")
#     #         return 0.0
# async def _get_cpu_usage(self) -> float:
#     """Get CPU usage percentage - non-blocking version"""
#     try:
#         # Initialize CPU usage on first call
#         if not hasattr(self, '_last_cpu_percent'):
#             # Call once with interval to initialize
#             self._last_cpu_percent = psutil.cpu_percent(interval=0.1)
            
#         # Get instant reading on subsequent calls (non-blocking)
#         current = psutil.cpu_percent(interval=None)
        
#         # Apply smoothing for more stable readings
#         self._last_cpu_percent = current if current > 0 else self._last_cpu_percent
#         return self._last_cpu_percent
#     except Exception as e:
#         self.logger.error(f"CPU metric error: {str(e)}")
#         return 0.0
    
#     def _get_memory_usage(self) -> float:
#         """Get memory usage percentage"""
#         try:
#             return psutil.virtual_memory().percent
#         except Exception as e:
#             self.logger.error(f"Memory metric error: {str(e)}")
#             return 0.0

#     def _get_disk_usage(self) -> float:
#         """Get disk usage percentage"""
#         try:
#             return psutil.disk_usage('/').percent
#         except Exception as e:
#             self.logger.error(f"Disk metric error: {str(e)}")
#             return 0.0

#     def _format_bytes(self, bytes_value: float) -> str:
#         """Format bytes to human-readable format with Sir Hawkington's elegance"""
#         for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
#             if bytes_value < 1024:
#                 return f"{bytes_value:.2f} {unit}"
#             bytes_value /= 1024
#         return f"{bytes_value:.2f} PB"

#     def _check_cache(self, key: str) -> Tuple[bool, Any]:
#         """Check if data exists in The Meth Snail's cache"""
#         if key in self._cache:
#             timestamp, data = self._cache[key]
#             ttl = self._cache_ttl.get(key, 60)  # Default TTL: 60 seconds
#             if time.time() - timestamp < ttl:
#                 return True, data
#         return False, None

#     def _update_cache(self, key: str, data: Any) -> None:
#         """Update Sir Hawkington's distinguished cache"""
#         self._cache[key] = (time.time(), data)

#     def _run_command(self, command: List[str], timeout: int = 5) -> Tuple[int, str, str]:
#         """The Meth Snail's command execution station"""
#         try:
#             result = subprocess.run(
#                 command,
#                 capture_output=True,
#                 text=True,
#                 timeout=timeout
#             )
#             return result.returncode, result.stdout, result.stderr
#         except subprocess.TimeoutExpired:
#             self.logger.warning(f"Command timed out after {timeout}s: {' '.join(command)}")
#             return 124, "", f"Timeout after {timeout}s"
#         except Exception as e:
#             self.logger.warning(f"Command failed: {' '.join(command)}: {str(e)}")
#             return 1, "", str(e)
            
#     def _command_exists(self, command: str) -> bool:
#         """Check if a command exists on the system with The Hamsters' diligence"""
#         try:
#             code, _, _ = self._run_command(["which", command], timeout=1)
#             return code == 0
#         except Exception:
#             return False

#     def _get_network_usage(self) -> Dict[str, Any]:
#         """Get detailed network usage metrics - Sir Hawkington's comprehensive network analysis"""
#         try:
#             # Initialize the network data structure
#             network_data = {}
            
#             # The Quantum Shadow People's Basic Network Stats
#             network_data.update(self._get_basic_network_stats())
            
#             # Sir Hawkington's Network Connections Registry
#             network_data["connections"] = self._get_network_connections()
            
#             # The Hamsters' Interface Configuration Management
#             interfaces, interface_stats = self._get_network_interfaces()
#             network_data["interfaces"] = interfaces
#             network_data["interface_stats"] = interface_stats
            
#             # The Meth Snail's Protocol Distribution Analysis
#             network_data["protocol_breakdown"] = self._get_protocol_breakdown()
            
#             # The Stick's Connection Quality Assessment
#             cached, data = self._check_cache('connection_quality')
#             if cached:
#                 network_data["connection_quality"] = data
#             else:
#                 network_data["connection_quality"] = self._get_connection_quality()
#                 self._update_cache('connection_quality', network_data["connection_quality"])
            
#             # The Quantum Shadow People's DNS Intelligence
#             cached, data = self._check_cache('dns_metrics')
#             if cached:
#                 network_data["dns_metrics"] = data
#             else:
#                 network_data["dns_metrics"] = self._get_dns_metrics()
#                 self._update_cache('dns_metrics', network_data["dns_metrics"])
            
#             # The Meth Snail's Internet Connectivity Analysis
#             cached, data = self._check_cache('internet_metrics')
#             if cached:
#                 network_data["internet_metrics"] = data
#             else:
#                 network_data["internet_metrics"] = self._get_internet_metrics()
#                 self._update_cache('internet_metrics', network_data["internet_metrics"])
            
#             return network_data
            
#         except Exception as e:
#             self.logger.error(f"Network metric error: {str(e)}") 
#             # Return minimal structure on error - Sir Hawkington's emergency fallback
#             return {
#                 "io_stats": {
#                     "bytes_sent": 0,
#                     "bytes_recv": 0,
#                     "sent_rate": 0,
#                     "recv_rate": 0,
#                     "bytes_sent_formatted": "0 B",
#                     "bytes_recv_formatted": "0 B"
#                 },
#                 "total_usage_mb": 0.0
#             }

#     def _get_basic_network_stats(self) -> Dict[str, Any]:
#         """Get basic network I/O stats - The Quantum Shadow People's domain"""
#         try:
#             net_io = psutil.net_io_counters()
#             current_time = time.time()
#             uptime = max(1, current_time - psutil.boot_time())  # Avoid division by zero
            
#             # Calculate rates based on uptime (long-term average)
#             sent_rate_avg = net_io.bytes_sent / uptime
#             recv_rate_avg = net_io.bytes_recv / uptime
            
#             # Calculate instantaneous rates if we have previous measurements
#             if self._last_net_io and self._last_net_io_time:
#                 time_delta = current_time - self._last_net_io_time
#                 if time_delta > 0:  # Avoid division by zero
#                     sent_rate = (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_delta
#                     recv_rate = (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_delta
#                 else:
#                     sent_rate = sent_rate_avg
#                     recv_rate = recv_rate_avg
#             else:
#                 sent_rate = sent_rate_avg
#                 recv_rate = recv_rate_avg
            
#             # Update last values for next calculation
#             self._last_net_io = net_io
#             self._last_net_io_time = current_time
            
#             # Calculate total rates
#             total_rate = sent_rate + recv_rate
            
#             return {
#                 "io_stats": {
#                     "bytes_sent": net_io.bytes_sent,
#                     "bytes_recv": net_io.bytes_recv,
#                     "packets_sent": net_io.packets_sent,
#                     "packets_recv": net_io.packets_recv,
#                     "errin": net_io.errin,
#                     "errout": net_io.errout,
#                     "dropin": net_io.dropin,
#                     "dropout": net_io.dropout,
#                     "sent_rate": sent_rate,
#                     "recv_rate": recv_rate,
#                     "total_rate": total_rate,
#                     "bytes_sent_formatted": self._format_bytes(net_io.bytes_sent),
#                     "bytes_recv_formatted": self._format_bytes(net_io.bytes_recv),
#                     "sent_rate_formatted": f"{self._format_bytes(sent_rate)}/s",
#                     "recv_rate_formatted": f"{self._format_bytes(recv_rate)}/s",
#                     "total_rate_formatted": f"{self._format_bytes(total_rate)}/s"
#                 },
#                 "total_usage_mb": (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024
#             }
#         except Exception as e:
#             self.logger.error(f"Error getting basic network stats: {str(e)}")
#             return {
#                 "io_stats": {
#                     "bytes_sent": 0,
#                     "bytes_recv": 0,
#                     "sent_rate": 0,
#                     "recv_rate": 0,
#                     "bytes_sent_formatted": "0 B",
#                     "bytes_recv_formatted": "0 B",
#                     "total_rate_formatted": "0 B/s"
#                 },
#                 "total_usage_mb": 0.0
#             }

#     def _get_network_connections(self) -> List[Dict[str, Any]]:
#         """Get network connections - Sir Hawkington's connection registry"""
#         connections = []
#         try:
#             for conn in psutil.net_connections(kind='inet'):
#                 try:
#                     # Format addresses with The Stick's precision
#                     laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
#                     raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
                    
#                     # Get process name with The Hamsters' diligence
#                     process_name = "Unknown"
#                     if conn.pid:
#                         try:
#                             process = psutil.Process(conn.pid)
#                             process_name = process.name()
#                         except (psutil.NoSuchProcess, psutil.AccessDenied):
#                             pass
                    
#                     # Add connection to the registry
#                     connections.append({
#                         "type": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
#                         "laddr": laddr,
#                         "raddr": raddr,
#                         "status": conn.status,
#                         "pid": conn.pid,
#                         "process_name": process_name
#                     })
#                 except Exception as e:
#                     self.logger.debug(f"Error processing connection: {str(e)}")
#                     continue
#         except (psutil.AccessDenied, PermissionError) as e:
#             self.logger.warning(f"Permission denied when accessing network connections: {str(e)}")
#         except Exception as e:
#             self.logger.error(f"Error collecting network connections: {str(e)}")
        
#         return connections

#     def _get_network_interfaces(self) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
#         """Get network interfaces and stats - The Hamsters' domain"""
#         # Check if we have cached interface data
#         cached, data = self._check_cache('interfaces')
#         if cached:
#             return data

#         interfaces = []
#         interface_stats = {}
        
#         try:
#             # Get network interfaces
#             net_if_addrs = psutil.net_if_addrs()
#             net_if_stats = psutil.net_if_stats()
#             net_io_counters = psutil.net_io_counters(pernic=True)
            
#             # Process each interface with The Hamsters' thoroughness
#             for name, addrs in net_if_addrs.items():
#                 try:
#                     # Extract addresses
#                     ip_address = None
#                     mac_address = None
#                     for addr in addrs:
#                         if addr.family == socket.AF_INET:
#                             ip_address = addr.address
#                         elif addr.family == psutil.AF_LINK:
#                             mac_address = addr.address
                    
#                     # Get interface stats
#                     is_up = False
#                     speed = 0
#                     mtu = 0
#                     if name in net_if_stats:
#                         is_up = net_if_stats[name].isup
#                         speed = net_if_stats[name].speed
#                         mtu = net_if_stats[name].mtu
                    
#                     # Add interface to list
#                     interfaces.append({
#                         "name": name,
#                         "address": ip_address,
#                         "mac_address": mac_address,
#                         "isup": is_up,
#                         "speed": speed,
#                         "mtu": mtu
#                     })
                    
#                     # Get interface I/O stats
#                     if name in net_io_counters:
#                         counter = net_io_counters[name]
#                         interface_stats[name] = {
#                             "bytes_sent": counter.bytes_sent,
#                             "bytes_recv": counter.bytes_recv,
#                             "packets_sent": counter.packets_sent,
#                             "packets_recv": counter.packets_recv,
#                             "errin": counter.errin,
#                             "errout": counter.errout,
#                             "dropin": counter.dropin,
#                             "dropout": counter.dropout
#                         }
#                 except Exception as e:
#                     self.logger.debug(f"Error processing interface {name}: {str(e)}")
#                     continue
            
#             # Cache the results for future use
#             result = (interfaces, interface_stats)
#             self._update_cache('interfaces', result)
#             return result
            
#         except Exception as e:
#             self.logger.error(f"Error collecting interface info: {str(e)}")
#             return [], {}

#     def _get_protocol_breakdown(self) -> Dict[str, int]:
#         """Get protocol breakdown from connections - The Meth Snail's specialty"""
#         protocol_counts = {"tcp": 0, "udp": 0, "http": 0, "https": 0, "dns": 0}
        
#         try:
#             # Count TCP/UDP from connections
#             for conn in psutil.net_connections(kind='inet'):
#                 try:
#                     if conn.type == socket.SOCK_STREAM:
#                         protocol_counts["tcp"] += 1
#                         # Check for HTTP/HTTPS based on port
#                         if hasattr(conn, 'raddr') and conn.raddr:
#                             if conn.raddr.port == 80:
#                                 protocol_counts["http"] += 1
#                             elif conn.raddr.port == 443:
#                                 protocol_counts["https"] += 1
#                         if hasattr(conn, 'laddr') and conn.laddr:
#                             if conn.laddr.port == 80:
#                                 protocol_counts["http"] += 1
#                             elif conn.laddr.port == 443:
#                                 protocol_counts["https"] += 1
#                     elif conn.type == socket.SOCK_DGRAM:
#                         protocol_counts["udp"] += 1
#                         # Check for DNS based on port
#                         if (hasattr(conn, 'raddr') and conn.raddr and conn.raddr.port == 53) or \
#                            (hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == 53):
#                             protocol_counts["dns"] += 1
#                 except (AttributeError, Exception) as e:
#                     continue
            
#             # Calculate percentages
#             total_connections = sum(protocol_counts.values())
#             if total_connections > 0:
#                 return {k: int((v / total_connections) * 100) for k, v in protocol_counts.items()}
            
#             # Ensure at least 1% for visualization
#             for protocol in protocol_counts:
#                 protocol_counts[protocol] = max(1, protocol_counts[protocol])
                
#             return protocol_counts
            
#         except Exception as e:
#             self.logger.error(f"Error collecting protocol breakdown: {str(e)}")
#             # Return minimal protocol data
#             return {"tcp": 60, "udp": 20, "http": 10, "https": 5, "dns": 5}
 

#     def _get_connection_quality(self) -> Dict[str, Any]:
#         """Get connection quality metrics - The Stick's domain of precise measurements"""
#         # Default values in case something goes wrong
#         quality_data = {
#             "average_latency": 0,
#             "min_latency": 0,
#             "max_latency": 0,
#             "jitter": 0,
#             "packet_loss_percent": 0,
#             "connection_stability": 0,
#             "overall_score": 0
#         }
        
#         # The Stick only proceeds with ping if it's available
#         if not self._command_exists('ping'):
#             self.logger.warning("The Stick is dismayed: ping command not found for connection quality assessment")
#             return quality_data
            
#         try:
#             # The Stick selects distinguished targets for quality assessment
#             targets = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
#             latencies = []
#             packet_loss = 0
#             ping_count = 3
            
#             # The Stick methodically tests each target
#             for target in targets:
#                 try:
#                     code, stdout, _ = self._run_command(
#                         ["ping", "-c", str(ping_count), "-W", "1", target],
#                         timeout=5
#                     )
                    
#                     # Extract latency from ping output
#                     if code == 0:
#                         # Parse ping output to get min/avg/max/mdev
#                         stats_line = stdout.strip().split("\n")[-1]
#                         if "min/avg/max" in stats_line:
#                             # Extract values from line like: rtt min/avg/max/mdev = 20.442/22.129/25.427/1.987 ms
#                             values = stats_line.split("=")[1].strip().split("/")
#                             latencies.append({
#                                 "min": float(values[0]),
#                                 "avg": float(values[1]),
#                                 "max": float(values[2]),
#                                 "mdev": float(values[3].split()[0])  # Remove 'ms' suffix
#                             })
                        
#                         # Check for packet loss with The Stick's unparalleled attention to detail
#                         for line in stdout.strip().split("\n"):
#                             if "packet loss" in line:
#                                 loss_pct = float(line.split("%")[0].split()[-1])
#                                 packet_loss += loss_pct / len(targets)
#                                 break
#                 except Exception as e:
#                     self.logger.debug(f"The Stick is disappointed: Ping to {target} failed: {str(e)}")
#                     packet_loss += 100 / len(targets)  # Count as 100% loss for this target
            
#             # The Stick calculates aggregate metrics with mathematical precision
#             if latencies:
#                 min_latency = min(l["min"] for l in latencies)
#                 max_latency = max(l["max"] for l in latencies)
#                 avg_latency = sum(l["avg"] for l in latencies) / len(latencies)
#                 jitter = sum(l["mdev"] for l in latencies) / len(latencies)
                
#                 # The Stick's proprietary stability algorithm
#                 stability = max(0, 100 - (packet_loss * 0.8) - (jitter * 2))
                
#                 # The Stick's holistic quality assessment
#                 overall_score = max(0, 100 - (avg_latency * 0.5) - (packet_loss * 0.8) - (jitter * 2))
                
#                 quality_data = {
#                     "average_latency": round(avg_latency, 1),
#                     "min_latency": round(min_latency, 1),
#                     "max_latency": round(max_latency, 1),
#                     "jitter": round(jitter, 1),
#                     "packet_loss_percent": round(packet_loss, 2),
#                     "connection_stability": round(stability, 1),
#                     "overall_score": round(overall_score, 1)
#                 }
            
#         except Exception as e:
#             self.logger.error(f"The Stick has encountered a regulatory violation: {str(e)}")
            
#         return quality_data

#     def _get_dns_metrics(self) -> Dict[str, Any]:
#         """Get DNS metrics - The Quantum Shadow People's reconnaissance mission"""
#         # Default DNS metrics for The Quantum Shadow People's baseline
#         dns_data = {
#             "query_time_ms": 0,
#             "success_rate": 0,
#             "cache_hit_ratio": 0,
#             "last_failures": 0
#         }
        
#         # The Quantum Shadow People only proceed if dig is available
#         if not self._command_exists('dig'):
#             self.logger.warning("The Quantum Shadow People cannot find 'dig' tool for DNS metrics")
#             return dns_data
            
#         try:
#             # The Quantum Shadow People's target DNS infrastructure
#             dns_servers = ["8.8.8.8", "1.1.1.1"]
#             domains = ["google.com", "github.com", "amazon.com"]
#             query_times = []
#             success_count = 0
#             total_queries = len(dns_servers) * len(domains)
            
#             # The Quantum Shadow People perform interdimensional DNS queries
#             for server in dns_servers:
#                 for domain in domains:
#                     try:
#                         code, stdout, stderr = self._run_command(
#                             ["dig", "@"+server, domain, "+stats", "+noall", "+answer"],
#                             timeout=3
#                         )
                        
#                         # The Quantum Shadow People validate query success
#                         if code == 0 and stdout.strip():
#                             success_count += 1
                            
#                             # Extract query time with quantum precision
#                             output = stdout + stderr  # Combine outputs to check both
#                             for line in output.strip().split("\n"):
#                                 if "Query time:" in line:
#                                     time_ms = float(line.split(":")[1].strip().split()[0])
#                                     query_times.append(time_ms)
#                                     break
#                     except Exception as e:
#                         self.logger.debug(f"The Quantum Shadow People's DNS query to {server} for {domain} failed: {str(e)}")
            
#             # The Quantum Shadow People calculate metrics with probabilistic uncertainty
#             if query_times:
#                 avg_query_time = sum(query_times) / len(query_times)
#             else:
#                 avg_query_time = 0
                
#             success_rate = success_count / total_queries if total_queries > 0 else 0
            
#             # The Quantum Shadow People's cache hit ratio estimation
#             cache_hit_ratio = 0.5  # Quantum default state
#             if len(query_times) >= 2:
#                 # Sort query times and compare first half vs second half
#                 sorted_times = sorted(query_times)
#                 half = len(sorted_times) // 2
#                 if half > 0:
#                     first_half_avg = sum(sorted_times[:half]) / half
#                     second_half_avg = sum(sorted_times[half:]) / (len(sorted_times) - half)
#                     if first_half_avg > 0:
#                         # Quantum entanglement formula for cache ratio
#                         time_ratio = second_half_avg / first_half_avg
#                         cache_hit_ratio = max(0, min(1, 1 - time_ratio))
            
#             dns_data = {
#                 "query_time_ms": round(avg_query_time, 1),
#                 "success_rate": round(success_rate, 2),
#                 "cache_hit_ratio": round(cache_hit_ratio, 2),
#                 "last_failures": total_queries - success_count
#             }
            
#         except Exception as e:
#             self.logger.error(f"The Quantum Shadow People's dimensional rift encountered an anomaly: {str(e)}")
            
#         return dns_data

#     def _get_internet_metrics(self) -> Dict[str, Any]:
#         """Get internet connectivity metrics - The Meth Snail's cosmic journey"""
#         # The Meth Snail's baseline internet metrics
#         internet_data = {
#             "gateway_latency_ms": 0,
#             "internet_latency_ms": 0,
#             "hop_count": 0,
#             "isp_performance_score": 0
#         }
        
#         try:
#             # The Meth Snail searches for the network gateway
#             gateway_ip = self._get_default_gateway()
            
#             # The Meth Snail measures gateway latency with cosmic precision
#             gateway_latency = 0
#             if gateway_ip:
#                 code, stdout, _ = self._run_command(
#                     ["ping", "-c", "3", "-W", "1", gateway_ip],
#                     timeout=3
#                 )
#                 if code == 0:
#                     # Extract average latency from the cosmic ping
#                     for line in stdout.strip().split("\n"):
#                         if "min/avg/max" in line:
#                             try:
#                                 gateway_latency = float(line.split("/")[1])
#                                 break
#                             except (ValueError, IndexError):
#                                 pass
            
#             # The Meth Snail travels the cosmic internet
#             internet_targets = ["google.com", "cloudflare.com"]
#             internet_latencies = []
            
#             for target in internet_targets:
#                 code, stdout, _ = self._run_command(
#                     ["ping", "-c", "3", "-W", "2", target],
#                     timeout=6
#                 )
#                 if code == 0:
#                     for line in stdout.strip().split("\n"):
#                         if "min/avg/max" in line:
#                             try:
#                                 avg_latency = float(line.split("/")[1])
#                                 internet_latencies.append(avg_latency)
#                                 break
#                             except (ValueError, IndexError):
#                                 pass
            
#             # The Meth Snail calculates average internet latency
#             internet_latency = sum(internet_latencies) / len(internet_latencies) if internet_latencies else 0
            
#             # The Meth Snail counts hops in the cosmic traceroute
#             hop_count = 0
#             if self._command_exists('traceroute'):
#                 code, stdout, _ = self._run_command(
#                     ["traceroute", "-m", "15", "-w", "1", "-q", "1", "google.com"],
#                     timeout=10
#                 )
#                 if code == 0:
#                     # Count non-empty lines excluding the first header line
#                     lines = [l for l in stdout.strip().split("\n") if l and not l.startswith("traceroute")]
#                     hop_count = len(lines)
            
#             # The Meth Snail's cosmic ISP performance formula
#             isp_score = 100  # Start at cosmic perfection
#             if gateway_latency > 0:
#                 # The Meth Snail's gateway latency penalty
#                 isp_score -= min(30, gateway_latency * 3)
            
#             if internet_latency > 0:
#                 # The Meth Snail's internet latency penalty
#                 isp_score -= min(40, (internet_latency - 20) / 2)
            
#             if hop_count > 0:
#                 # The Meth Snail's hop count penalty
#                 isp_score -= min(20, max(0, hop_count - 8) * 2)
            
#             # The Meth Snail ensures the score stays within the cosmic range
#             isp_score = max(0, min(100, isp_score))
            
#             internet_data = {
#                 "gateway_latency_ms": round(gateway_latency, 1),
#                 "internet_latency_ms": round(internet_latency, 1),
#                 "hop_count": hop_count,
#                 "isp_performance_score": round(isp_score)
#             }
            
#         except Exception as e:
#             self.logger.error(f"The Meth Snail's cosmic journey was interrupted: {str(e)}")
            
#         return internet_data

#     def _get_default_gateway(self) -> Optional[str]:
#         """Get the default gateway IP - The Meth Snail's router discovery"""
#         gateway_ip = None
#         try:
#             # The Meth Snail uses standard commands for router discovery
#             if self._command_exists('ip'):
#                 code, stdout, _ = self._run_command(
#                     ["ip", "route", "show", "default"],
#                     timeout=2
#                 )
#                 if code == 0:
#                     route_output = stdout.strip()
#                     if route_output:
#                         # Parse output like: default via 192.168.1.1 dev wlp2s0 proto dhcp metric 600
#                         parts = route_output.split()
#                         if len(parts) > 2 and parts[0] == "default" and parts[1] == "via":
#                             gateway_ip = parts[2]
            
#             # The Meth Snail has alternative methods for router discovery
#             if not gateway_ip and self._command_exists('route'):
#                 code, stdout, _ = self._run_command(
#                     ["route", "-n"],
#                     timeout=2
#                 )
#                 if code == 0:
#                     for line in stdout.strip().split('\n'):
#                         if line.startswith('0.0.0.0'):
#                             parts = line.split()
#                             if len(parts) >= 2:
#                                 gateway_ip = parts[1]
#                                 break
                    
#         except Exception as e:
#             self.logger.warning(f"The Meth Snail couldn't find the default gateway: {str(e)}")
            
#         return gateway_ip

#     async def _get_additional_metrics(self) -> Dict:
#         """Get additional system metrics - The Hamsters' supplementary research"""
#         try:
#             # The Hamsters diligently collect additional system insights
#             return {
#                 'swap_usage': psutil.swap_memory().percent,
#                 'cpu_temperature': self._get_cpu_temperature(),
#                 'active_python_processes': self._count_python_processes(),
#                 'load_average': self._get_load_average(),
#                 'uptime': self._get_system_uptime()
#             }
#         except Exception as e:
#             self.logger.error(f"The Hamsters encountered a metrics collection issue: {str(e)}")
#             return {}

#     def _get_cpu_temperature(self) -> Optional[float]:
#         """Get CPU temperature if available - Sir Hawkington's thermal oversight"""
#         try:
#             # Sir Hawkington checks various temperature sensors
#             temps = psutil.sensors_temperatures()
            
#             # Check for common temperature sensor names across platforms
#             for sensor_name in ['coretemp', 'k10temp', 'cpu_thermal', 'acpitz']:
#                 if temps and sensor_name in temps and temps[sensor_name]:
#                     # Return the first core's temperature
#                     return temps[sensor_name][0].current
                    
#             # Sir Hawkington couldn't find temperature sensors
#             return None
#         except Exception as e:
#             self.logger.debug(f"Sir Hawkington's thermal monocle malfunctioned: {str(e)}")
#             return None

#     def _count_python_processes(self) -> int:
#         """Count number of Python processes - The Meth Snail's python census"""
#         try:
#             # The Meth Snail carefully counts all python processes
#             python_count = 0
#             for p in psutil.process_iter(['name', 'cmdline']):
#                 try:
#                     # Check if 'python' appears in the process name
#                     if 'python' in p.info['name'].lower():
#                         python_count += 1
#                     # Also check command line for python interpreters
#                     elif p.info['cmdline'] and any('python' in cmd.lower() for cmd in p.info['cmdline']):
#                         python_count += 1
#                 except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
#                     # The Meth Snail methodically ignores vanishing processes
#                     continue
                    
#             return python_count
#         except Exception as e:
#             self.logger.debug(f"The Meth Snail's python census was disrupted: {str(e)}")
#             return 0

#     def _get_load_average(self) -> List[float]:
#         """Get system load average - The Quantum Shadow People's workload analysis"""
#         try:
#             # The Quantum Shadow People analyze system load
#             # Normalize by CPU count to get per-core load
#             cpu_count = psutil.cpu_count() or 1  # Avoid division by zero
#             return [x / cpu_count * 100 for x in psutil.getloadavg()]
#         except Exception as e:
#             self.logger.debug(f"The Quantum Shadow People's load analysis failed: {str(e)}")
#             return [0.0, 0.0, 0.0]
            
#     def _get_system_uptime(self) -> int:
#         """Get system uptime in seconds - The Hamsters' uptime chronometer"""
#         try:
#             # The Hamsters measure system uptime with precision
#             return int(time.time() - psutil.boot_time())
#         except Exception as e:
#             self.logger.debug(f"The Hamsters' chronometer malfunctioned: {str(e)}")
#             return 0

#     async def start_monitoring(self):
#         """Start continuous monitoring - Sir Hawkington begins his watch"""
#         self.logger.info("Sir Hawkington commences the distinguished monitoring vigil")
#         self.is_monitoring = True
#         while self.is_monitoring:
#             try:
#                 await self.collect_metrics()
#             except Exception as e:
#                 self.logger.error(f"Sir Hawkington's monitoring encountered an anomaly: {str(e)}")
                
#             # Sir Hawkington waits patiently between metric collections
#             await asyncio.sleep(self.monitoring_interval)

#     async def stop_monitoring(self):
#         """Stop monitoring - Sir Hawkington retires to his perch"""
#         self.logger.info("Sir Hawkington gracefully concludes his monitoring duties")
#         self.is_monitoring = False

#     async def get_status(self) -> Dict:
#         """Get current monitoring status - The Meth Snail's status report"""
#         # The Meth Snail delivers a detailed status report
#         status = {
#             'is_monitoring': self.is_monitoring,
#             'last_update': self.last_metrics['timestamp'] if self.last_metrics else None,
#             'monitoring_interval': self.monitoring_interval,
#             'cache_size': len(self._cache),
#             'system_uptime': self._get_system_uptime(),
#         }
        
#         # Add monitoring duration if active
#         if self.is_monitoring and self.last_metrics and 'timestamp' in self.last_metrics:
#             start_time = self.last_metrics['timestamp']
#             if isinstance(start_time, datetime):
#                 status['monitoring_duration'] = (datetime.now() - start_time).total_seconds()
        
#         return status

#     async def cleanup(self):
#         """Cleanup monitor resources - The farewell ceremony"""
#         self.logger.info("Resource Monitor powering down... *sad beep*")
#         self.logger.info("Sir Hawkington hangs up his aristocratic monitoring monocle")
#         self.logger.info("The Meth Snail retreats to the cosmic void of system hibernation")
#         self.is_monitoring = False
#         self._cache.clear()


#OLD CODE
# # core/optimization/resource_monitor.py

# import psutil
# from typing import Dict, Any, List, Optional
# from datetime import datetime
# import asyncio
# import logging  
# import socket
# import time
# import subprocess
# from functools import lru_cache
# from collections import Counter


# class ResourceMonitor:
#     """
#     System Resource Monitor
    
#     Watches your system resources like a hawk... 
#     if hawks were interested in CPU usage and had a thing for metrics.
    
#     Warning: May cause sudden urges to optimize everything in sight.
#     """

#     def __init__(self):
#         self.logger = logging.getLogger('ResourceMonitor')
#         self.is_monitoring = False
#         self.monitoring_interval = 5  # seconds
#         self.last_metrics: Optional[Dict] = None

#     async def initialize(self):
#         """Initialize the monitor (boot up the surveillance)"""
#         self.logger.info("Resource Monitor powering up... beep boop")
#         self.is_monitoring = False
#         self.last_metrics = None

#     async def collect_metrics(self) -> Dict:
#         """Collect current system metrics"""
#         try:
#             process_count = len(list(psutil.process_iter()))

#             # Debug log before collecting network metrics
#             self.logger.info("About to collect network metrics")
#             network_data = self._get_network_usage()
#             self.logger.info(f"Network metrics collected: {network_data.keys()}")

#             metrics = {
#                 'timestamp': datetime.now(),
#                 'cpu_usage': await self._get_cpu_usage(),
#                 'memory_usage': self._get_memory_usage(),
#                 'disk_usage': self._get_disk_usage(),
#                 'network': network_data,
#                 'process_count': process_count,
#                 'additional': await self._get_additional_metrics()
#             }
            
#             # Debug log final metrics structure
#             self.logger.info(f"Final metrics structure keys: {metrics.keys()}")
#             self.logger.info(f"Network data included: {'network' in metrics}")
            
#             self.last_metrics = metrics
#             return metrics

#         except Exception as e:
#             self.logger.error(f"Error collecting metrics: {str(e)}")
#             raise
    
#     async def _get_cpu_usage(self) -> float:
#         """Get CPU usage percentage"""
#         try:
#             # CPU usage needs a small interval to calculate
#             return psutil.cpu_percent(interval=1)
#         except Exception as e:
#             self.logger.error(f"CPU metric error: {str(e)}")
#             return 0.0

#     def _get_memory_usage(self) -> float:
#         """Get memory usage percentage"""
#         try:
#             return psutil.virtual_memory().percent
#         except Exception as e:
#             self.logger.error(f"Memory metric error: {str(e)}")
#             return 0.0

#     def _get_disk_usage(self) -> float:
#         """Get disk usage percentage"""
#         try:
#             return psutil.disk_usage('/').percent
#         except Exception as e:
#             self.logger.error(f"Disk metric error: {str(e)}")
#             return 0.0

#     def _get_network_usage(self) -> Dict[str, Any]:
#         """Get detailed network usage metrics"""
#         try:
#             # Get basic network I/O stats
#             net_io = psutil.net_io_counters()
            
#             # Format bytes for display (helper function)
#             def format_bytes(bytes_value):
#                 for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
#                     if bytes_value < 1024:
#                         return f"{bytes_value:.2f} {unit}"
#                     bytes_value /= 1024
#                 return f"{bytes_value:.2f} PB"
        
#             # Build a structured response with all the network data
#             network_data = {
#                 "io_stats": {
#                     "bytes_sent": net_io.bytes_sent,
#                     "bytes_recv": net_io.bytes_recv,
#                     "packets_sent": net_io.packets_sent,
#                     "packets_recv": net_io.packets_recv,
#                     "errin": net_io.errin,
#                     "errout": net_io.errout,
#                     "dropin": net_io.dropin,
#                     "dropout": net_io.dropout,
#                     # Calculate rates (simple estimation)
#                     "sent_rate": net_io.bytes_sent / (time.time() - psutil.boot_time()),
#                     "recv_rate": net_io.bytes_recv / (time.time() - psutil.boot_time()),
#                     # Formatted values for display
#                     "bytes_sent_formatted": format_bytes(net_io.bytes_sent),
#                     "bytes_recv_formatted": format_bytes(net_io.bytes_recv),
#                 }
#             }
        
#             # Add the simplified total for backward compatibility 
#             network_data["total_usage_mb"] = (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024
        
#             # Try to get network connections (will be empty if permission denied)
#             try:
#                 connections = []
#                 for conn in psutil.net_connections(kind='inet'):
#                     if conn.laddr:
#                         laddr = f"{conn.laddr.ip}:{conn.laddr.port}"
#                     else:
#                         laddr = "N/A"
                        
#                     if conn.raddr:
#                         raddr = f"{conn.raddr.ip}:{conn.raddr.port}"
#                     else:
#                         raddr = "N/A"
                    
#                     # Get process name if possible
#                     process_name = "Unknown"
#                     if conn.pid:
#                         try:
#                             process = psutil.Process(conn.pid)
#                             process_name = process.name()
#                         except (psutil.NoSuchProcess, psutil.AccessDenied):
#                             pass
                    
#                     connections.append({
#                         "type": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
#                         "laddr": laddr,
#                         "raddr": raddr,
#                         "status": conn.status,
#                         "pid": conn.pid,
#                         "process_name": process_name
#                     })
                
#                 network_data["connections"] = connections
#             except (psutil.AccessDenied, PermissionError):
#                 # Handle permission issues gracefully
#                 network_data["connections"] = []
#                 self.logger.warning("Permission denied when accessing network connections")
            
#             # Try to get network interfaces
#             try:
#                 interfaces = []
#                 for name, stats in psutil.net_if_stats().items():
#                     # Get addresses for this interface
#                     addresses = psutil.net_if_addrs().get(name, [])
#                     ip_address = None
#                     mac_address = None
                    
#                     for addr in addresses:
#                         if addr.family == socket.AF_INET:
#                             ip_address = addr.address
#                         elif addr.family == psutil.AF_LINK:
#                             mac_address = addr.address
                    
#                     interfaces.append({
#                         "name": name,
#                         "address": ip_address,
#                         "mac_address": mac_address,
#                         "isup": stats.isup,
#                         "speed": stats.speed,
#                         "mtu": stats.mtu
#                     })
                
#                 network_data["interfaces"] = interfaces
                
#                 # Interface statistics
#                 interface_stats = {}
#                 for name, stats in psutil.net_io_counters(pernic=True).items():
#                     interface_stats[name] = {
#                         "bytes_sent": stats.bytes_sent,
#                         "bytes_recv": stats.bytes_recv,
#                         "packets_sent": stats.packets_sent,
#                         "packets_recv": stats.packets_recv,
#                         "errin": stats.errin,
#                         "errout": stats.errout,
#                         "dropin": stats.dropin,
#                         "dropout": stats.dropout
#                     }
                
#                 network_data["interface_stats"] = interface_stats
#             except Exception as e:
#                 self.logger.error(f"Error collecting interface info: {str(e)}")
#                 network_data["interfaces"] = []
#                 network_data["interface_stats"] = {}
            
#             # Get actual protocol breakdown from connections
#             try:
#                 protocol_counts = {"tcp": 0, "udp": 0, "http": 0, "https": 0, "dns": 0}
                
#                 # Count TCP/UDP from connections
#                 for conn in psutil.net_connections(kind='inet'):
#                     if conn.type == socket.SOCK_STREAM:
#                         protocol_counts["tcp"] += 1
#                         # Check for HTTP/HTTPS based on port
#                         if conn.raddr and conn.raddr.port == 80:
#                             protocol_counts["http"] += 1
#                         elif conn.raddr and conn.raddr.port == 443:
#                             protocol_counts["https"] += 1
#                         elif conn.laddr and conn.laddr.port == 80:
#                             protocol_counts["http"] += 1
#                         elif conn.laddr and conn.laddr.port == 443:
#                             protocol_counts["https"] += 1
#                     elif conn.type == socket.SOCK_DGRAM:
#                         protocol_counts["udp"] += 1
#                         # Check for DNS based on port
#                         if (conn.raddr and conn.raddr.port == 53) or (conn.laddr and conn.laddr.port == 53):
#                             protocol_counts["dns"] += 1
                
#                 # Convert to percentages
#                 total_connections = sum(protocol_counts.values())
#                 if total_connections > 0:
#                     network_data["protocol_breakdown"] = {
#                         k: int((v / total_connections) * 100) for k, v in protocol_counts.items()
#                     }
#                 else:
#                     network_data["protocol_breakdown"] = {k: 0 for k in protocol_counts}
#             except Exception as e:
#                 self.logger.error(f"Error collecting protocol breakdown: {str(e)}")
#                 network_data["protocol_breakdown"] = {"tcp": 0, "udp": 0, "http": 0, "https": 0, "dns": 0}
            
#             # Get actual connection quality data using ping
#             try:
#                 # Use ping to measure latency to common DNS servers
#                 targets = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
#                 latencies = []
#                 packet_loss = 0
#                 ping_count = 3
                
#                 for target in targets:
#                     try:
#                         # Run ping command with timeout
#                         ping_result = subprocess.run(
#                             ["ping", "-c", str(ping_count), "-W", "1", target],
#                             capture_output=True,
#                             text=True,
#                             timeout=5
#                         )
                        
#                         # Extract latency from ping output
#                         if ping_result.returncode == 0:
#                             # Parse ping output to get min/avg/max/mdev
#                             stats_line = ping_result.stdout.strip().split("\n")[-1]
#                             if "min/avg/max" in stats_line:
#                                 # Extract values from line like: rtt min/avg/max/mdev = 20.442/22.129/25.427/1.987 ms
#                                 values = stats_line.split("=")[1].strip().split("/")
#                                 latencies.append({
#                                     "min": float(values[0]),
#                                     "avg": float(values[1]),
#                                     "max": float(values[2]),
#                                     "mdev": float(values[3].split()[0])  # Remove 'ms' suffix
#                                 })
                            
#                             # Check for packet loss
#                             for line in ping_result.stdout.strip().split("\n"):
#                                 if "packet loss" in line:
#                                     loss_pct = float(line.split("%")[0].split()[-1])
#                                     packet_loss += loss_pct / len(targets)
#                                     break
#                     except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
#                         self.logger.warning(f"Ping to {target} failed: {str(e)}")
#                         packet_loss += 100 / len(targets)  # Count as 100% loss for this target
                
#                 # Calculate aggregate metrics
#                 if latencies:
#                     min_latency = min(l["min"] for l in latencies)
#                     max_latency = max(l["max"] for l in latencies)
#                     avg_latency = sum(l["avg"] for l in latencies) / len(latencies)
#                     jitter = sum(l["mdev"] for l in latencies) / len(latencies)
                    
#                     # Calculate stability and overall score
#                     # Lower packet loss and jitter = higher stability
#                     stability = max(0, 100 - (packet_loss * 0.8) - (jitter * 2))
                    
#                     # Overall score based on latency, stability and packet loss
#                     overall_score = max(0, 100 - (avg_latency * 0.5) - (packet_loss * 0.8) - (jitter * 2))
                    
#                     network_data["connection_quality"] = {
#                         "average_latency": round(avg_latency, 1),
#                         "min_latency": round(min_latency, 1),
#                         "max_latency": round(max_latency, 1),
#                         "jitter": round(jitter, 1),
#                         "packet_loss_percent": round(packet_loss, 2),
#                         "connection_stability": round(stability, 1),
#                         "overall_score": round(overall_score, 1)
#                     }
#                 else:
#                     # Fallback if no ping data available
#                     network_data["connection_quality"] = {
#                         "average_latency": 0,
#                         "min_latency": 0,
#                         "max_latency": 0,
#                         "jitter": 0,
#                         "packet_loss_percent": packet_loss,
#                         "connection_stability": max(0, 100 - packet_loss),
#                         "overall_score": max(0, 100 - packet_loss)
#                     }
#             except Exception as e:
#                 self.logger.error(f"Error collecting connection quality: {str(e)}")
#                 network_data["connection_quality"] = {
#                     "average_latency": 0,
#                     "min_latency": 0,
#                     "max_latency": 0,
#                     "jitter": 0,
#                     "packet_loss_percent": 0,
#                     "connection_stability": 0,
#                     "overall_score": 0
#                 }
            
#             # Get actual DNS metrics using dig
#             try:
#                 dns_servers = ["8.8.8.8", "1.1.1.1"]
#                 domains = ["google.com", "github.com", "amazon.com"]
#                 query_times = []
#                 success_count = 0
#                 total_queries = len(dns_servers) * len(domains)
                
#                 for server in dns_servers:
#                     for domain in domains:
#                         try:
#                             # Use dig to query DNS with timing
#                             dig_result = subprocess.run(
#                                 ["dig", "@"+server, domain, "+stats", "+noall", "+answer"],
#                                 capture_output=True,
#                                 text=True,
#                                 timeout=3
#                             )
                            
#                             # Check if query was successful
#                             if dig_result.returncode == 0 and dig_result.stdout.strip():
#                                 success_count += 1
                                
#                                 # Try to extract query time
#                                 for line in dig_result.stderr.strip().split("\n") + dig_result.stdout.strip().split("\n"):
#                                     if "Query time:" in line:
#                                         time_ms = float(line.split(":")[1].strip().split()[0])
#                                         query_times.append(time_ms)
#                                         break
#                         except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
#                             self.logger.warning(f"DNS query to {server} for {domain} failed: {str(e)}")
                
#                 # Calculate metrics
#                 if query_times:
#                     avg_query_time = sum(query_times) / len(query_times)
#                 else:
#                     avg_query_time = 0
                    
#                 success_rate = success_count / total_queries if total_queries > 0 else 0
                
#                 # Estimate cache hit ratio by comparing first and second query times
#                 # This is a rough approximation
#                 cache_hit_ratio = 0.5  # Default fallback
#                 if len(query_times) >= 2:
#                     # Sort query times and compare first half vs second half
#                     # If caching is working, second queries should be faster
#                     sorted_times = sorted(query_times)
#                     half = len(sorted_times) // 2
#                     if half > 0:
#                         first_half_avg = sum(sorted_times[:half]) / half
#                         second_half_avg = sum(sorted_times[half:]) / (len(sorted_times) - half)
#                         if first_half_avg > 0:
#                             # Calculate ratio based on time difference
#                             time_ratio = second_half_avg / first_half_avg
#                             cache_hit_ratio = max(0, min(1, 1 - time_ratio))
                
#                 network_data["dns_metrics"] = {
#                     "query_time_ms": round(avg_query_time, 1),
#                     "success_rate": round(success_rate, 2),
#                     "cache_hit_ratio": round(cache_hit_ratio, 2),
#                     "last_failures": total_queries - success_count
#                 }
#             except Exception as e:
#                 self.logger.error(f"Error collecting DNS metrics: {str(e)}")
#                 network_data["dns_metrics"] = {
#                     "query_time_ms": 0,
#                     "success_rate": 0,
#                     "cache_hit_ratio": 0,
#                     "last_failures": 0
#                 }
            
#             # Get actual internet metrics
#             try:
#                 # Get default gateway
#                 gateway_ip = None
#                 try:
#                     # Try to get default gateway using 'ip route' command
#                     route_cmd = subprocess.run(
#                         ["ip", "route", "show", "default"],
#                         capture_output=True,
#                         text=True,
#                         timeout=2
#                     )
#                     if route_cmd.returncode == 0:
#                         route_output = route_cmd.stdout.strip()
#                         if route_output:
#                             # Parse output like: default via 192.168.1.1 dev wlp2s0 proto dhcp metric 600
#                             parts = route_output.split()
#                             if len(parts) > 2 and parts[0] == "default" and parts[1] == "via":
#                                 gateway_ip = parts[2]
#                 except Exception as e:
#                     self.logger.warning(f"Failed to get default gateway: {str(e)}")
                
#                 # Measure gateway latency
#                 gateway_latency = 0
#                 if gateway_ip:
#                     try:
#                         ping_result = subprocess.run(
#                             ["ping", "-c", "3", "-W", "1", gateway_ip],
#                             capture_output=True,
#                             text=True,
#                             timeout=3
#                         )
#                         if ping_result.returncode == 0:
#                             # Extract average latency
#                             for line in ping_result.stdout.strip().split("\n"):
#                                 if "min/avg/max" in line:
#                                     gateway_latency = float(line.split("/")[1])
#                                     break
#                     except Exception as e:
#                         self.logger.warning(f"Failed to ping gateway: {str(e)}")
                
#                 # Measure internet latency (average of google.com and cloudflare.com)
#                 internet_targets = ["google.com", "cloudflare.com"]
#                 internet_latencies = []
                
#                 for target in internet_targets:
#                     try:
#                         ping_result = subprocess.run(
#                             ["ping", "-c", "3", "-W", "2", target],
#                             capture_output=True,
#                             text=True,
#                             timeout=6
#                         )
#                         if ping_result.returncode == 0:
#                             for line in ping_result.stdout.strip().split("\n"):
#                                 if "min/avg/max" in line:
#                                     avg_latency = float(line.split("/")[1])
#                                     internet_latencies.append(avg_latency)
#                                     break
#                     except Exception as e:
#                         self.logger.warning(f"Failed to ping {target}: {str(e)}")
                
#                 internet_latency = sum(internet_latencies) / len(internet_latencies) if internet_latencies else 0
                
#                 # Calculate hop count
#                 hop_count = 0
#                 try:
#                     # Use traceroute to count hops to google.com
#                     traceroute_result = subprocess.run(
#                         ["traceroute", "-m", "15", "-w", "1", "-q", "1", "google.com"],
#                         capture_output=True,
#                         text=True,
#                         timeout=10
#                     )
#                     if traceroute_result.returncode == 0:
#                         # Count non-empty lines excluding the first header line
#                         lines = [l for l in traceroute_result.stdout.strip().split("\n") if l and not l.startswith("traceroute")]
#                         hop_count = len(lines)
#                 except Exception as e:
#                     self.logger.warning(f"Failed to run traceroute: {str(e)}")
                
#                 # Calculate ISP performance score
#                 # Based on gateway latency, internet latency and hop count
#                 isp_score = (gateway_latency + internet_latency + hop_count) / 3
#                 if gateway_latency > 0:
#                     # Penalize high gateway latency (should be < 5ms ideally)
#                     isp_score -= min(30, gateway_latency * 3)
                
#                 if internet_latency > 0:
#                     # Penalize high internet latency (> 100ms is poor)
#                     isp_score -= min(40, (internet_latency - 20) / 2)
                
#                 if hop_count > 0:
#                     # Penalize excessive hops (> 15 is poor)
#                     isp_score -= min(20, max(0, hop_count - 8) * 2)
                
#                 # Ensure score is between 0-100
#                 isp_score = max(0, min(100, isp_score))
                
#                 network_data["internet_metrics"] = {
#                     "gateway_latency_ms": round(gateway_latency, 1),
#                     "internet_latency_ms": round(internet_latency, 1),
#                     "hop_count": hop_count,
#                     "isp_performance_score": round(isp_score)
#                 }
#             except Exception as e:
#                 self.logger.error(f"Error collecting internet metrics: {str(e)}")
#                 network_data["internet_metrics"] = {
#                     "gateway_latency_ms": 0,
#                     "internet_latency_ms": 0,
#                     "hop_count": 0,
#                     "isp_performance_score": 0
#                 }
            
#             return network_data
            
#         except Exception as e:
#             self.logger.error(f"Network metric error: {str(e)}") 
#             return {
#                 "io_stats": {
#                     "bytes_sent": 0,
#                     "bytes_recv": 0,
#                     "sent_rate": 0,
#                     "recv_rate": 0,
#                     "bytes_sent_formatted": "0 B",
#                     "bytes_recv_formatted": "0 B"
#                 },
#                 "total_usage_mb": 0.0
#             }
    
#     async def _get_additional_metrics(self) -> Dict:
#         """Get additional system metrics"""
#         try:
#             return {
#                 'swap_usage': psutil.swap_memory().percent,
#                 'cpu_temperature': self._get_cpu_temperature(),
#                 'active_python_processes': self._count_python_processes(),
#                 'load_average': self._get_load_average()
#             }
#         except Exception as e:
#             self.logger.error(f"Additional metrics error: {str(e)}")
#             return {}
    
#     def _get_cpu_temperature(self) -> Optional[float]:
#         """Get CPU temperature if available"""
#         try:
#             temps = psutil.sensors_temperatures()
#             if temps and 'coretemp' in temps:
#                 return temps['coretemp'][0].current
#             return None
#         except Exception:
#             return None
    
#     def _count_python_processes(self) -> int:
#         """Count number of Python processes"""
#         try:
#             return len([p for p in list(psutil.process_iter(['name'])) 
#                    if 'python' in p.info['name'].lower()])
#         except Exception:
#             return 0
    
#     def _get_load_average(self) -> list:
#         """Get system load average"""
#         try:
#             return [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()]
#         except Exception:
#             return [0, 0, 0]
    
#     async def start_monitoring(self):
#         """Start continuous monitoring"""
#         self.is_monitoring = True
#         while self.is_monitoring:
#             await self.collect_metrics()
#             await asyncio.sleep(self.monitoring_interval)

#     async def stop_monitoring(self):
#         """Stop monitoring"""
#         self.is_monitoring = False

#     async def get_status(self) -> Dict:
#         """Get current monitoring status"""
#         return {
#             'is_monitoring': self.is_monitoring,
#             'last_update': self.last_metrics['timestamp'] if self.last_metrics else None,
#             'monitoring_interval': self.monitoring_interval
#         }

#     async def cleanup(self):
#         """Cleanup monitor resources"""
#         self.logger.info("Resource Monitor powering down... *sad beep*")
#         self.is_monitoring = False