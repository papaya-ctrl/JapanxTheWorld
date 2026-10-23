import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import { readFileSync } from "node:fs";
import { validateBuildConfiguration } from "./src/api/configuration.ts";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  if (command === "build") {
    const config = validateBuildConfiguration(env, mode !== "demo", process.env.VERCEL === "1");
    if (process.env.VERCEL === "1") {
      const hosting = JSON.parse(readFileSync("vercel.json", "utf8"));
      const policy = hosting.headers?.flatMap((rule: { headers: { key: string; value: string }[] }) => rule.headers).find((header: { key: string }) => header.key === "Content-Security-Policy")?.value ?? "";
      const connect = policy.split(";").find((part: string) => part.trim().startsWith("connect-src "))?.trim().split(/\s+/).slice(1) ?? [];
      if (!connect.includes(new URL(config.baseURL).origin)) throw new Error("Add the exact HTTPS backend origin to Vercel connect-src before building.");
    }
  }
  return {
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    globals: true,
    env: { VITE_USE_MOCK_API: "true" },
    setupFiles: "./src/test/setup.ts",
  },
  };
});
