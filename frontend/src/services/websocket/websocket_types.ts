// src/types/websocket.types.ts

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface WebSocketMessage {
  type: 'cpu_metrics' | 'memory_metrics' | 'disk_metrics' | 'network_metrics' | 'error' | 'connection_established' | 'system_info' | 'all_metrics';
  data?: any;
  timestamp?: string;
  message?: string;
}

export interface CircuitBreakerConfig {
  failureThreshold: number;
  resetTimeout: number;
  monitoringPeriod: number;
}

export interface RateLimiterConfig {
  maxRequests: number;
  windowMs: number;
}

export interface BackpressureConfig {
  maxQueueSize: number;
  dropStrategy: 'oldest' | 'newest';
}

export interface CircuitBreakerState {
  isOpen: boolean;
  failures: number;
  lastFailure: number | null;
  nextRetry: number | null;
}