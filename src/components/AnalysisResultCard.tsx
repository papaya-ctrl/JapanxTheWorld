import { Link } from "react-router";
import type { DocumentAnalysisResult } from "../types";
import { ImportantPointsList } from "./ImportantPointsList";
import { NextStepsList } from "./NextStepsList";
import { UrgencyBadge } from "./UrgencyBadge";

type AnalysisResultCardProps = {
  result: DocumentAnalysisResult;
};

const formatDeadline = (deadline: string | null) => {
  if (!deadline) {
    return "No clear deadline was found in this result.";
  }

  return new Date(deadline).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
};

export function AnalysisResultCard({ result }: AnalysisResultCardProps) {
  const sourceLabel =
    result.source === "template" ? "Verified Guide" : "AI-assisted Explanation";
  const sourceHelp =
    result.source === "template"
      ? "Based on JapanxTheWorld trusted content"
      : "Please confirm important details with official sources";

  return (
    <article className="overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-xl shadow-slate-200/60">
      <div className="border-b border-slate-200 bg-gradient-to-r from-blue-50 via-white to-red-50 px-6 py-6 sm:px-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <div className="rounded-2xl bg-slate-900 px-4 py-2 text-white">
                <p className="text-xs font-semibold uppercase text-white">
                  {sourceLabel}
                </p>
                <p className="mt-1 text-xs text-white/75">{sourceHelp}</p>
              </div>
              <UrgencyBadge urgency={result.urgency} />
            </div>
            <div>
              <p className="text-sm font-medium text-blue-700">Document type</p>
              <h1 className="mt-1 text-2xl font-semibold text-slate-900 sm:text-3xl">
                {result.documentType}
              </h1>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Deadline
            </p>
            <p className="mt-2 max-w-xs text-sm leading-6 text-slate-700">
              {formatDeadline(result.deadline)}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-8 px-6 py-6 sm:px-8 sm:py-8">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900">Summary</h2>
          <p className="text-sm leading-7 text-slate-700">{result.summary}</p>
        </section>

        <section className="grid gap-8 lg:grid-cols-2">
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-slate-900">
              Important points
            </h2>
            <ImportantPointsList items={result.importantPoints} />
          </div>
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-slate-900">Next steps</h2>
            <NextStepsList steps={result.nextSteps} />
          </div>
        </section>

        {result.relatedGuide ? (
          <section className="rounded-3xl border border-blue-100 bg-blue-50 px-5 py-4">
            <p className="text-sm font-semibold text-blue-900">Related guide</p>
            <p className="mt-2 text-sm leading-6 text-blue-900/80">
              A matching procedure guide is available if you want more step-by-step
              help.
            </p>
            <Link
              to={`/life-guides/${result.relatedGuide}`}
              className="mt-4 inline-flex rounded-full bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              Open related guide
            </Link>
          </section>
        ) : null}

        <section className="rounded-3xl border border-red-100 bg-red-50 px-5 py-4">
          <p className="text-sm font-semibold text-red-700">
            Official confirmation warning
          </p>
          <p className="mt-2 text-sm leading-6 text-red-700/90">
            {result.officialWarning}
          </p>
        </section>
      </div>
    </article>
  );
}
