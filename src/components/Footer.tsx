type FooterProps = {
  supportNote?: string;
};

export function Footer({
  supportNote = "This platform is a support tool. Please confirm important procedures with official sources.",
}: FooterProps) {
  return (
    <footer className="border-t border-slate-200 bg-white/85">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="grid gap-6 md:grid-cols-[1.4fr_1fr]">
          <div className="space-y-3">
            <p className="text-base font-semibold text-slate-900">
              JapanxTheWorld
            </p>
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              Built to reduce confusion around documents, procedures, and daily
              life steps for foreign students and workers in Japan.
            </p>
          </div>
          <div className="rounded-3xl border border-red-100 bg-red-50 px-5 py-4">
            <p className="text-sm font-semibold text-red-700">Important note</p>
            <p className="mt-2 text-sm leading-6 text-red-700/90">
              {supportNote}
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
