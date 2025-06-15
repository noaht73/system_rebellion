// src/types/metrics.ts
import { CPUData } from '../components/metrics/CPU/Tabs/types';
// Base metric type for individual readings
export interface NetworkDetails {
  // Legacy properties for backward compatibility
  bytes_sent: number;
  bytes_recv: number;
  packets_sent: number;
  packets_recv: number;
  rate_mbps: number;
  sent_rate_bps?: number;
  recv_rate_bps?: number;
  raw_bytes_total?: number;
  
  // Enhanced network metrics
  io_stats?: {
    bytes_sent: number;
    bytes_recv: number;
    packets_sent: number;
    packets_recv: number;
    sent_rate: number;
    recv_rate: number;
    errors_in: number;
    errors_out: number;
    drops_in: number;
    drops_out: number;
  };
  
  connection_quality?: {
    average_latency: number;
    packet_loss_percent: number;
    connection_stability: number;
    jitter: number;
    gateway_latency: number;
    dns_latency: number;
    internet_latency: number;
  };
  
  protocol_stats?: {
    tcp: {
      active: number;
      listening?: number;
      established: number;
      time_wait?: number;
      close_wait?: number;
      fin_wait1?: number;
      fin_wait2?: number;
      last_ack?: number;
      syn_sent?: number;
      syn_recv?: number;
      closing?: number;
    };
    udp: {
      active: number;
      datagrams_sent?: number;
      datagrams_received?: number;
    };
    http: {
      connections: number;
      get_requests?: number;
      post_requests?: number;
    };
    https: {
      connections: number;
      tls_handshakes?: number;
    };
    dns: {
      queries: number;
      responses?: number;
      timeouts?: number;
    };
  };
  
  protocol_breakdown?: {
    web: number;
    email: number;
    streaming: number;
    gaming: number;
    file_transfer: number;
    other: number;
  };
  
  top_bandwidth_processes?: Array<{
    name: string;
    pid: number;
    read_rate?: number;
    write_rate?: number;
    total_rate?: number;
    connection_count?: number;
  }>;
  
  interfaces?: Array<{
    name: string;
    address?: string;
    mac_address?: string;
    isup: boolean;
    speed?: number;
    mtu?: number;
    bytes_sent?: number;
    bytes_recv?: number;
  }>;
  
  dns_metrics?: {
    query_time_ms: number;
    success_rate: number;
    cache_hit_ratio: number;
  };
  
  internet_metrics?: {
    connected: boolean;
    download_speed: number;
    upload_speed: number;
    isp_latency: number;
  };
}

export interface AdditionalMetrics {
  swap_usage?: number;
  cpu_temperature?: number;
  active_python_processes?: number;
  load_average?: number[];
  network_details?: NetworkDetails;
  [key: string]: any;
}

// Type for optimization profile thresholds
interface ThresholdLevels {
  warning: number;
  critical: number;
  normal: number;
  high: number;
  low: number;
  medium: number;
  very_high: number;
  very_low: number;
  
}

export interface MetricThresholds {
  cpu: ThresholdLevels;
  memory: ThresholdLevels;
  disk: ThresholdLevels;
  network: ThresholdLevels;
  timestamp?: string;
}

export interface SystemMetric {
  id: string;
  user_id: string;
  cpu_usage: number;
  cpu_temperature?: number;
  cpu_frequency?: number;
  cpu_core_count?: number;
  cpu_thread_count?: number;
  cpu_model?: string;
  cpu_vendor?: string;
  cpu_cache?: number;
  cpu_cache_size?: number;
  cpu_cache_lines?: number;
  cpu_cache_type?: string;
  cpu_cache_level?: number;
  cpu_cache_associativity?: number;
  cpu_cache_line_size?: number;
  cpu_cache_line_count?: number;
  cpu_cache_line_associativity?: number;
  cpu: CPUData;
  memory_usage: number;
  memory_allocation: number;
  memory_total: number;
  memory_available: number;
  memory_free: number;
  memory_buffer: number;
  memory_cache: number;
  memory_swap: number;
  memory_swap_total: number;
  memory_swap_free: number;
  memory_swap_used: number;
  memory_swap_percent: number;
  memory_percent: number;
  disk_usage: number;
  disk_total: number;
  disk_available: number;
  disk_free: number;
  disk_used: number;
  disk_percent: number;
  network_usage?: number;
  network_total: number;
  network_available: number;
  network_free: number;
  network_used: number;
  network_percent: number;
  network?: NetworkDetails;
  process_count: number;
  timestamp: string;
  additional_metrics?: Record<string, any>;
  additional?: AdditionalMetrics;
}
  
// Type for metric alerts
export enum AlertSeverity {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

export interface MetricAlert {
  id: string;
  metric_type: 'cpu' | 'memory' | 'disk' | 'network';
  type: 'usage' | 'temperature' | 'memory' | 'disk' | 'network' | 'bandwidth' | 'connections';
  severity: AlertSeverity;
  threshold: number;
  current_value: number;
  timestamp: string;
  message: string;
}

export type IntervalID = NodeJS.Timeout;

export interface MetricsState {
  metrics: SystemMetric[];
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
  useWebSocket: boolean;
  connectionStatus: 'disconnected' | 'connecting' | 'connected';
  lastUpdate: number | null;
}

// Type for historical data
export interface HistoricalMetrics {
  data: SystemMetric[];
  start_time: string;
  end_time: string;
  interval: number;
}

// Response types from API
export interface SystemMetricsResponse {
  data: SystemMetric;
  alerts: MetricAlert[];
}

// Request types for API
export interface MetricsQueryParams {
  start_time?: string;
  end_time?: string;
  interval?: number;
  limit?: number;
}

// Optimization types
export interface OptimizationResult {
  id: string;
  timestamp: string;
  metrics_before: SystemMetric;
  metrics_after: SystemMetric;
  actions_taken: string[];
  success: boolean;
}

export interface OptimizationProfiles {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  usage_type: string;
  thresholds:{
    cpu_threshold: number;
    memory_threshold: number;
    disk_threshold: number;
    network_threshold: number;
    enable_auto_tuning: boolean;
    // Advanced settings
    cpu_priority?: 'high' | 'medium' | 'low';
    background_process_limit?: number;
    memory_allocation?: {
      applications: number; // percentage
      system_cache: number; // percentage
    };
    actions: {
      cpu: string[];
      memory: string[];
      disk: string[];
      network: string[];
    };
    disk_performance?: 'speed' | 'balance' | 'powersave';
    network_optimization?: {
      prioritize_streaming: boolean;
      prioritize_downloads: boolean;
      low_latency_mode: boolean;
    };
    power_profile?: 'performance' | 'balanced' | 'powersave';
  };
}

export interface MetricsApiResponse {
  data: SystemMetric;
  timestamp: string;
}

// System alert interface
export interface SystemAlert {
  id: string;
  timestamp: string;
  title: string;
  message: string;
  severity: AlertSeverity;
}

// Auto tuner interfaces
export interface AutoTunerState {
  uuid: string;
  user: string;
  status: string;
  success: boolean;
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

export interface AutoTunerApiResponse {
  uuid: string;
  user: string;
  status: string;
  success: boolean;
  timestamp: string;
}

export interface AutoTunerAlert {
  id: string;
  metric_type: 'cpu' | 'memory' | 'disk' | 'network';
  severity: AlertSeverity;
  threshold: number;
  current_value: number;
  timestamp: string;
  message: string;
}

export interface AutoTunerAlertState {
  alerts: AutoTunerAlert[];
  loading: boolean;
  error: string | null;
}