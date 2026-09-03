import type { OfficialResource } from "../types";
import { darkPrimaryCtaClass } from "./ctaStyles";

type OfficialResourceCardProps = {
  resource: OfficialResource;
};

export function OfficialResourceCard({ resource }: OfficialResourceCardProps) {
  return (
    <article className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <span className="rounded-full bg-red-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-red-700">
            {resource.category}
          </span>
          <span className="text-xs font-medium text-slate-500">Official link</span>
        </div>
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-slate-900">{resource.title}</h3>
          <p className="text-sm leading-6 text-slate-600">{resource.description}</p>
        </div>
        <a
          href={resource.url}
          target="_blank"
          rel="noreferrer"
          className={darkPrimaryCtaClass}
        >
          Open official website
        </a>
      </div>
    </article>
  );
}
