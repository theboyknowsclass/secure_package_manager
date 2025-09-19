import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    watch: {
      usePolling: true,
    },
    // Reduce logging noise in production
    hmr: {
      overlay: process.env.NODE_ENV !== "production",
    },
  },
  define: {
    global: "globalThis",
  },
  // Suppress build warnings and info in production
  logLevel: process.env.NODE_ENV === "production" ? "error" : "info",
});
