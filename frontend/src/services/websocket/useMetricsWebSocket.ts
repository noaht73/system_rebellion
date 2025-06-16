// useMetricsWebSocket.ts
import { useEffect, useRef, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../../store/store';
import { ConnectionStatus, WebSocketMessage } from './websocket_types';
import { initWebSocket } from './WebSocketService';
import { 
  setConnectionStatus, 
  setError as setMetricsError,
  setSystemInfo
} from '../../store/slices/metricsSlice';
import { updateCPUMetrics } from '../../store/slices/metrics/CPUSlice';
import { updateMemoryMetrics } from '../../store/slices/metrics/MemorySlice';
import { updateDiskMetrics } from '../../store/slices/metrics/DiskSlice';
import { updateNetworkMetrics } from '../../store/slices/metrics/NetworkSlice';

export const useMetricsWebSocket = () => {
  const dispatch = useDispatch();
  const wsRef = useRef<ReturnType<typeof initWebSocket> | null>(null);
  const { user, token } = useSelector((state: RootState) => state.auth);

  // Handle incoming messages
  const handleMessage = useCallback((message: WebSocketMessage) => {
    console.log('🔄 [useMetricsWebSocket] Received message type:', message.type);
    console.log('🔄 [useMetricsWebSocket] Message data:', JSON.stringify(message.data, null, 2));
    
    switch (message.type) {
      case 'system_info':
        dispatch(setSystemInfo(message.data));
        break;

      case 'all_metrics':
        if (message.data) {
          if (message.data.cpu) {
            dispatch(updateCPUMetrics(message.data.cpu));
          }
          if (message.data.memory) {
            dispatch(updateMemoryMetrics(message.data.memory));
          }
          if (message.data.disk) {
            dispatch(updateDiskMetrics(message.data.disk));
          }
          if (message.data.network) {
            dispatch(updateNetworkMetrics(message.data.network));
          }
        }
        break;

      case 'error':
        dispatch(setMetricsError(message.data?.message || 'Unknown error'));
        break;

      default:
        console.warn('Unknown message type:', message.type);
    }
  }, [dispatch]);

  const isAuthenticated = !!(user?.id && token);

  // Effect for initializing and cleaning up the WebSocket service
  useEffect(() => {
    console.log('🎯 [useMetricsWebSocket] Initializing WebSocket service...');
    
    const ws = initWebSocket(dispatch);
    wsRef.current = ws;

    // Set up event handlers that don't depend on auth state
    ws.onMessage = handleMessage;
    ws.onConnectionStatusChange = (status: ConnectionStatus) => {
      console.log('🎯 [useMetricsWebSocket] WebSocket connection status changed:', status);
      dispatch(setConnectionStatus(status));
    };
    ws.onError = (error: Error) => {
      console.error('🚨 [useMetricsWebSocket] WebSocket error:', error);
      dispatch(setMetricsError(error.message));
    };

    // Cleanup function
    return () => {
      console.log('🧹 [useMetricsWebSocket] Cleaning up WebSocket service...');
      ws.disconnect();
      wsRef.current = null;
    };
  }, [dispatch, handleMessage]); // This effect runs only once

  // Effect for connecting/disconnecting based on authentication state
  useEffect(() => {
    console.log(`🎯 [useMetricsWebSocket] Auth state changed. isAuthenticated: ${isAuthenticated}`);
    if (isAuthenticated) {
      if (wsRef.current) {
        console.log('✅ [useMetricsWebSocket] User is authenticated. Connecting WebSocket...');
        wsRef.current.connect(token!); // token is guaranteed to be present here
      } else {
        console.error('🚨 [useMetricsWebSocket] WebSocket service not initialized. Cannot connect.');
      }
    } else {
      if (wsRef.current && wsRef.current.isConnected()) {
        console.log('🔌 [useMetricsWebSocket] User is not authenticated. Disconnecting WebSocket...');
        wsRef.current.disconnect();
      }
    }
  }, [isAuthenticated, token]); // This effect runs when auth state changes

  // Public API
  return {
    reconnect: () => {
      console.log('🔄 [useMetricsWebSocket] Reconnecting WebSocket...');
      wsRef.current?.connect(token);
    },
    disconnect: () => {
      console.log('🔌 [useMetricsWebSocket] Disconnecting WebSocket...');
      wsRef.current?.disconnect();
    },
    resetCircuitBreaker: () => {
      console.log('🔄 [useMetricsWebSocket] Resetting circuit breaker...');
      if (wsRef.current) {
        wsRef.current.resetCircuitBreaker();
        wsRef.current.connect(token);
      }
    },
    isConnected: () => wsRef.current?.isConnected() || false,
    requestIntervalChange: (seconds: number) => wsRef.current?.requestIntervalChange(seconds),
    requestSystemInfo: () => wsRef.current?.requestSystemInfo()
  };
};

export default useMetricsWebSocket;