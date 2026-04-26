import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // The UI is mounted by FastAPI under `/ui`.
  base: "/ui/",
  server: {
    proxy: {
      "/v1": "http://localhost:8787",
      /** Agent v2 SSE (`useAgentStream`); required when UI is opened on the Vite port (not only via nginx :8787). */
      "/v2": "http://localhost:8787",
      "/health": "http://localhost:8787",
    },
  },
  build: {
    // Copy the built UI into the FastAPI static directory.
    outDir: "../science_graphrag/api/static/ui",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (id.includes("@mui") || id.includes("@emotion")) return "mui";
            if (
              id.includes("node_modules/react-dom") ||
              id.includes("node_modules/react-router") ||
              id.includes("node_modules/react/")
            ) {
              return "react-vendor";
            }
          }
        },
      },
    },
  },
});

