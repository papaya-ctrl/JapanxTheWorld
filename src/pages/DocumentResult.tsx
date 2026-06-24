import { useMemo } from "react";
import { Link, useLocation } from "react-router";
import { AnalysisResultCard } from "../components/AnalysisResultCard";
import type { DocumentAnalysisResult } from "../types";

type LocationState = {
  result?: DocumentAnalysisResult;
};

const readStoredResult = (): DocumentAnalysisResult | null => {
  const raw = window.sessionStorage.getItem("japanxtheworld.lastAnalysis");
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as DocumentAnalysisResult;
  } catch {
    return null;
  }
};

export function DocumentResult() {
  const location = useLocation();
  const locationState = location.state as LocationState | null;

  const result = useMemo(
    () => locationState?.result ?? readStoredResult(),
    [locationState],
  );

  if (!result) {
    return (
      <section className="rounded-[32px] border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          No result yet
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-slate-900">
          Start with a document first
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-slate-600">
          The result page needs a completed document analysis. Paste document text
          on the decoder page and then come back here.
        </p>
        <Link
          to="/document-decoder"
          className="mt-6 inline-flex rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700"
        >
          Open Document Decoder
        </Link>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-700">
            Analysis result
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            This layout stays the same whether the backend used a trusted template
            or AI support.
          </p>
        </div>
        <Link
          to="/document-decoder"
          className="inline-flex rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
        >
          Analyze another document
        </Link>
      </div>
      <AnalysisResultCard result={result} />
    </div>
  );
}
