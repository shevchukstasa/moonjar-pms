import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // React core — loaded first, always needed
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // Data-fetching + state
          'vendor-query': ['@tanstack/react-query', 'zustand', 'axios'],
          // Charts — heavy, only needed on analytics pages
          'vendor-charts': ['recharts'],
          // Form utilities
          'vendor-forms': ['react-hook-form', '@hookform/resolvers', 'zod'],
          // Table
          'vendor-table': ['@tanstack/react-table'],
          // Icons — used widely but tree-shakeable per chunk
          'vendor-icons': ['lucide-react'],
          // Date utilities
          'vendor-date': ['date-fns'],
        },
      },
    },
  },
});
