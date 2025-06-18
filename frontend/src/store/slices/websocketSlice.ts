import { createSlice, PayloadAction } from '@reduxjs/toolkit';

import { ConnectionStatus } from '../../services/websocket/websocket_types';

export interface WebSocketState {
  connectionStatus: ConnectionStatus;
}

const initialState: WebSocketState = {
  connectionStatus: ConnectionStatus.Disconnected,
};

const websocketSlice = createSlice({
  name: 'websocket',
  initialState,
  reducers: {
    setConnectionStatus(state, action: PayloadAction<ConnectionStatus>) {
      state.connectionStatus = action.payload;
    },
  },
});

export const { setConnectionStatus } = websocketSlice.actions;
export default websocketSlice.reducer;
