import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const backendTarget = process.env.API_PROXY_TARGET ?? 'http://backend:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api/': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/ws/': {
        target: backendTarget,
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
