import type { ReactNode } from "react";
import type { GuideOfficialSource } from "../types";

type IconProps = {
  className?: string;
};

type NoticeTone = "important" | "warning" | "deadline" | "action" | "confirmation";

type NoticeProps = {
  title: string;
  children: ReactNode;
  label?: string;
};

type ListProps = {
  title: string;
  items: string[];
};

type OfficialConfirmationCardProps = {
  body: string;
  sources?: GuideOfficialSource[];
};

const toneStyles: Record<
  NoticeTone,
  {
    article: string;
    icon: string;
    label: string;
  }
> = {
  important: {
    article: "border-red-200 bg-red-50",
    icon: "bg-red-100 text-red-700 ring-red-200",
    label: "text-red-800",
  },
  warning: {
    article: "border-red-200 bg-red-50",
    icon: "bg-red-100 text-red-700 ring-red-200",
    label: "text-red-800",
  },
  deadline: {
    article: "border-amber-200 bg-amber-50",
    icon: "bg-amber-100 text-amber-800 ring-amber-200",
    label: "text-amber-900",
  },
  action: {
    article: "border-blue-200 bg-blue-50",
    icon: "bg-blue-100 text-blue-700 ring-blue-200",
    label: "text-blue-900",
  },
  confirmation: {
    article: "border-slate-300 bg-slate-50",
    icon: "bg-white text-slate-700 ring-slate-200",
    label: "text-slate-900",
  },
};

function WarningIcon({ className = "" }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
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
  );
}

function ClockIcon({ className = "" }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function ArrowIcon({ className = "" }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  );
}

function CheckIcon({ className = "" }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m5 12 4 4L19 6" />
    </svg>
  );
}

function DocumentIcon({ className = "" }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7Z" />
      <path d="M14 2v5h5" />
      <path d="M9 13h6" />
      <path d="M9 17h4" />
    </svg>
  );
}

function ShieldIcon({ className = "" }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-5" />
    </svg>
  );
}

function Notice({
  tone,
  title,
  label,
  children,
}: NoticeProps & { tone: NoticeTone }) {
  const styles = toneStyles[tone];

  const Icon =
    tone === "deadline"
      ? ClockIcon
      : tone === "action"
        ? ArrowIcon
        : tone === "confirmation"
          ? ShieldIcon
          : WarningIcon;

  return (
    <article
      role="note"
      aria-label={label ?? title}
      className={`rounded-[28px] border p-5 shadow-sm sm:p-6 ${styles.article}`}
    >
      <div className="flex gap-4">
        <span
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ring-1 ${styles.icon}`}
        >
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          {label ? (
            <p className={`text-xs font-bold uppercase tracking-[0.16em] ${styles.label}`}>
              {label}
            </p>
          ) : null}
          <h2 className="mt-1 text-xl font-semibold text-slate-950">{title}</h2>
          <div className="mt-3 text-sm leading-7 text-slate-700">{children}</div>
        </div>
      </div>
    </article>
  );
}

export function ImportantNotice({ title, children }: NoticeProps) {
  return (
    <Notice tone="important" title={title} label="Important rule">
      {children}
    </Notice>
  );
}

export function WarningNotice({ title, children }: NoticeProps) {
  return (
    <Notice tone="warning" title={title} label="Warning">
      {children}
    </Notice>
  );
}

export function DeadlineNotice({ title, children }: NoticeProps) {
  return (
    <Notice tone="deadline" title={title} label="Time-sensitive">
      {children}
    </Notice>
  );
}

export function ActionNotice({ title, children }: NoticeProps) {
  return (
    <Notice tone="action" title={title} label="Recommended next action">
      {children}
    </Notice>
  );
}

const splitFirstSentence = (step: string) => {
  const match = step.match(/^(.+?[.!?])\s+(.*)$/);
  return match ? { lead: match[1], rest: match[2] } : { lead: step, rest: "" };
};

export function NumberedSteps({ title, items }: ListProps) {
  return (
    <article className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-xl font-semibold text-slate-950">{title}</h2>
      <ol className="mt-5 space-y-4">
        {items.map((item, index) => {
          const { lead, rest } = splitFirstSentence(item);

          return (
            <li key={item} className="flex gap-4 rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-200">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">
                {index + 1}
              </span>
              <p className="text-sm leading-7 text-slate-700">
                <strong className="font-semibold text-slate-950">{lead}</strong>
                {rest ? ` ${rest}` : ""}
              </p>
            </li>
          );
        })}
      </ol>
    </article>
  );
}

export function ChecklistList({ title, items }: ListProps) {
  return (
    <article className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-xl font-semibold text-slate-950">{title}</h2>
      <ul className="mt-4 space-y-2.5">
        {items.map((item) => (
          <li key={item} className="flex gap-3 rounded-2xl bg-slate-50 px-4 py-3 ring-1 ring-slate-200">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200">
              <CheckIcon className="h-4 w-4" />
            </span>
            <span className="text-sm leading-6 text-slate-700">{item}</span>
          </li>
        ))}
      </ul>
    </article>
  );
}

export function RequiredDocumentsList({ title, items }: ListProps) {
  return (
    <article className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-xl font-semibold text-slate-950">{title}</h2>
      <ul className="mt-4 divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200">
        {items.map((item) => (
          <li key={item} className="flex gap-3 bg-slate-50 px-4 py-3">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-slate-700 ring-1 ring-slate-200">
              <DocumentIcon className="h-4 w-4" />
            </span>
            <span className="text-sm leading-6 text-slate-700">{item}</span>
          </li>
        ))}
      </ul>
    </article>
  );
}

export function CommonMistakesList({ title, items }: ListProps) {
  return (
    <article className="rounded-[28px] border border-red-100 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-xl font-semibold text-slate-950">{title}</h2>
      <ul className="mt-4 space-y-3">
        {items.map((item) => (
          <li key={item} className="flex gap-3 rounded-2xl bg-red-50 px-4 py-3 ring-1 ring-red-100">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-700 ring-1 ring-red-200">
              <WarningIcon className="h-4 w-4" />
            </span>
            <span className="text-sm leading-6 text-slate-800">{item}</span>
          </li>
        ))}
      </ul>
    </article>
  );
}

export function OfficialConfirmationCard({
  body,
  sources = [],
}: OfficialConfirmationCardProps) {
  return (
    <Notice
      tone="confirmation"
      title="Official confirmation / source section"
      label="Official confirmation"
    >
      <p>{body}</p>
      {sources.length ? (
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {sources.map((source) => (
            <a
              key={source.url}
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="rounded-2xl border border-slate-200 bg-white p-4 transition hover:border-blue-200 hover:bg-blue-50 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              <p className="text-sm font-semibold text-slate-950">{source.title}</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">{source.organization}</p>
            </a>
          ))}
        </div>
      ) : null}
    </Notice>
  );
}
