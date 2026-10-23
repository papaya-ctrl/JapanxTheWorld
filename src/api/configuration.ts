export type PublicEnvironment = Record<string, unknown>;
export const PUBLIC_ENV_KEYS = ["VITE_API_BASE_URL", "VITE_USE_MOCK_API", "VITE_MOCK_API_SCENARIO", "VITE_REQUIRE_AUTH"];

export function apiConfiguration(env: PublicEnvironment, production = env.PROD === true && env.MODE !== "test" && env.MODE !== "demo") {
  const baseURL = String(env.VITE_API_BASE_URL ?? (production ? "/api" : "http://localhost:8000/api")).replace(/\/$/, "");
  if (baseURL !== "/api") {
    let url: URL;
    try { url = new URL(baseURL); } catch { throw new Error("Configure an API origin ending in /api, or use /api on the same origin."); }
    if (!["https:", "http:"].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== "/api") {
      throw new Error("The API URL must be an HTTP(S) origin ending in /api, without credentials or query parameters.");
    }
    if (production && (url.protocol !== "https:" || /^(localhost|0\.0\.0\.0|127\..*|\[::1\])$/.test(url.hostname) || url.hostname.endsWith(".localhost"))) {
      throw new Error("Production requires an HTTPS API URL without a localhost address.");
    }
  }
  for (const key of ["VITE_USE_MOCK_API", "VITE_REQUIRE_AUTH"]) {
    if (env[key] !== undefined && !["true", "false"].includes(String(env[key]))) throw new Error(`${key} must be true or false.`);
  }
  const useMock = env.VITE_USE_MOCK_API === "true";
  const requireAuth = env.VITE_REQUIRE_AUTH === "true";
  if (production && (useMock || !requireAuth)) throw new Error("Production requires live API mode and explicit account access.");
  return { baseURL, useMock, requireAuth };
}

export const getApiConfiguration = () => apiConfiguration(import.meta.env);

export function validateBuildConfiguration(env: PublicEnvironment, production = true, vercel = false) {
  if (Object.keys(env).some(key => key.startsWith("VITE_") && !PUBLIC_ENV_KEYS.includes(key))) throw new Error("Unknown VITE_ variable: only reviewed public configuration is allowed.");
  const config = apiConfiguration(env, production);
  if (vercel && config.baseURL === "/api") throw new Error("Configure the separate HTTPS Python backend URL for Vercel.");
  return config;
}
