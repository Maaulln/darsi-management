import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true,
    },
    hmr: {
      host: 'localhost',
      port: 8080,
      protocol: 'ws',
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/metabase': {
        target: process.env.VITE_METABASE_URL || 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
  build: { outDir: 'dist' },
});
