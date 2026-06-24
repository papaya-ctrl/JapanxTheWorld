type NextStepsListProps = {
  steps: string[];
};

export function NextStepsList({ steps }: NextStepsListProps) {
  if (!steps.length) {
    return (
      <p className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-500">
        No next steps are available yet.
      </p>
    );
  }

  return (
    <ol className="space-y-3">
      {steps.map((step, index) => (
        <li
          key={step}
          className="flex gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-700"
        >
          <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
            {index + 1}
          </span>
          <span>{step}</span>
        </li>
      ))}
    </ol>
  );
}
