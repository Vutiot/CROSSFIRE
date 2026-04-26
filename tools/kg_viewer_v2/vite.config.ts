import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

// Build a single-folder dist that serve.py can serve as static assets.
// Dev server proxies /api/* to the python serve.py on :8080.
export default defineConfig({
  plugins: [preact()],
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    target: "es2022",
    sourcemap: true,
    chunkSizeWarningLimit: 1500,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8080",
    },
  },
});
