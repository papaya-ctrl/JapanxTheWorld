import { Link } from "react-router";
import type { GuideSummary } from "../types";

type GuideCardProps = {
  guide: GuideSummary;
};

export function GuideCard({ guide }: GuideCardProps) {
  return (
    <article className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
            {guide.category}
          </span>
          <span className="text-xs font-medium text-slate-500">
            {guide.estimatedReadMinutes} min read
          </span>
        </div>
        <div className="space-y-2">
          <h3 className="text-xl font-semibold text-slate-900">{guide.title}</h3>
          <p className="text-sm leading-6 text-slate-600">{guide.summary}</p>
        </div>
        <Link
          to={`/life-guides/${guide.id}`}
          className="inline-flex rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
        >
          Open guide
        </Link>
      </div>
    </article>
  );
}
