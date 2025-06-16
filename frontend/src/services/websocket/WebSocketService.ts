// src/services/websocket/WebSocketService.ts
import { 
  WebSocketMessage, 
  ConnectionStatus, 
  CircuitBreakerConfig,
  RateLimiterConfig,
  BackpressureConfig,
  CircuitBreakerState
} from './websocket_types';

// Built-in Circuit Breaker
class CircuitBreaker {
  private failures = 0;
  private lastFailure: number | null = null;
  private state: 'closed' | 'open' | 'half-open' = 'closed';
  
  constructor(private config: CircuitBreakerConfig) {
    // Load state from localStorage if available
    const savedState = localStorage.getItem('websocket_circuit_breaker');
    if (savedState) {
      try {
        const parsed = JSON.parse(savedState);
        this.failures = parsed.failures || 0;
        this.lastFailure = parsed.lastFailure || null;
        this.state = parsed.state || 'closed';
      } catch (e) {
        console.error('Failed to parse circuit breaker state');
      }
    }
  }
  
  canAttemptConnection(): boolean {
    if (this.state === 'closed') return true;
    
    if (this.state === 'open' && this.lastFailure) {
      const timeSinceFailure = Date.now() - this.lastFailure;
      if (timeSinceFailure > this.config.resetTimeout) {
        this.state = 'half-open';
        return true;
      }
    }
    
    return this.state === 'half-open';
  }
  
  recordSuccess(): void {
    this.failures = 0;
    this.lastFailure = null;
    this.state = 'closed';
    this.saveState();
  }
  
  recordFailure(): void {
    this.failures++;
    this.lastFailure = Date.now();
    
    if (this.failures >= this.config.failureThreshold) {
      this.state = 'open';
      console.warn(`Circuit breaker opened after ${this.failures} failures`);
    }
    
    this.saveState();
  }
  
  getWaitTimeSeconds(): number {
    if (!this.lastFailure) return 0;
    const elapsed = Date.now() - this.lastFailure;
    const remaining = Math.max(0, this.config.resetTimeout - elapsed);
    return Math.ceil(remaining / 1000);
  }
  
  reset(): void {
    this.failures = 0;
    this.lastFailure = null;
    this.state = 'closed';
    localStorage.removeItem('websocket_circuit_breaker');
  }
  
  getState(): CircuitBreakerState {
    return {
      isOpen: this.state === 'open',
      failures: this.failures,
      lastFailure: this.lastFailure,
      nextRetry: this.lastFailure ? this.lastFailure + this.config.resetTimeout : null
    };
  }
  
  private saveState(): void {
    localStorage.setItem('websocket_circuit_breaker', JSON.stringify({
      failures: this.failures,
      lastFailure: this.lastFailure,
      state: this.state
    }));
  }
}

// Built-in Rate Limiter
class RateLimiter {
  private requests: number[] = [];
  
  constructor(private config: RateLimiterConfig) {}
  
  checkLimit(): boolean {
    const now = Date.now();
    this.requests = this.requests.filter(time => now - time < this.config.windowMs);
    
    if (this.requests.length < this.config.maxRequests) {
      this.requests.push(now);
      return true;
    }
    
    return false;
  }
  
  recordRejection(): void {
    console.warn('Rate limit exceeded');
  }
}

// Built-in Backpressure Handler
class BackpressureHandler {
  private queue: any[] = [];
  
  constructor(private config: BackpressureConfig) {}
  
  canProcess(): boolean {
    return this.queue.length < this.config.maxQueueSize;
  }
  
  recordProcessed(): void {
  }
  
  addToQueue(item: any): void {
    if (this.queue.length >= this.config.maxQueueSize) {
      if (this.config.dropStrategy === 'oldest') {
        this.queue.shift();
      } else {
        return; // Drop newest
      }
    }
    this.queue.push(item);
  }
}

export class WebSocketService {
  private socket: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private isAuthenticated: boolean = false;
  private connectionStatus: ConnectionStatus = 'disconnected';
  
  // Event handlers
  public onMessage: ((message: WebSocketMessage) => void) | null = null;
  public onConnectionStatusChange: ((status: ConnectionStatus) => void) | null = null;
  public onError: ((error: Error) => void) | null = null;
  private lastToken: string | null = null; // For reconnection
  
  // Resilience components
  private circuitBreaker: CircuitBreaker;
  private rateLimiter: RateLimiter;
  private backpressureHandler: BackpressureHandler;
  
  // Configuration
  private readonly reconnectDelay = 5000;
  private readonly heartbeatInterval_ms = 30000;
  private readonly maxReconnectAttempts = 5;
  private reconnectAttempts = 0;
  
  constructor() {
    console.log('🦔 Sir Hawkington Von Monitorious III at your service!');
    
    this.circuitBreaker = new CircuitBreaker({
      failureThreshold: 5,
      resetTimeout: 60000,
      monitoringPeriod: 120000
    });
    
    this.rateLimiter = new RateLimiter({
      maxRequests: 100,
      windowMs: 60000
    });
    
    this.backpressureHandler = new BackpressureHandler({
      maxQueueSize: 1000,
      dropStrategy: 'oldest'
    });
  }
  
  // Get the WebSocket URL (NO TOKEN!)
  private buildWebSocketUrl(token: string): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NODE_ENV === 'development' 
      ? 'localhost:8000' 
      : window.location.host;
    const clientId = this.getClientId();
    // Append the token as a query parameter for authentication
    const url = `${protocol}//${host}/ws/system-metrics/${clientId}?token=${encodeURIComponent(token)}`;
    console.log(`🦔 Generated WebSocket URL with token: ${url}`);
    return url;
  }

  private getClientId(): string {
    let clientId = localStorage.getItem('ws_client_id');
    if (!clientId) {
      clientId = `client_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
      localStorage.setItem('ws_client_id', clientId);
    }
    return clientId;
  }
  
  // Main connection method
  public async connect(token: string | null): Promise<void> {
    this.lastToken = token;
    if (this.socket?.readyState === WebSocket.OPEN || 
        this.socket?.readyState === WebSocket.CONNECTING) {
      console.log('🦔 Already connected or connecting, dear chap!');
      return;
    }
    
    if (!this.circuitBreaker.canAttemptConnection()) {
      const waitTime = this.circuitBreaker.getWaitTimeSeconds();
      throw new Error(`🦔 Circuit breaker is open! Please wait ${waitTime} seconds.`);
    }
    
    try {
      if (!token) {
      console.error('🚨 [WebSocketService] Connection attempt failed: No auth token provided.');
      this.updateConnectionStatus('error');
      // Do not attempt to reconnect if there's no token.
      return;
    }

    const url = this.buildWebSocketUrl(token);
      console.log('🦔 Establishing WebSocket connection...');
      
      this.socket = new WebSocket(url);
      this.setupEventListeners();
      this.updateConnectionStatus('connecting');
      
    } catch (error) {
      console.error('🦔 Connection failed:', error);
      this.circuitBreaker.recordFailure();
      this.updateConnectionStatus('error');
      this.scheduleReconnect();
      throw error;
    }
  }
  
  private setupEventListeners(): void {
    if (!this.socket) return;
    
    // Connection opened - wait for connection_established message before auth
    this.socket.onopen = this.onOpen;
    
    // Handle messages from server
    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log('🦔 Received message:', message.type, message);
        
        switch (message.type) {
          case 'connection_established':
            console.log('🦔 Connection established!');
            break;
            
          case 'auth_failed':
            console.error('🚨 Authentication failed:', message.message);
            this.circuitBreaker.recordFailure();
            this.socket?.close();
            break;
            
          case 'metrics_update':
            this.handleMetricsUpdate(message);
            break;
            
          case 'system_info':
            console.log('📊 System info received:', message.data);
            break;
            
          case 'error':
            console.error('🚨 Server error:', message.message);
            break;
            
          case 'pong':
            console.log('🏓 Pong received');
            break;

          case 'heartbeat':
            console.log('💓 Heartbeat received');
            this.send(JSON.stringify({ type: 'pong' }));
            break;
            
          default:
            console.log('🦔 Unknown message type:', message.type);
        }
      } catch (error) {
        console.error('🚨 Error parsing WebSocket message:', error);
      }
    };
    
    // Connection closed
    this.socket.onclose = (event) => {
      console.log('🦔 WebSocket closed:', event.code, event.reason);
      this.isAuthenticated = false;
      this.stopHeartbeat();
      
      if (event.code === 1000) {
        // Normal closure
        this.updateConnectionStatus('disconnected');
      } else {
        // Abnormal closure
        this.updateConnectionStatus('error');
        this.circuitBreaker.recordFailure();
        this.scheduleReconnect();
      }
    };
    
    // Connection error
    this.socket.onerror = (event) => {
      console.error('🦔 WebSocket error:', event);
      this.onError?.(new Error('WebSocket connection error'));
    };
  }
  
  private onOpen = (): void => {
    console.log('✅ WebSocket connection opened and authenticated via URL token');
    this.updateConnectionStatus('connected');
    this.isAuthenticated = true;
    this.reconnectAttempts = 0;
    this.circuitBreaker.recordSuccess();
    this.startHeartbeat(); // Start heartbeat after successful authentication
  }
  
  private handleMetricsUpdate(message: any): void {
    console.log('🔄 [WebSocketService] Processing metrics update:', message);
    console.log('🔍 [WebSocketService] Message type:', typeof message);
    console.log('🔍 [WebSocketService] Message keys:', Object.keys(message));
    
    if (!this.backpressureHandler.canProcess()) {
      console.warn('🦔 [WebSocketService] Backpressure - dropping metrics update');
      return;
    }
    
    // Get the metrics data from the message
    // The backend sends a single message with all metrics nested under keys
    const metricsData = message.data || message;
    console.log('🔍 [WebSocketService] MetricsData keys:', Object.keys(metricsData));
    
    // Enhanced debugging - log the metrics data structure
    console.log('🔍 [WebSocketService] FULL METRICS DATA STRUCTURE:', JSON.stringify(metricsData, null, 2));
    
    // CPU metrics - the detailed CPU data is directly under the 'cpu' key
    if (metricsData.cpu) {
      console.log('✅ [WebSocketService] Found CPU data:', metricsData.cpu);
      console.log('🔍 [WebSocketService] CPU data structure:', JSON.stringify(metricsData.cpu, null, 2));
      console.log('🚀 [WebSocketService] Dispatching cpu_metrics with data:', metricsData.cpu);
      this.onMessage?.({
        type: 'cpu_metrics',
        data: metricsData.cpu
      });
    } else {
      console.log('❌ [WebSocketService] No CPU data found in metricsData');
      console.log('🔍 [WebSocketService] Available keys in metricsData:', Object.keys(metricsData));
    }
    
    // Memory metrics - the detailed memory data is directly under the 'memory' key
    if (metricsData.memory) {
      console.log('✅ [WebSocketService] Found Memory data:', metricsData.memory);
      console.log('🔍 [WebSocketService] Memory data structure:', JSON.stringify(metricsData.memory, null, 2));
      console.log('🚀 [WebSocketService] Dispatching memory_metrics with data:', metricsData.memory);
      this.onMessage?.({
        type: 'memory_metrics',
        data: metricsData.memory
      });
    } else {
      console.log('❌ [WebSocketService] No Memory data found in metricsData');
    }
    
    // Disk metrics - the detailed disk data is directly under the 'disk' key
    if (metricsData.disk) {
      console.log('✅ [WebSocketService] Found Disk data:', metricsData.disk);
      console.log('🔍 [WebSocketService] Disk data structure:', JSON.stringify(metricsData.disk, null, 2));
      console.log('🚀 [WebSocketService] Dispatching disk_metrics with data:', metricsData.disk);
      this.onMessage?.({
        type: 'disk_metrics',
        data: metricsData.disk
      });
    } else {
      console.log('❌ [WebSocketService] No Disk data found in metricsData');
    }
    
    // Network metrics - the detailed network data is directly under the 'network' key
    if (metricsData.network) {
      console.log('✅ [WebSocketService] Found Network data:', metricsData.network);
      console.log('🔍 [WebSocketService] Network data structure:', JSON.stringify(metricsData.network, null, 2));
      console.log('🚀 [WebSocketService] Dispatching network_metrics with data:', metricsData.network);
      this.onMessage?.({
        type: 'network_metrics',
        data: metricsData.network
      });
    } else {
      console.log('❌ [WebSocketService] No Network data found in metricsData');
    }
    
    this.backpressureHandler.recordProcessed();
  }
  
  // Send a message
  public send(message: any): void {
    if (!this.isAuthenticated) {
      console.warn('🦔 Cannot send message - not authenticated!');
      return;
    }
    
    if (this.socket?.readyState !== WebSocket.OPEN) {
      console.warn('🦔 Cannot send message - WebSocket not open');
      return;
    }
    
    if (!this.rateLimiter.checkLimit()) {
      console.warn('🦔 Rate limit exceeded!');
      return;
    }
    
    try {
      const messageStr = typeof message === 'string' 
        ? message 
        : JSON.stringify(message);
      
      this.socket.send(messageStr);
    } catch (error) {
      console.error('🦔 Error sending message:', error);
    }
  }
  
  // Heartbeat management
  private startHeartbeat(): void {
    this.stopHeartbeat();
    
    this.heartbeatInterval = setInterval(() => {
      if (this.isAuthenticated && this.socket?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, this.heartbeatInterval_ms);
  }
  
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
  
  // Reconnection logic
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('🦔 Max reconnection attempts reached!');
      return;
    }
    
    const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts);
    console.log(`🦔 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect(this.lastToken).catch(error => {
        console.error('🦔 Reconnection failed:', error);
      });
    }, delay);
  }
  
  // Connection status management
  private updateConnectionStatus(status: ConnectionStatus): void {
    this.connectionStatus = status;
    this.onConnectionStatusChange?.(status);
  }
  
  // Public methods
  public disconnect(): void {
    console.log('🦔 Disconnecting WebSocket...');
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    this.stopHeartbeat();
    this.isAuthenticated = false;
    
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
    }
    
    this.updateConnectionStatus('disconnected');
  }
  
  public getConnectionState(): ConnectionStatus {
    return this.connectionStatus;
  }
  
  public isConnected(): boolean {
    return this.isAuthenticated && 
           this.socket !== null && 
           this.socket.readyState === WebSocket.OPEN;
  }
  
  public resetCircuitBreaker(): void {
    console.log('🦔 Resetting circuit breaker...');
    this.circuitBreaker.reset();
  }
  
  public getCircuitBreakerState(): CircuitBreakerState {
    return this.circuitBreaker.getState();
  }
  
  // Request interval change
  public requestIntervalChange(seconds: number): void {
    if (!this.isAuthenticated) return;
    
    this.send({
      type: 'set_interval',
      interval: Math.max(1, Math.min(10, seconds))
    });
  }
  
  // Request system info
  public requestSystemInfo(): void {
    if (!this.isAuthenticated) return;
    
    this.send({
      type: 'request_system_info'
    });
  }
}

// Singleton export
let wsInstance: WebSocketService | null = null;

export const initWebSocket = (_dispatch: unknown): WebSocketService => {
  if (!wsInstance) {
    console.log('🦔 Initializing WebSocket service...');
        wsInstance = new WebSocketService();
  }
  return wsInstance;
};

export const getWebSocketInstance = (): WebSocketService | null => {
  return wsInstance;
};