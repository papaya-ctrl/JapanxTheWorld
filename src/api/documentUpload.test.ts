import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { analyzeDocument, isDocumentAnalysisResult } from "./client";
import { isDocumentUploadResult } from "./documentContract";
import { DOCUMENT_REQUEST_TIMEOUT_MS } from "./documentUpload";
import { uploadResult } from "../test/documentFixtures";

const fileInput = (type = "image/jpeg", name = "arbitrary.jpg") => {
  const file = new File(["synthetic document"], name, { type });
  return { file, name, type, size: file.size };
};
const response = (body: unknown, status = 200, headers = {}) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });

beforeEach(() => vi.stubEnv("VITE_USE_MOCK_API", "false"));
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.useRealTimers(); });

describe("live document API", () => {
  it.each([["image/jpeg", "photo.jpg"], ["application/pdf", "scan.pdf"]])("sends the actual %s upload as file-only FormData", async (type, name) => {
    const fetch = vi.fn().mockResolvedValue(response(uploadResult()));
    vi.stubGlobal("fetch", fetch);
    const documentFile = fileInput(type, name);
    const result = await analyzeDocument({ documentFile, documentText: "ignored", documentTypeHint: "ignored", sourceLanguageHint: "ignored" });
    expect(result).toEqual(uploadResult());
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/documents/analyze");
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect([...init.body.keys()]).toEqual(["file"]);
    const sent = init.body.get("file") as File;
    expect(sent.name).toBe(documentFile.file.name);
    expect(sent.type).toBe(documentFile.file.type);
    expect(sent.size).toBe(documentFile.file.size);
    const bytes = await new Promise(resolve => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.readAsText(sent); });
    expect(bytes).toBe("synthetic document");
    expect(init.headers).toBeUndefined(); // Browser supplies its own multipart boundary.
    expect(init.cache).toBe("no-store");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("requires a real file and never accepts pasted text as a live upload", async () => {
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    await expect(analyzeDocument({ documentText: "simulate:success" })).rejects.toMatchObject({ code: "INVALID_REQUEST" });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("defaults to live when mock mode is absent", async () => {
    vi.stubEnv("VITE_USE_MOCK_API", undefined);
    const fetch = vi.fn().mockResolvedValue(response(uploadResult())); vi.stubGlobal("fetch", fetch);
    expect((await analyzeDocument({ documentFile: fileInput() })).source).toBe("deterministic");
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("never falls back to mock results on network failure", async () => {
    const fetch = vi.fn().mockRejectedValue(new TypeError("PRIVATE_INTERNAL_TRACE")); vi.stubGlobal("fetch", fetch);
    await expect(analyzeDocument({ documentFile: fileInput("image/png", "residence-tax.png") })).rejects.toMatchObject({ code: "SERVER_UNAVAILABLE" });
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("rejects template/AI responses in live mode", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ source: "ai", summary: "Do not display" })));
    await expect(analyzeDocument({ documentFile: fileInput() })).rejects.toMatchObject({ code: "MALFORMED_ANALYSIS" });
  });

  it.each([
    [400, "INVALID_DOCUMENT"], [413, "FILE_TOO_LARGE"], [413, "ANALYSIS_MEMORY_LIMIT"],
    [422, "DOCUMENT_UNREADABLE"], [500, "ANALYSIS_FAILED"], [503, "OCR_UNAVAILABLE"], [504, "ANALYSIS_TIMEOUT"],
  ])("handles HTTP %i / %s without echoing internal details", async (status, code) => {
    const fetch = vi.fn().mockResolvedValue(response({ code, message: "PRIVATE_STACK_TRACE" }, status)); vi.stubGlobal("fetch", fetch);
    try { await analyzeDocument({ documentFile: fileInput() }); throw new Error("Expected failure"); }
    catch (error) {
      expect(error).toMatchObject({ code, status });
      expect(JSON.stringify(error)).not.toContain("PRIVATE_STACK_TRACE");
    }
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("handles actual DRF throttling detail and Retry-After without retrying", async () => {
    const fetch = vi.fn().mockResolvedValue(response({ detail: "Request was throttled." }, 429, { "Retry-After": "42" })); vi.stubGlobal("fetch", fetch);
    await expect(analyzeDocument({ documentFile: fileInput() })).rejects.toMatchObject({ code: "HTTP_429", status: 429, retryAfterSeconds: 42 });
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("prevents overlapping OCR submissions", async () => {
    let complete!: (result: Response) => void;
    const fetch = vi.fn().mockImplementation(() => new Promise(resolve => { complete = resolve; })); vi.stubGlobal("fetch", fetch);
    const first = analyzeDocument({ documentFile: fileInput() });
    await expect(analyzeDocument({ documentFile: fileInput() })).rejects.toMatchObject({ code: "ANALYSIS_BUSY" });
    complete(response(uploadResult()));
    await first;
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("bounds request time and does not retry a possibly-running server job", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn().mockImplementation((_url, init) => new Promise((_resolve, reject) => {
      init.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    })); vi.stubGlobal("fetch", fetch);
    const check = expect(analyzeDocument({ documentFile: fileInput() })).rejects.toMatchObject({ code: "CLIENT_TIMEOUT" });
    await vi.advanceTimersByTimeAsync(DOCUMENT_REQUEST_TIMEOUT_MS);
    await check;
    expect(fetch).toHaveBeenCalledOnce();
  });
});

describe("Step 7 response contract", () => {
  it("accepts the exact structured response while retaining null primary fields", () => {
    expect(isDocumentUploadResult(uploadResult())).toBe(true);
    expect(isDocumentAnalysisResult(uploadResult())).toBe(true);
    expect(uploadResult().primaryAmount).toBeNull();
  });
  it.each([
    (r: Record<string, any>) => { delete r.amounts; },
    (r: Record<string, any>) => { r.deadlines[0].date = "2026-02-30"; },
    (r: Record<string, any>) => { r.deadlines[0].status = "complete"; },
    (r: Record<string, any>) => { r.amounts[0].value = "18000"; },
    (r: Record<string, any>) => { r.amounts[0].evidenceIds = ["missing-id"]; },
    (r: Record<string, any>) => { r.primaryDeadline = r.deadline = "2027-11-02"; },
    (r: Record<string, any>) => { r.primaryAmount = 999999; },
    (r: Record<string, any>) => { r.extractionStatus = "complete"; },
  ])("rejects malformed or unsupported fields without making up replacements", mutate => {
    const result = uploadResult(); mutate(result);
    expect(isDocumentUploadResult(result)).toBe(false);
  });
});
