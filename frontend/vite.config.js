import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8848',
        changeOrigin: true,
      },
      '/images': {
        target: 'http://localhost:8848',
        changeOrigin: true,
      },
    },
  },
  // Production: built files served by nginx from frontend/dist/
})
