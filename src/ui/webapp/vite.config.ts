import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite config tuned for SPA build to be served by Python HTTP server.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  },
  server: {
    host: '127.0.0.1',
    port: 5175,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true
      },
      '/mcp': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true
      }
    }
  }
})