import { createSlice, PayloadAction } from '@reduxjs/toolkit';

// Define a more specific type for the metrics payload
interface AllMetricsPayload {
  cpu: any;
  memory: any;
  disk: any;
  network: any;
}

interface AllMetricsState {
  data: AllMetricsPayload | null;
}

const initialState: AllMetricsState = {
  data: null,
};

const allMetricsSlice = createSlice({
  name: 'allMetrics',
  initialState,
  reducers: {
    setAllMetrics(state, action: PayloadAction<AllMetricsPayload>) {
      state.data = action.payload;
    },
  },
});

export const { setAllMetrics } = allMetricsSlice.actions;
export default allMetricsSlice.reducer;
