import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // The UI is mounted by FastAPI under `/ui`.
  base: "/ui/",
  server: {
    proxy: {
      "/v1": "http://localhost:8787",
    },
  },
  build: {
    // Copy the built UI into the FastAPI static directory.
    outDir: "../science_graphrag/api/static/ui",
    emptyOutDir: true,
  },
});

