type ImportantPointsListProps = {
  items: string[];
};

const splitFirstSentence = (item: string) => {
  const match = item.match(/^(.+?[.!?])\s+(.*)$/);
  return match ? { lead: match[1], rest: match[2] } : { lead: item, rest: "" };
};

function WarningIcon() {
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
      <path d="m12 3 10 18H2L12 3Z" />
      <path d="M12 9v5" />
      <path d="M12 18h.01" />
    </svg>
  );
}

export function ImportantPointsList({ items }: ImportantPointsListProps) {
  if (!items.length) {
    return (
      <p className="rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-200">
        No important points are available yet.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {items.map((item) => {
        const { lead, rest } = splitFirstSentence(item);

        return (
          <li
            key={item}
            className="flex gap-3 rounded-2xl border border-amber-200 bg-white px-4 py-3 text-sm leading-6 text-slate-800 shadow-sm"
          >
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-800 ring-1 ring-amber-200">
              <WarningIcon />
            </span>
            <span>
              <strong className="font-semibold text-slate-950">{lead}</strong>
              {rest ? ` ${rest}` : ""}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
