import { Link } from "react-router";
import type { AnalysisUrgency } from "../types";

type ResultSourceBadgeProps = {
  source: "template" | "ai";
};

type DeadlineStatusProps = {
  deadline: string | null;
  urgency: AnalysisUrgency;
};

type OfficialConfirmationNoticeProps = {
  warning: string;
};

type RelatedGuideCalloutProps = {
  guideId: string;
};

const urgencyConfig: Record<
  AnalysisUrgency,
  {
    label: string;
    panel: string;
    icon: string;
  }
> = {
  urgent: {
    label: "Urgent",
    panel: "border-red-200 bg-red-50",
    icon: "bg-red-100 text-red-700 ring-red-200",
  },
  important: {
    label: "Important",
    panel: "border-amber-200 bg-amber-50",
    icon: "bg-amber-100 text-amber-800 ring-amber-200",
  },
  low: {
    label: "Low urgency",
    panel: "border-blue-200 bg-blue-50",
    icon: "bg-blue-100 text-blue-700 ring-blue-200",
  },
};

function WarningIcon() {
  return (
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
  );
}

function ClockIcon() {
  return (
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
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
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

function ArrowIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
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

const formatDeadline = (deadline: string | null) => {
  if (!deadline) {
    return "No clear deadline detected";
  }

  return new Date(deadline).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
};

export function ResultSourceBadge({ source }: ResultSourceBadgeProps) {
  const sourceLabel =
    source === "template" ? "Verified Guide" : "AI-assisted Explanation";
  const sourceHelp =
    source === "template"
      ? "Based on JapanxTheWorld trusted content"
      : "Please confirm important details with official sources";

  return (
    <div className="rounded-2xl bg-slate-950 px-4 py-3 text-white shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-white">
        {sourceLabel}
      </p>
      <p className="mt-1 text-xs leading-5 text-white/75">{sourceHelp}</p>
    </div>
  );
}

export function DeadlineStatus({ deadline, urgency }: DeadlineStatusProps) {
  const config = urgencyConfig[urgency];

  return (
    <section
      role="status"
      aria-label="Deadline and urgency"
      className={`rounded-3xl border px-5 py-4 ${config.panel}`}
    >
      <div className="flex gap-3">
        <span
          className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full ring-1 ${config.icon}`}
        >
          {urgency === "urgent" ? <WarningIcon /> : <ClockIcon />}
        </span>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-700">
            Deadline / urgency
          </p>
          <p className="mt-2 text-base font-semibold text-slate-950">
            {formatDeadline(deadline)}
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-700">
            Status: {config.label}
          </p>
        </div>
      </div>
    </section>
  );
}

export function OfficialConfirmationNotice({
  warning,
}: OfficialConfirmationNoticeProps) {
  return (
    <section
      role="note"
      aria-label="Official confirmation warning"
      className="rounded-3xl border border-red-200 bg-red-50 px-5 py-5 shadow-sm"
    >
      <div className="flex gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-700 ring-1 ring-red-200">
          <WarningIcon />
        </span>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-red-800">
            Official confirmation
          </p>
          <h2 className="mt-1 text-xl font-semibold text-slate-950">
            Confirm before acting
          </h2>
          <p className="mt-3 text-sm leading-7 text-red-900">{warning}</p>
          <p className="mt-3 text-sm leading-7 text-red-900">
            Important tax, immigration, pension, labor, or municipal details should
            be checked with the official organization or a trusted support desk.
          </p>
        </div>
      </div>
    </section>
  );
}

export function RelatedGuideCallout({ guideId }: RelatedGuideCalloutProps) {
  return (
    <section className="rounded-3xl border border-blue-200 bg-blue-50 px-5 py-5 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-3">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-700 ring-1 ring-blue-200">
            <CheckIcon />
          </span>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-900">
              Full guide available
            </p>
            <h2 className="mt-1 text-xl font-semibold text-slate-950">
              Read the step-by-step guide
            </h2>
            <p className="mt-2 text-sm leading-6 text-blue-950/80">
              Open the related Life Guide for more context, documents to prepare,
              common mistakes, and official source links.
            </p>
          </div>
        </div>
        <Link
          to={`/life-guides/${guideId}`}
          className="inline-flex w-fit items-center gap-2 rounded-full bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          Open guide
          <ArrowIcon />
        </Link>
      </div>
    </section>
  );
}
