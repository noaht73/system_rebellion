import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export type CircuitBreakerState = 'closed' | 'open' | 'half-open';

interface CircuitBreakerSliceState {
  status: CircuitBreakerState;
}

const initialState: CircuitBreakerSliceState = {
  status: 'closed',
};

const circuitBreakerSlice = createSlice({
  name: 'circuitBreaker',
  initialState,
  reducers: {
    setCircuitBreakerState(state, action: PayloadAction<CircuitBreakerState>) {
      state.status = action.payload;
    },
  },
});

export const { setCircuitBreakerState } = circuitBreakerSlice.actions;
export default circuitBreakerSlice.reducer;
