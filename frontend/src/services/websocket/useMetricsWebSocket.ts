import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../../store/store';
import { setAllMetrics } from '../../store/slices/allMetricsSlice';
import { setCircuitBreakerState } from '../../store/slices/circuitBreakerSlice';
import { setConnectionStatus } from '../../store/slices/websocketSlice';
import { ConnectionStatus } from './websocket_types';
import { webSocketService } from './simplifiedWebSocketService';

export const useMetricsWebSocket = () => {
  const dispatch = useDispatch();
  const token = useSelector((state: RootState) => state.auth.token);

  useEffect(() => {
    const handleWebSocketOpen = () => dispatch(setConnectionStatus(ConnectionStatus.CONNECTED));
    const handleWebSocketClose = () => dispatch(setConnectionStatus(ConnectionStatus.DISCONNECTED));
    const handleWebSocketError = (error: Error | ErrorEvent) => console.error('WebSocket error:', error.message);
    const handleWebSocketMessage = (type: string, payload: any) => {
      switch (type) {
        case 'all_metrics':
          dispatch(setAllMetrics(payload));
          break;
        case 'circuit_breaker':
          dispatch(setCircuitBreakerState(payload.status));
          break;
        default:
          console.warn(`Unknown message type: ${type}`);
      }
    };

    if (token) {
      webSocketService.onOpen = handleWebSocketOpen;
      webSocketService.onClose = handleWebSocketClose;
      webSocketService.onError = handleWebSocketError;
      webSocketService.onMessage = handleWebSocketMessage;

      dispatch(setConnectionStatus(ConnectionStatus.CONNECTING));
      webSocketService.connect(token);

      return () => {
        webSocketService.disconnect();
      };
    }
  }, [dispatch, token]);

  return {
    requestSystemInfo: webSocketService.requestSystemInfo,
    resetCircuitBreaker: webSocketService.resetCircuitBreaker,
  };
};
