import React from 'react';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';
import store from './store/store.ts';
import App from './App';
import './index.css';
import { webSocketService } from './services/websocket/simplifiedWebSocketService';

// Initialize WebSocket connection when the app loads
webSocketService.connect(store.getState().auth.token);

const root = createRoot(document.getElementById('root')!);

root.render(
  <React.StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </React.StrictMode>
);