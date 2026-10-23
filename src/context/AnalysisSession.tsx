import { createContext, type ReactNode, useContext, useEffect, useRef } from "react";
import type { DocumentAnalysisResult } from "../types";

type Session = {
  put: (result: DocumentAnalysisResult) => string;
  get: (id: unknown) => DocumentAnalysisResult | null;
  clear: () => void;
};
const Context = createContext<Session | null>(null);

/** Only an opaque id enters navigation history. All extracted data stays in RAM. */
export function AnalysisSessionProvider({ children }: { children: ReactNode }) {
  const current = useRef<{ id: string; result: DocumentAnalysisResult } | null>(null);
  const session = useRef<Session>({
    put(result) {
      const id = crypto.randomUUID();
      current.current = { id, result };
      return id;
    },
    get(id) { return typeof id === "string" && current.current?.id === id ? current.current.result : null; },
    clear() { current.current = null; },
  });
  useEffect(() => {
    // Remove data saved by earlier app versions; never read it into the UI.
    for (const storage of ["sessionStorage", "localStorage"] as const) {
      try { window[storage].removeItem("japanxtheworld.lastAnalysis"); } catch { /* Storage can be disabled. */ }
    }
    const state: unknown = window.history.state;
    if (state && typeof state === "object" && "usr" in state && state.usr && typeof state.usr === "object" && "result" in state.usr) {
      const { result: _discarded, ...usr } = state.usr;
      window.history.replaceState({ ...state, usr }, "");
    }
    return () => { current.current = null; };
  }, []);
  return <Context.Provider value={session.current}>{children}</Context.Provider>;
}
export function useAnalysisSession() {
  const value = useContext(Context);
  if (!value) throw new Error("Analysis session is unavailable.");
  return value;
}
