import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    proxy: {
      "/api":
        loadEnv(mode, ".", "VITE_").VITE_API_TARGET ||
        `http://127.0.0.1:${loadEnv(mode, "../..", "API_PORT").API_PORT || "8000"}`,
    },
  },
}));
