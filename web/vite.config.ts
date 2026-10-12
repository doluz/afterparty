import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The API serves the built app from src/afterparty/static; in dev, Vite proxies to it.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8080',
      '/afterparty-extension.zip': 'http://127.0.0.1:8080',
    },
  },
  build: { outDir: '../src/afterparty/static', emptyOutDir: true },
})
