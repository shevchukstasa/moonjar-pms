import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "Moonjar Warehouse",
        short_name: "MJ Warehouse",
        theme_color: "#4A90E2",
        background_color: "#ffffff",
        display: "standalone",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: /^https?:\/\/.*\/api\/.*/,
            handler: "NetworkFirst",
            options: { cacheName: "api-cache", expiration: { maxEntries: 50, maxAgeSeconds: 300 } },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5175,
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
});
