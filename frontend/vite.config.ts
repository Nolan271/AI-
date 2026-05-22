import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        proxyTimeout: 600_000,   // 10min — SSE 流可能要跑几分钟
        timeout: 600_000,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        proxyTimeout: 60_000,
        timeout: 60_000,
      },
    },
  },
})
