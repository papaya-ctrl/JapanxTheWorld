import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { uploadResult } from "../test/documentFixtures";

let navigation: unknown;
function Observer() { navigation = useLocation().state; return null; }
const renderDecoder = (route = "/document-decoder", state?: unknown) => render(
  <MemoryRouter initialEntries={[{ pathname: route, state }]}><Observer /><App /></MemoryRouter>,
);
const select = async (user: ReturnType<typeof userEvent.setup>) => user.upload(
  screen.getByLabelText("Upload Photo / Document"), new File(["synthetic document"], "document.png", { type: "image/png" }),
);
const ok = () => new Response(JSON.stringify(uploadResult()), { status: 200 });

beforeEach(() => {
  vi.stubEnv("VITE_USE_MOCK_API", "false");
  window.localStorage.clear(); window.sessionStorage.clear(); navigation = null;
});
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.restoreAllMocks(); vi.useRealTimers(); });

describe("live upload navigation and privacy", () => {
  it("uploads once, displays real structured facts, and keeps the result out of storage/history", async () => {
    const fetch = vi.fn().mockResolvedValue(ok()); vi.stubGlobal("fetch", fetch);
    const storage = vi.spyOn(Storage.prototype, "setItem");
    const log = vi.spyOn(console, "log");
    const user = userEvent.setup(); renderDecoder();
    expect(screen.queryByText(/Demo mode/)).not.toBeInTheDocument();
    await select(user);
    expect(screen.getByText("File selected. Ready to analyze.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Analyze document" }));
    expect(await screen.findByRole("heading", { name: "National Health Insurance Tax" })).toBeInTheDocument();
    expect(screen.getByText("Partial extraction")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledOnce();
    expect(storage).not.toHaveBeenCalled();
    expect(log).not.toHaveBeenCalled();
    expect(navigation).toEqual({ analysisId: expect.any(String) });
    expect(JSON.stringify(navigation)).not.toMatch(/18000|evidence|納期限/);
  });

  it("expires after a reload even when navigation state survives", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ok()));
    const user = userEvent.setup(); const view = renderDecoder();
    await select(user); await user.click(screen.getByRole("button", { name: "Analyze document" }));
    await screen.findByRole("heading", { name: "National Health Insurance Tax" });
    const state = navigation;
    view.unmount();
    renderDecoder("/document-decoder/result", state);
    expect(screen.getByText("Result unavailable or expired")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "National Health Insurance Tax" })).not.toBeInTheDocument();
  });

  it("does not load raw results from old navigation or browser storage", () => {
    window.sessionStorage.setItem("japanxtheworld.lastAnalysis", JSON.stringify(uploadResult()));
    window.localStorage.setItem("japanxtheworld.lastAnalysis", JSON.stringify(uploadResult()));
    window.history.replaceState({ usr: { result: uploadResult() }, key: "old" }, "");
    renderDecoder("/document-decoder/result", { result: uploadResult() });
    expect(screen.getByText("Result unavailable or expired")).toBeInTheDocument();
    expect(window.sessionStorage.getItem("japanxtheworld.lastAnalysis")).toBeNull();
    expect(window.localStorage.getItem("japanxtheworld.lastAnalysis")).toBeNull();
    expect(window.history.state.usr.result).toBeUndefined();
  });

  it("locks all upload controls and duplicate submissions while a request is running", async () => {
    let finish!: (result: Response) => void;
    const fetch = vi.fn().mockImplementation(() => new Promise(resolve => { finish = resolve; })); vi.stubGlobal("fetch", fetch);
    const user = userEvent.setup(); renderDecoder(); await select(user);
    await user.click(screen.getByRole("button", { name: "Analyze document" }));
    expect(screen.getByText(/Uploading and analyzing document/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyzing…" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Replace" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Remove file" })).toBeDisabled();
    fireEvent.submit(screen.getByRole("button", { name: "Analyzing…" }).closest("form")!);
    expect(fetch).toHaveBeenCalledOnce();
    await act(async () => finish(ok()));
    await screen.findByText("Partial extraction");
  });

  it("shows unreadable OCR as an error without navigating or automatically retrying", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: "DOCUMENT_UNREADABLE", message: "private native trace" }), { status: 422 })); vi.stubGlobal("fetch", fetch);
    const user = userEvent.setup(); renderDecoder(); await select(user);
    await user.click(screen.getByRole("button", { name: "Analyze document" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("could not be read clearly");
    expect(alert).not.toHaveTextContent("private native trace");
    expect(within(alert).getByRole("button", { name: "Retry analysis" })).toBeEnabled();
    expect(fetch).toHaveBeenCalledOnce();
    expect(navigation).toBeNull();
  });

  it("respects Retry-After and leaves a resource-limit failure visible", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: "ANALYSIS_BUSY" }), { status: 503, headers: { "Retry-After": "5" } })); vi.stubGlobal("fetch", fetch);
    const user = userEvent.setup(); renderDecoder(); await select(user);
    await user.click(screen.getByRole("button", { name: "Analyze document" }));
    await screen.findByRole("alert");
    expect(screen.getByRole("button", { name: "Analyze document" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Retry analysis" })).toBeDisabled();
    expect(screen.getByText(/Please wait 5 seconds/)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("revokes local preview URLs on replacement, removal, and unmount", async () => {
    const create = vi.fn().mockReturnValueOnce("blob:first").mockReturnValueOnce("blob:second").mockReturnValueOnce("blob:third");
    const revoke = vi.fn();
    vi.spyOn(URL, "createObjectURL").mockImplementation(create);
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(revoke);
    const user = userEvent.setup(); const view = renderDecoder();
    await select(user); await screen.findByAltText("Selected document preview");
    await user.upload(screen.getByLabelText("Upload Photo / Document"), new File(["second"], "second.png", { type: "image/png" }));
    expect(revoke).toHaveBeenCalledWith("blob:first");
    await user.click(screen.getByRole("button", { name: "Remove file" }));
    expect(revoke).toHaveBeenCalledWith("blob:second");
    await select(user); view.unmount();
    expect(revoke).toHaveBeenCalledWith("blob:third");
  });
});
