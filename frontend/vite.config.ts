import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The mocks live in ../mocks, outside this folder.
    fs: { allow: [".."] },
    // Same-origin calls to the FastAPI backend in dev (uvicorn backend.api:app).
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
