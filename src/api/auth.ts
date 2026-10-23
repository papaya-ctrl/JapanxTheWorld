import { getApiConfiguration } from "./configuration";
import type { ApiError } from "../types";

type Account = { id: number; username: string; canAnalyzeDocuments: boolean };
type Session = { user: Account; expiresAt: number };
let session: Session | null = null;
let token: string | null = null;
let revision = 0;
let expiryTimer: ReturnType<typeof setTimeout> | undefined;
const listeners = new Set<() => void>();
export const AUTH_SESSION_EVENT = "japanxtheworld:account-change";
export const subscribeToAuth = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
export const getAuthSession = () => session;
export const getAuthRevision = () => revision;
export const authorizationHeader = () => token ? `Token ${token}` : undefined;

function changed() {
  revision += 1;
  listeners.forEach(listener => listener());
  if (typeof window !== "undefined") window.dispatchEvent(new Event(AUTH_SESSION_EVENT));
}

export function clearAuthSession() {
  clearTimeout(expiryTimer);
  expiryTimer = undefined;
  if (!session && !token) return;
  session = null; token = null; changed();
}

export function requireSameAccount(expectedRevision: number) {
  if (revision !== expectedRevision) throw { code: "AUTH_REQUIRED", message: "Your account changed. Please submit again after signing in." } satisfies ApiError;
}

export async function signIn(username: string, password: string): Promise<void> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15_000);
  try {
    const response = await fetch(`${getApiConfiguration().baseURL}/auth/login`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }), credentials: "omit", cache: "no-store",
      referrerPolicy: "no-referrer", signal: controller.signal,
    });
    if (!response.ok) {
      throw { code: response.status === 429 ? "RATE_LIMITED" : "SIGN_IN_FAILED", message: response.status === 429
        ? "Too many sign-in attempts. Please wait before trying again."
        : response.status >= 500 ? "Sign-in is unavailable. Please try again later." : "Sign-in failed. Check your account name and password." } satisfies ApiError;
    }
    const result = await response.json();
    if (!result || typeof result.token !== "string" || !/^[a-f0-9]{40}$/.test(result.token) || !Number.isInteger(result.expiresIn) || result.expiresIn <= 0 || result.expiresIn > 86400 ||
        !result.user || !Number.isInteger(result.user.id) || typeof result.user.username !== "string" || typeof result.user.canAnalyzeDocuments !== "boolean") {
      throw { code: "SIGN_IN_FAILED", message: "The account response could not be verified." } satisfies ApiError;
    }
    clearAuthSession();
    token = result.token;
    session = { user: { id: result.user.id, username: result.user.username, canAnalyzeDocuments: result.user.canAnalyzeDocuments }, expiresAt: Date.now()+result.expiresIn*1000 };
    expiryTimer = setTimeout(clearAuthSession, result.expiresIn*1000);
    changed();
  } catch (error) {
    if (error && typeof error === "object" && "code" in error) throw error;
    throw { code: "SIGN_IN_FAILED", message: "Unable to reach the account server. Please try again later." } satisfies ApiError;
  } finally { clearTimeout(timer); }
}

export async function signOut(): Promise<boolean> {
  const authorization = authorizationHeader();
  clearAuthSession(); // Private results disappear even if the network is unavailable.
  if (!authorization) return true;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10_000);
  try {
    const response = await fetch(`${getApiConfiguration().baseURL}/auth/logout`, {
      method: "POST", headers: { Authorization: authorization, "Content-Type": "application/json" }, body: "{}", credentials: "omit",
      cache: "no-store", referrerPolicy: "no-referrer", signal: controller.signal,
    });
    return response.ok || response.status === 401;
  } catch { return false; }
  finally { clearTimeout(timer); }
}
