import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    proxy: {
      '/predict-risk': 'http://127.0.0.1:8000',
      '/api': 'http://127.0.0.1:8000',
      '/evacuation-route': 'http://127.0.0.1:8000',
    },
  },

});
