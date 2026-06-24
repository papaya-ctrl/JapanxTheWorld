type ImportantPointsListProps = {
  items: string[];
};

export function ImportantPointsList({ items }: ImportantPointsListProps) {
  if (!items.length) {
    return (
      <p className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-500">
        No important points are available yet.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li
          key={item}
          className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-700"
        >
          {item}
        </li>
      ))}
    </ul>
  );
}
