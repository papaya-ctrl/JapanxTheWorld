type NextStepsListProps = {
  steps: string[];
};

const splitFirstSentence = (step: string) => {
  const match = step.match(/^(.+?[.!?])\s+(.*)$/);
  return match ? { lead: match[1], rest: match[2] } : { lead: step, rest: "" };
};

export function NextStepsList({ steps }: NextStepsListProps) {
  if (!steps.length) {
    return (
      <p className="rounded-2xl bg-blue-50 px-4 py-3 text-sm text-blue-900 ring-1 ring-blue-200">
        No next steps are available yet.
      </p>
    );
  }

  return (
    <ol className="space-y-4">
      {steps.map((step, index) => {
        const { lead, rest } = splitFirstSentence(step);

        return (
          <li
            key={step}
            className="flex gap-3 rounded-2xl border border-blue-100 bg-blue-50 px-4 py-4 text-sm leading-6 text-slate-800"
          >
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white shadow-sm">
              {index + 1}
            </span>
            <span>
              <strong className="font-semibold text-slate-950">{lead}</strong>
              {rest ? ` ${rest}` : ""}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
