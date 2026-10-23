import { useEffect } from "react";
import { Link, useLocation } from "react-router";
import { AnalysisResultCard } from "../components/AnalysisResultCard";
import { useAnalysisSession } from "../context/AnalysisSession";

export function DocumentResult() {
  const location = useLocation();
  useEffect(() => { window.scrollTo({ top: 0, left: 0, behavior: "instant" }); }, []);
  const session = useAnalysisSession();
  const state: unknown = location.state;
  const result = session.get(state && typeof state === "object" && "analysisId" in state ? state.analysisId : null);

  if (!result) {
    return (
      <section className="rounded-[32px] border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          Result unavailable or expired
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-slate-900">
          Start with a document first
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-slate-600">
          Results are kept in memory and cleared after a reload. Upload a document
          on the decoder page to start a new analysis.
        </p>
        <Link
          to="/document-decoder"
          className="mt-6 inline-flex rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
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
            Review the extracted fields and their original source evidence. Results
            are cleared when you reload this app.
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
