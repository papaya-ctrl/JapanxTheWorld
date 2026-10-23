import type { DocumentUploadResult, ExtractedField, SourceEvidence } from "../types";
import { formatDocumentDate } from "../lib/documentDates";

export const formatYen = (value: number) => `JPY ${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value)}`;
const panel = "space-y-4 rounded-[28px] border border-slate-200 bg-slate-50 p-5 sm:p-6";

function SourceSnippets({ ids, evidence }: { ids: string[]; evidence: SourceEvidence[] }) {
  const relevant = evidence.filter(e => ids.includes(e.id));
  if (!relevant.length) return null;
  return <details className="mt-3 text-sm">
    <summary className="w-fit cursor-pointer rounded text-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600">View original source text</summary>
    <ul className="mt-3 space-y-2">
      {relevant.map(e => {
        // Only referenced boxes are inspectable. Large prose blocks and long
        // numeric identifiers are withheld instead of exposing a raw OCR dump.
        const safe = e.text.length <= 180 && !/(?:\d[ -]?){12,}/.test(e.text)
          && !/^\s*\d{8,}\s*$/.test(e.text);
        return <li key={e.id} className="rounded-2xl border border-slate-200 bg-white p-3">
          <p className="text-xs font-medium text-slate-500">Page {e.page}</p>
          {safe ? <blockquote lang="ja" className="mt-1 whitespace-pre-wrap break-words text-slate-800">{e.text}</blockquote>
            : <p className="mt-1 text-slate-600">Check this field on the original document; the source block includes additional or identifier-like text.</p>}
        </li>;
      })}
    </ul>
  </details>;
}

function FieldStatus({ field }: { field: ExtractedField }) {
  return <>
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${field.status === "verified" ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-900"}`}>
      {field.status === "verified" ? "Verified field" : "Unverified field"}
    </span>
    {field.occurrences > 1 ? <p className="mt-2 text-xs text-slate-600">Repeated in {field.occurrences} sections; shown once.</p> : null}
    {field.reasons.length ? <ul className="mt-2 space-y-1 text-sm text-amber-900">{field.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul> : null}
  </>;
}

export function ExtractedDocumentFields({ result }: { result: DocumentUploadResult }) {
  return <>
    {result.documentTypeEvidenceIds.length ? <SourceSnippets ids={result.documentTypeEvidenceIds} evidence={result.evidence} /> : null}
    <section aria-labelledby="deadlines-heading" className={panel}>
      <h2 id="deadlines-heading" className="text-xl font-semibold text-slate-950">Deadlines</h2>
      <div className="rounded-2xl border border-blue-100 bg-white p-4">
        <h3 className="text-sm font-semibold text-blue-800">Primary deadline</h3>
        {result.primaryDeadline ? <time dateTime={result.primaryDeadline} className="mt-1 block text-lg font-semibold text-slate-900">{formatDocumentDate(result.primaryDeadline)}</time>
          : <p className="mt-1 text-sm text-slate-700">{result.deadlines.length ? "A primary deadline has not been conclusively selected." : "No deadline was extracted."}</p>}
      </div>
      {result.deadlines.length ? <ul className="grid gap-3 sm:grid-cols-2">{result.deadlines.map((field, index) => <li key={index} className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4">
        <h3 className="font-semibold text-slate-900">{field.label}</h3>
        <p className="my-2 text-base text-slate-800">{field.date ? <>{field.status === "unverified" ? "Candidate date: " : ""}<time dateTime={field.date}>{formatDocumentDate(field.date)}</time></> : "Date unverified"}</p>
        <FieldStatus field={field} />
        <SourceSnippets ids={field.evidenceIds} evidence={result.evidence} />
      </li>)}</ul> : <p className="text-sm text-slate-600">No supported deadline fields are available.</p>}
    </section>
    <section aria-labelledby="amounts-heading" className={panel}>
      <h2 id="amounts-heading" className="text-xl font-semibold text-slate-950">Amounts</h2>
      <div className="rounded-2xl border border-blue-100 bg-white p-4">
        <h3 className="text-sm font-semibold text-blue-800">Primary amount</h3>
        <p className="mt-1 text-sm text-slate-700">{result.primaryAmount !== null ? formatYen(result.primaryAmount)
          : result.amounts.length ? "The primary amount has not been conclusively selected. Review the labeled fields below." : "No amount was extracted."}</p>
      </div>
      {result.amounts.length ? <ul className="grid gap-3 sm:grid-cols-2">{result.amounts.map((field, index) => <li key={index} className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4">
        <h3 className="font-semibold text-slate-900">{field.label}</h3>
        <p className="my-2 text-base text-slate-800">{field.value !== null ? `${field.status === "unverified" ? "Candidate value: " : ""}${formatYen(field.value)}` : "Amount unverified"}</p>
        <FieldStatus field={field} />
        <SourceSnippets ids={field.evidenceIds} evidence={result.evidence} />
      </li>)}</ul> : <p className="text-sm text-slate-600">No supported monetary fields are available.</p>}
    </section>
  </>;
}
