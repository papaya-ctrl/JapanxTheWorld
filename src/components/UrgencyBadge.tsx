import type { AnalysisUrgency } from "../types";

type UrgencyBadgeProps = {
  urgency: AnalysisUrgency;
};

const urgencyConfig: Record<
  AnalysisUrgency,
  { label: string; styles: string }
> = {
  low: {
    label: "Low urgency",
    styles: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  },
  important: {
    label: "Important",
    styles: "bg-amber-50 text-amber-700 ring-amber-200",
  },
  urgent: {
    label: "Urgent",
    styles: "bg-red-50 text-red-700 ring-red-200",
  },
};

export function UrgencyBadge({ urgency }: UrgencyBadgeProps) {
  const config = urgencyConfig[urgency];

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ring-1 ${config.styles}`}
    >
      {config.label}
    </span>
  );
}
