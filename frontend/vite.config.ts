import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Dev server proxies /api like nginx does in the image, so the code never needs an absolute backend URL.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": process.env.VITE_DEV_BACKEND ?? "http://localhost:8000" } },
  test: { include: ["tests/**/*.test.{ts,tsx}"] },
});
