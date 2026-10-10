import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:8765', rewrite: path => path.replace(/^\/api/, '') } }
  },
  preview: { port: 5173, strictPort: true }
});
