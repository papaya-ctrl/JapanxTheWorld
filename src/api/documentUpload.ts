import type { ApiError } from "../types";
import { authorizationHeader, clearAuthSession, getAuthRevision, requireSameAccount } from "./auth";

// Backend processing permits 120 seconds; reserve additional upload/network time.
export const DOCUMENT_REQUEST_TIMEOUT_MS = 150_000;
let pending = false;
const messages: Record<string, string> = {
  AUTH_REQUIRED: "Sign in again to analyze documents.",
  ACCESS_DENIED: "Document analysis access has not been granted. Contact the administrator.",
  RATE_LIMITED: "Too many requests. Please wait before trying again.",
  SERVICE_BUSY: "The server is unavailable. Please try again later.",
  EMPTY_FILE: "This file is empty. Please choose another file.",
  INVALID_REQUEST: "Please upload one document in a supported format.",
  UNSUPPORTED_FILE_TYPE: "Please upload a JPEG, PNG, WebP, or PDF file.",
  UNSUPPORTED_REQUEST_TYPE: "Please upload a JPEG, PNG, WebP, or PDF file.",
  INVALID_DOCUMENT: "This file is corrupted or cannot be read as a supported document. Please choose another file.",
  FILE_TOO_LARGE: "The upload exceeds the size limit. Please choose a file up to 10 MB.",
  REQUEST_TOO_LARGE: "The upload exceeds the request limits. Please choose a smaller document.",
  DOCUMENT_LIMIT_EXCEEDED: "The document exceeds the supported page, image, or text limits. Please choose fewer pages or a smaller image.",
  ANALYSIS_MEMORY_LIMIT: "The document reached the processing memory limit. Please choose fewer pages or a smaller image.",
  DOCUMENT_UNREADABLE: "The document could not be read clearly. Please try a clearer image or PDF.",
  OCR_UNAVAILABLE: "Document recognition is unavailable. Please try again later.",
  ANALYSIS_BUSY: "Document analysis is busy. Please wait before trying again.",
  ANALYSIS_TIMEOUT: "Document processing exceeded the time limit. Please try fewer pages or a smaller image.",
  ANALYSIS_FAILED: "Document analysis failed. Please try again later.",
};

function retryAfter(response: Response): number | undefined {
  const raw = response.headers.get("Retry-After");
  if (!raw) return undefined;
  const seconds = Number(raw);
  const value = Number.isFinite(seconds) ? seconds : (Date.parse(raw) - Date.now()) / 1000;
  return Number.isFinite(value) && value > 0 ? Math.ceil(value) : undefined;
}

export async function postDocument(baseURL: string, file: File): Promise<unknown> {
  if (pending) throw { code: "ANALYSIS_BUSY", message: messages.ANALYSIS_BUSY } satisfies ApiError;
  pending = true;
  const revision = getAuthRevision();
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(), DOCUMENT_REQUEST_TIMEOUT_MS);
  try {
    const body = new FormData();
    body.append("file", file, file.name);
    const authorization = authorizationHeader();
    const response = await fetch(`${baseURL.replace(/\/$/, "")}/documents/analyze`, {
      method: "POST", body, signal: controller.signal, cache: "no-store",
      credentials: "omit", referrerPolicy: "no-referrer",
      headers: authorization ? { Authorization: authorization } : undefined,
    });
    if (!response.ok) {
      if (response.status === 401 && revision === getAuthRevision()) clearAuthSession();
      const payload: unknown = await response.json().catch(() => null);
      const backendCode = payload && typeof payload === "object" && "code" in payload && typeof payload.code === "string" ? payload.code : undefined;
      const code = backendCode && messages[backendCode] ? backendCode : `HTTP_${response.status}`;
      const fallback = response.status === 429 ? "Too many requests. Please wait before trying again."
        : response.status === 401 ? messages.AUTH_REQUIRED
        : response.status === 403 ? messages.ACCESS_DENIED
        : response.status === 503 ? "The server is unavailable. Please try again later."
        : response.status === 504 ? messages.ANALYSIS_TIMEOUT
        : response.status === 413 ? messages.DOCUMENT_LIMIT_EXCEEDED
        : response.status === 422 ? messages.DOCUMENT_UNREADABLE
        : "Document analysis failed. Please try again later.";
      throw { code, message: messages[code] ?? fallback, status: response.status, retryAfterSeconds: retryAfter(response) } satisfies ApiError;
    }
    let result: unknown;
    try { result = await response.json(); }
    catch { throw { code: "MALFORMED_ANALYSIS", message: "The analysis result could not be displayed safely. Please try again." } satisfies ApiError; }
    requireSameAccount(revision);
    return result;
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && typeof error.code === "string" && "message" in error && typeof error.message === "string") throw error;
    throw {
      code: controller.signal.aborted ? "CLIENT_TIMEOUT" : "SERVER_UNAVAILABLE",
      message: controller.signal.aborted
        ? "The request timed out. The server may still be processing it. Please wait before submitting again."
        : "Unable to reach the document server. Check your connection before trying again.",
    } satisfies ApiError;
  } finally {
    globalThis.clearTimeout(timeout);
    pending = false;
  }
}
