import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy: /api and /openapi.json go to the FastAPI backend on 127.0.0.1:8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/openapi.json": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [],
  },
});
