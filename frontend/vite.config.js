import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Offline-first: everything is bundled locally, nothing is fetched from a CDN.
// The build lands in Django's static dir and is served at /static/spa/.
export default defineConfig({
  plugins: [vue()],
  base: "/static/spa/",
  build: {
    outDir: "../static/spa",
    emptyOutDir: true,
    assetsInlineLimit: 4096,
  },
  server: {
    port: 5173,
    // Dev mode talks to the Django server running on the LAN host.
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
});
