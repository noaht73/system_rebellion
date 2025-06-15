// src/store/slices/metricsSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface MetricsState {
  historical: any;
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  lastUpdated: string | null;
  error: string | null;
  useWebSocket: boolean;
}

const initialState: MetricsState = {
  status: 'disconnected',
  lastUpdated: null,
  error: null,
  useWebSocket: true,
  historical: undefined
};

const metricsSlice = createSlice({
  name: 'metrics',
  initialState,
  reducers: {
    setConnectionStatus: (state, action: PayloadAction<MetricsState['status']>) => {
      state.status = action.payload;
      if (action.payload === 'connected') {
        state.error = null;
      }
    },
    setLastUpdated: (state, action: PayloadAction<string>) => {
      state.lastUpdated = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      if (action.payload) {
        state.status = 'error';
      }
    },
    toggleConnectionType: (state) => {
      state.useWebSocket = !state.useWebSocket;
    },
    resetMetrics: () => initialState,
  },
});

// Export actions
export const {
  setConnectionStatus,
  setLastUpdated,
  setError,
  toggleConnectionType,
  resetMetrics,
} = metricsSlice.actions;

// Selectors
export const selectMetricsStatus = (state: { metrics: MetricsState }) => state.metrics.status;
export const selectLastUpdated = (state: { metrics: MetricsState }) => state.metrics.lastUpdated;
export const selectMetricsError = (state: { metrics: MetricsState }) => state.metrics.error;
export const selectUseWebSocket = (state: { metrics: MetricsState }) => state.metrics.useWebSocket;

export default metricsSlice.reducer;