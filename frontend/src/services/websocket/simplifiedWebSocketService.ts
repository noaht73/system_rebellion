import { AuthenticationRequest, WebSocketMessage } from './websocket_types';
const WEBSOCKET_URL_BASE = 'ws://localhost:8000/ws/system-metrics';
const RECONNECT_DELAY_MS = 5000;
const HEARTBEAT_INTERVAL_MS = 30000;

export class WebSocketService {
  public onMessage: (type: string, payload: any) => void = () => {};
  public onError: (error: Error) => void = () => {};
  public onOpen: () => void = () => {};
  public onClose: (closeEvent: CloseEvent) => void = () => {};

  private socket: WebSocket | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private authToken: string | null = null;

  constructor() {}

  public connect(token: string | null) {
    this.authToken = token;
    if (!this.authToken) {
      this.handleError(new Error('Missing authentication token.'));
      return;
    }

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return;
    }

    const clientId = `web-${Math.random().toString(36).substring(2, 9)}`;
    const url = `${WEBSOCKET_URL_BASE}/${clientId}?token=${this.authToken}`;

    this.socket = new WebSocket(url);

    this.socket.onopen = () => this.handleOpen();
    this.socket.onmessage = (event) => this.handleMessage(event);
    this.socket.onerror = (event) => this.handleError(event);
    this.socket.onclose = (event) => this.handleClose(event);
  }

  public disconnect() {
    this.stopHeartbeat();
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.socket) {
      this.socket.close(1000, 'Client disconnected');
      this.socket = null;
    }
    this.onClose(new CloseEvent('close', { code: 1000, reason: 'Client disconnected' }));
  }

  private handleOpen() {
    const authMessage: AuthenticationRequest = { type: 'auth', authenticationToken: this.authToken! };
    this.sendMessage(authMessage);
    this.startHeartbeat();
  }

  private handleMessage(event: MessageEvent) {
    let message: WebSocketMessage;

    try {
      message = JSON.parse(event.data);
    } catch (error) {
      this.handleError(new Error('Failed to parse server message.'));
      return;
    }

    switch (message.type) {
      case 'auth_success':
        this.onOpen();
        break;

      case 'auth_failed':
        this.handleError(new Error(String(message.payload) || 'Authentication failed'));
        this.disconnect();
        break;

      default:
        this.onMessage(message.type, message.payload);
    }
  }

  private handleClose(event: CloseEvent) {
    this.stopHeartbeat();
    this.onClose(event);

    if (event.code !== 1000) {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) return;
    
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      if (this.authToken) {
        this.connect(this.authToken);
      }
    }, RECONNECT_DELAY_MS);
  }

  private sendMessage(message: object) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      this.handleError(new Error('WebSocket is not connected.'));
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      this.sendMessage({ type: 'heartbeat' });
    }, HEARTBEAT_INTERVAL_MS);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  public requestSystemInfo() {
    this.sendMessage({ type: 'get_all_metrics' });
  }

  public resetCircuitBreaker() {
    this.sendMessage({ type: 'reset_circuit_breaker' });
  }

  private handleError(error: Error | Event) {
    console.error(error);
    this.onError(error instanceof Error ? error : new Error('WebSocket error.'));
  }
}

export const webSocketService = new WebSocketService();
