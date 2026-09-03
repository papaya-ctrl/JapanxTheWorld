import { Link } from "react-router";
import { darkPrimaryCtaClass } from "./ctaStyles";

type FeatureCardProps = {
  title: string;
  description: string;
  ctaLabel: string;
  ctaTo: string;
  accent?: "blue" | "red";
};

export function FeatureCard({
  title,
  description,
  ctaLabel,
  ctaTo,
  accent = "blue",
}: FeatureCardProps) {
  const accentStyles =
    accent === "red"
      ? "from-red-50 to-white ring-red-100"
      : "from-blue-50 to-white ring-blue-100";

  return (
    <article
      className={`rounded-[28px] bg-gradient-to-br ${accentStyles} p-6 shadow-sm ring-1`}
    >
      <div className="flex h-full flex-col justify-between gap-6">
        <div className="space-y-3">
          <h3 className="text-xl font-semibold text-slate-900">{title}</h3>
          <p className="text-sm leading-6 text-slate-600">{description}</p>
        </div>
        <Link
          to={ctaTo}
          className={`${darkPrimaryCtaClass} w-fit items-center`}
        >
          {ctaLabel}
        </Link>
      </div>
    </article>
  );
}
