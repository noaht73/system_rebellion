// vite.config.ts - Now with 100% more distinguished chaos!
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// Sir Hawkington's Distinguished Proxy Configuration
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      { find: '@', replacement: path.resolve(__dirname, 'src') },
      { find: 'src', replacement: path.resolve(__dirname, 'src') },
    ] 
  },


  server: {
    // The Meth Snail insists on port 5173 for optimal performance
    port: 5173,
    proxy: {
      // All /api requests will be proxied to the backend with aristocratic elegance
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.log('🧐 Sir Hawkington observes a proxy error:', err);
          });
          proxy.on('proxyReq', (_proxyReq, req) => {
            console.log(`🎩 Distinguished request to ${req.url} being proxied with elegance`);
          });
        }
      },
      // WebSocket proxy for all /ws requests
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
        configure: (proxy) => {
          proxy.on('error', (err, req) => {
            console.error('🐌 The Meth Snail reports a WebSocket error:', err);
            console.error('🐌 Request that caused the error:', req?.url);
          });
          proxy.on('proxyReqWs', (_proxyReq, req, socket) => {
            console.log('🔌 WebSocket connection established to:', req.url);
            socket.on('error', (err) => {
              console.error('🔌 WebSocket socket error:', err);
            });
          });
          proxy.on('open', () => {
            console.log('🔌 WebSocket proxy connection opened');
          });
          proxy.on('close', (_req, socket) => {
            console.log('🔌 WebSocket proxy connection closed');
            if (socket) {
              socket.end();
            }
          });
        }
      }
    }
  },
  // The Stick's anxiety management settings
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // The VIC-20 suggests optimal chunking strategies
          if (id.includes('node_modules')) {
            return 'vendor';
          }
        }
      }
    }
  }
});