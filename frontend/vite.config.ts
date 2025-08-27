import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',  // Listen on all network interfaces
    port: 51083,
    strictPort: true,  // 严格使用指定端口
    proxy: {
      '/api': {
        target: 'http://localhost:51082',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:51082',
        changeOrigin: true,
      },
    },
  },
})