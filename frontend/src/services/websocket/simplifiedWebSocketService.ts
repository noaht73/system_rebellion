import { store } from '../../store/store';
import { updateCPUMetrics, CPUMetric } from '../../store/slices/metrics/CPUSlice';
import { updateDiskMetrics, DiskMetric } from '../../store/slices/metrics/DiskSlice';

// --- Inferred Type Definitions ---
// NOTE: These types are inferred based on usage and error messages.
// They should ideally be defined in and imported from './websocket_types.ts'.

export interface AuthenticationRequest {
  type: 'auth';
  authenticationToken: string;
}

export type WebSocketMessageType =
  | 'auth_success'
  | 'auth_failed'
  | 'cpu_metrics'
  | 'disk_metrics'
  | 'connection_established'
  | 'system_info';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  payload: any;
}

// --- Type Guards ---

function isCPUMetric(payload: any): payload is CPUMetric {
  return (
    payload &&
    typeof payload.usage_percent === 'number' &&
    typeof payload.physical_cores === 'number' &&
    typeof payload.logical_cores === 'number' &&
    Array.isArray(payload.cores) &&
    Array.isArray(payload.top_processes)
  );
}

function isDiskMetric(payload: any): payload is DiskMetric {
  return (
    payload &&
    typeof payload.percent === 'number' &&
    typeof payload.total === 'number' &&
    typeof payload.used === 'number' &&
    Array.isArray(payload.partitions) &&
    typeof payload.io_counters === 'object' &&
    payload.io_counters !== null
  );
}

// --- WebSocket Service ---

const WEBSOCKET_URL_BASE = 'ws://localhost:8000/ws/system-metrics';
const RECONNECT_DELAY_MS = 5000;
const HEARTBEAT_INTERVAL_MS = 30000;

class WebSocketService {
  private socket: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private authToken: string | null = null;

  // Public callbacks for consumers to hook into
  public onOpen: () => void = () => {};
  public onClose: (event: CloseEvent) => void = () => {};
  public onError: (error: Error) => void = () => {};

  public connect(token: string | null) {
    this.authToken = token;
    if (!this.authToken) {
      this.handleError(new Error('Authentication token is missing.'));
      return;
    }

    if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
      console.log('WebSocket is already connecting, open, or closing.');
      return;
    }

    const clientId = `web-${Math.random().toString(36).substring(2, 9)}`;
    const url = `${WEBSOCKET_URL_BASE}/${clientId}?token=${this.authToken}`;
    this.socket = new WebSocket(url);

    this.socket.onopen = this.handleOpen;
    this.socket.onmessage = this.handleMessage;
    this.socket.onclose = this.handleClose;
    this.socket.onerror = (event) => this.handleError(new Error('WebSocket error occurred.'), event);
  }

  public disconnect() {
    console.log('Disconnecting WebSocket.');
    this.stopHeartbeat();
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.socket) {
      this.socket.onclose = null; // Prevent handleClose from triggering reconnect
      this.socket.close(1000, 'Client initiated disconnect.');
      this.socket = null;
    }
  }

  private handleOpen = () => {
    console.log('WebSocket connection established.');
    if (this.reconnectTimeout) {
        clearTimeout(this.reconnectTimeout);
        this.reconnectTimeout = null;
    }
    const authMessage: AuthenticationRequest = { type: 'auth', authenticationToken: this.authToken! };
    this.sendMessage(authMessage);
    this.startHeartbeat();
    this.onOpen(); // Trigger public callback
  };

  private handleMessage = (event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);

      switch (message.type) {
        case 'auth_success':
          console.log('Authentication successful.');
          break;

        case 'auth_failed':
          console.error('Authentication failed:', message.payload);
          this.handleError(new Error(message.payload?.error || 'Authentication Failed'));
          this.disconnect();
          break;

        case 'cpu_metrics':
          if (isCPUMetric(message.payload)) {
            store.dispatch(updateCPUMetrics(message.payload));
          } else {
            console.error('Invalid CPU metric payload:', message.payload);
          }
          break;

        case 'disk_metrics':
          if (isDiskMetric(message.payload)) {
            store.dispatch(updateDiskMetrics(message.payload));
          } else {
            console.error('Invalid Disk metric payload:', message.payload);
          }
          break;

        case 'connection_established':
          console.log('Connection established message received.');
          break;

        case 'system_info':
          console.log('System info received:', message.payload);
          break;

        default:
          console.warn('Received unhandled message type:', message.type);
      }
    } catch (error) {
      console.error('Error processing WebSocket message:', error);
      this.handleError(new Error('Failed to parse incoming message.'));
    }
  };

  private handleClose = (event: CloseEvent) => {
    console.log(`WebSocket connection closed: ${event.code} - ${event.reason}`);
    this.stopHeartbeat();
    this.onClose(event); // Trigger public callback

    if (event.code !== 1000) {
      this.scheduleReconnect();
    }
  };

  private handleError = (error: Error, event?: Event) => {
    console.error('WebSocket Error:', error, event || '');
    this.onError(error); // Trigger public callback
  };

  private scheduleReconnect = () => {
    if (this.reconnectTimeout) return; // Already scheduled
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect(this.authToken);
    }, RECONNECT_DELAY_MS);
  };

  private sendMessage = (message: object) => {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      console.error('Cannot send message, WebSocket is not open.');
    }
  };

  private startHeartbeat = () => {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      this.sendMessage({ type: 'heartbeat' });
    }, HEARTBEAT_INTERVAL_MS);
  };

  private stopHeartbeat = () => {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  };
}

export const webSocketService = new WebSocketService();
