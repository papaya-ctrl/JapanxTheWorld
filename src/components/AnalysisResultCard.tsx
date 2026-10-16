import type { DocumentAnalysisResult } from "../types";
import { ImportantPointsList } from "./ImportantPointsList";
import { NextStepsList } from "./NextStepsList";
import {
  DeadlineStatus,
  OfficialConfirmationNotice,
  RelatedGuideCallout,
  ResultSourceBadge,
} from "./ResultStatusBlocks";

type AnalysisResultCardProps = {
  result: DocumentAnalysisResult;
};

export function AnalysisResultCard({ result }: AnalysisResultCardProps) {
  return (
    <article className="overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-xl shadow-slate-200/60">
      <div className="border-b border-slate-200 bg-gradient-to-r from-blue-50 via-white to-amber-50 px-6 py-6 sm:px-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <ResultSourceBadge source={result.source} />
            </div>
            <div>
              <p className="text-sm font-medium text-blue-700">Document type</p>
              <h1 className="mt-1 text-2xl font-semibold text-slate-900 sm:text-3xl">
                {result.documentType}
              </h1>
            </div>
          </div>

          <DeadlineStatus deadline={result.deadline} urgency={result.urgency} />
        </div>
      </div>

      <div className="space-y-8 px-6 py-6 sm:px-8 sm:py-8">
        <section className="space-y-3">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-blue-700">
            What it means
          </p>
          <h2 className="text-xl font-semibold text-slate-950">Summary</h2>
          <p className="text-sm leading-7 text-slate-700">{result.summary}</p>
        </section>

        <section
          role="region"
          aria-labelledby="important-points-heading"
          className="rounded-[28px] border border-amber-200 bg-amber-50 p-5 shadow-sm sm:p-6"
        >
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-800 ring-1 ring-amber-200">
              <svg
                aria-hidden="true"
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m12 3 10 18H2L12 3Z" />
                <path d="M12 9v5" />
                <path d="M12 18h.01" />
              </svg>
            </span>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-amber-900">
                Critical information
              </p>
              <h2 id="important-points-heading" className="text-xl font-semibold text-slate-950">
                Important Points
              </h2>
            </div>
          </div>
          <div className="mt-5">
            <ImportantPointsList items={result.importantPoints} />
          </div>
        </section>

        <section className="rounded-[28px] border border-blue-200 bg-white p-5 shadow-sm sm:p-6">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-blue-700">
            What to do next
          </p>
          <h2 className="mt-1 text-xl font-semibold text-slate-950">Next Steps</h2>
          <div className="mt-5">
            <NextStepsList steps={result.nextSteps} />
          </div>
        </section>

        <OfficialConfirmationNotice warning={result.officialWarning} />

        {result.relatedGuide ? <RelatedGuideCallout guideId={result.relatedGuide} /> : null}
      </div>
    </article>
  );
}
