// useMetricsWebSocket.ts
import { useEffect, useRef, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../../store/store';
import { ConnectionStatus, WebSocketMessage } from './websocket_types';
import { initWebSocket } from './WebSocketService';
import { 
  setConnectionStatus, 
  setError as setMetricsError
} from '../../store/slices/metricsSlice';
import {
  updateCPUMetrics,
  setCPULoading,
  setCPUError
} from '../../store/slices/metrics/CPUSlice';
import {
  updateMemoryMetrics,
  setMemoryLoading,
  setMemoryError
} from '../../store/slices/metrics/MemorySlice';
import {
  updateDiskMetrics,
  setDiskLoading,
  setDiskError
} from '../../store/slices/metrics/DiskSlice';
import {
  updateNetworkMetrics,
  setNetworkLoading,
  setNetworkError
} from '../../store/slices/metrics/NetworkSlice';

export const useMetricsWebSocket = () => {
  const dispatch = useDispatch();
  const wsRef = useRef<ReturnType<typeof initWebSocket> | null>(null);
  const user = useSelector((state: RootState) => state.auth?.user);

  // Handle incoming messages
  const handleMessage = useCallback((message: WebSocketMessage) => {
    console.log('🔄 [useMetricsWebSocket] Received message type:', message.type);
    console.log('🔄 [useMetricsWebSocket] Message data:', JSON.stringify(message.data, null, 2));
    
    switch (message.type) {
      case 'cpu_metrics':
        console.log('🚀 [useMetricsWebSocket] Dispatching updateCPUMetrics');
        dispatch(updateCPUMetrics(message.data));
        dispatch(setCPULoading(false));
        dispatch(setCPUError(null));
        break;
        
      case 'memory_metrics':
        console.log('🚀 [useMetricsWebSocket] Dispatching updateMemoryMetrics');
        dispatch(updateMemoryMetrics(message.data));
        dispatch(setMemoryLoading(false));
        dispatch(setMemoryError(null));
        break;
        
      case 'disk_metrics':
        console.log('🚀 [useMetricsWebSocket] Dispatching updateDiskMetrics');
        dispatch(updateDiskMetrics(message.data));
        dispatch(setDiskLoading(false));
        dispatch(setDiskError(null));
        break;
        
      case 'network_metrics':
        console.log('🚀 [useMetricsWebSocket] Dispatching updateNetworkMetrics');
        dispatch(updateNetworkMetrics(message.data));
        dispatch(setNetworkLoading(false));
        dispatch(setNetworkError(null));
        break;
        
      case 'error':
        console.log('❌ [useMetricsWebSocket] Dispatching setMetricsError with message:', 
          message.data?.message || 'Unknown error');
        dispatch(setMetricsError(message.data?.message || 'Unknown error'));
        break;
        
      default:
        console.warn('🚨 [useMetricsWebSocket] Unknown message type:', message.type);
    }
  }, [dispatch]);

  useEffect(() => {
    console.log('🎯 [useMetricsWebSocket] Effect triggered');
    console.log('🎯 [useMetricsWebSocket] User state:', user);
    console.log('🎯 [useMetricsWebSocket] User authenticated:', !!user);
    
    if (user) {
      try {
        console.log('✅ [useMetricsWebSocket] User authenticated, initializing WebSocket...');
        
        // Initialize or get existing WebSocket service
        if (!wsRef.current) {
          console.log('🎯 [useMetricsWebSocket] Creating new WebSocket service...');
          wsRef.current = initWebSocket(dispatch);
          
          // Set up event handlers
          if (wsRef.current) {
            console.log('🎯 [useMetricsWebSocket] Setting up WebSocket event handlers...');
            
            // Set message handler
            wsRef.current.onMessage = handleMessage;
            
            // Handle connection status changes
            wsRef.current.onConnectionStatusChange = (status: ConnectionStatus) => {
              console.log('🎯 [useMetricsWebSocket] WebSocket connection status changed:', status);
              dispatch(setConnectionStatus(status));
              
              if (status === 'connected') {
                console.log('🎯 [useMetricsWebSocket] WebSocket connected - ready to receive metrics');
              }
            };
            
            // Handle errors
            wsRef.current.onError = (error: Error) => {
              console.error('🚨 [useMetricsWebSocket] WebSocket error:', error);
              dispatch(setMetricsError(error.message));
            };
            
            console.log('🎯 [useMetricsWebSocket] Attempting to connect WebSocket...');
            // Connect the WebSocket
            wsRef.current.connect();
          } else {
            console.error('🚨 [useMetricsWebSocket] Failed to create WebSocket service');
          }
        } else {
          console.log('🎯 [useMetricsWebSocket] WebSocket service already exists, checking connection...');
          // If WebSocket already exists, ensure it's connected
          if (wsRef.current.getConnectionState() !== 'connected') {
            console.log('🎯 [useMetricsWebSocket] WebSocket not connected, attempting to connect...');
            wsRef.current.connect();
          } else {
            console.log('🎯 [useMetricsWebSocket] WebSocket already connected');
          }
        }
      } catch (error) {
        console.error('🚨 [useMetricsWebSocket] Error initializing WebSocket:', error);
        dispatch(setMetricsError('Failed to initialize WebSocket connection'));
      }
    } else {
      console.log('❌ [useMetricsWebSocket] User not authenticated, skipping WebSocket initialization');
      // Clean up WebSocket if user is not authenticated
      if (wsRef.current) {
        console.log('🧹 [useMetricsWebSocket] Cleaning up WebSocket connection...');
        wsRef.current.disconnect();
        wsRef.current = null;
      }
    }
  }, [user, dispatch, handleMessage]);

  // Public API
  return {
    reconnect: () => {
      console.log('🔄 [useMetricsWebSocket] Reconnecting WebSocket...');
      wsRef.current?.connect();
    },
    disconnect: () => {
      console.log('🔌 [useMetricsWebSocket] Disconnecting WebSocket...');
      wsRef.current?.disconnect();
    },
    resetCircuitBreaker: () => {
      console.log('🔄 [useMetricsWebSocket] Resetting circuit breaker...');
      if (wsRef.current) {
        wsRef.current.resetCircuitBreaker();
        wsRef.current.connect();
      }
    },
    isConnected: () => wsRef.current?.isConnected() || false,
    requestIntervalChange: (seconds: number) => wsRef.current?.requestIntervalChange(seconds),
    requestSystemInfo: () => wsRef.current?.requestSystemInfo()
  };
};

export default useMetricsWebSocket;