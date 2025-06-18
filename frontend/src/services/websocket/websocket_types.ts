// src/types/websocket.types.ts

export enum ConnectionStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  ERROR = 'error',
}

// Requests from client
export interface AuthenticationRequest {
  type: 'auth';
  authenticationToken: string;
}

export interface GetMetricsRequest {
  type: 'get_metrics';
  requestedMetrics: Array<'cpu' | 'memory' | 'disk' | 'network'>;
}

export interface SetIntervalRequest {
    type: 'set_interval';
    payload: { seconds: number };
}

export interface GetSystemInfoRequest {
    type: 'get_system_info';
}

export interface PingRequest {
    type: 'ping';
}

export type ClientToServerMessage = AuthenticationRequest | GetMetricsRequest | SetIntervalRequest | GetSystemInfoRequest | PingRequest;

// Messages from server
export interface AllMetricsMessage {
  type: 'all_metrics';
  payload: Record<string, unknown>;
}

export interface CircuitBreakerMessage {
    type: 'circuit_breaker';
    payload: {
        status: 'open' | 'closed' | 'half-open';
        failures: number;
        lastFailureTime: number | null;
        nextRetryTime: number | null;
    };
}

export interface WebSocketMessage {
  type: WebSocketMessageType;
  payload?: unknown;
  timestamp?: string;
}

export type WebSocketMessageType =
  | 'cpu_metrics'
  | 'memory_metrics'
  | 'disk_metrics'
  | 'network_metrics'
  | 'all_metrics'
  | 'error'
  | 'connection_established'
  | 'system_info'
  | 'auth_failed'
  | 'auth_success'
  | 'heartbeat'
  | 'pong'
  | 'circuit_breaker';

export interface CircuitBreakerConfig {
  maxFailures: number;
  resetTimeoutMs: number;
  monitoringIntervalMs: number;
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
  failureCount: number;
  lastFailureTime: number | null;
  nextRetryTime: number | null;
}