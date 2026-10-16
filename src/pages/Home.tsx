import { Link } from "react-router";
import { FeatureCard } from "../components/FeatureCard";

const featureCards = [
  {
    title: "Document Decoder",
    description:
      "Upload a Japanese document or paste text and receive a simple English explanation, clear points, and next steps.",
    ctaLabel: "Open decoder",
    ctaTo: "/document-decoder",
    accent: "blue" as const,
  },
  {
    title: "Life Procedure Guides",
    description:
      "Explore practical guides for city hall tasks, insurance notices, tax questions, and daily life procedures.",
    ctaLabel: "Browse guides",
    ctaTo: "/life-guides",
    accent: "blue" as const,
  },
  {
    title: "Dashboard Checklist",
    description:
      "Track what you still need to do and keep important tasks in one calm, organized place.",
    ctaLabel: "Go to dashboard",
    ctaTo: "/dashboard",
    accent: "red" as const,
  },
];

export function Home() {
  return (
    <div className="space-y-16">
      <section className="grid gap-8 rounded-[36px] bg-gradient-to-br from-blue-600 via-blue-500 to-slate-900 px-6 py-10 text-white shadow-2xl shadow-blue-900/20 sm:px-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-end">
        <div className="space-y-5">
          <span className="inline-flex rounded-full bg-white/15 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white/90">
            Frontend mock-first build
          </span>
          <h1 className="max-w-2xl text-4xl font-semibold leading-tight sm:text-5xl">
            A calmer way to understand life and documents in Japan
          </h1>
          <p className="max-w-2xl text-base leading-7 text-blue-50/90">
            JapanxTheWorld is designed for foreign students and workers who need
            clear next steps, structured guides, and trusted reminders to confirm
            important procedures with official support.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/document-decoder"
              className="inline-flex rounded-full bg-white px-5 py-3 text-sm font-semibold text-blue-700 transition hover:bg-blue-50"
            >
              Start with a document
            </Link>
            <Link
              to="/help-center"
              className="inline-flex rounded-full border border-white/20 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              Find official support
            </Link>
          </div>
        </div>

        <div className="grid gap-4">
          <div className="rounded-[28px] bg-white/95 p-5 text-slate-900">
            <p className="text-sm font-semibold text-blue-700">What you can do</p>
            <ul className="mt-3 space-y-3 text-sm leading-6 text-slate-600">
              <li>Understand a document without reading complex Japanese alone.</li>
              <li>Follow practical guides for common official procedures.</li>
              <li>Track important tasks with a personal checklist.</li>
            </ul>
          </div>
          <div className="rounded-[28px] border border-red-200 bg-red-50 p-5">
            <p className="text-sm font-semibold text-red-700">Safety reminder</p>
            <p className="mt-2 text-sm leading-6 text-red-700/90">
              This service supports understanding. Final decisions about
              immigration, tax, insurance, legal, medical, or financial matters
              should always be confirmed with official sources.
            </p>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-700">
              Main features
            </p>
            <h2 className="mt-2 text-3xl font-semibold text-slate-900">
              Where to start
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-slate-600">
            Each area is designed to reduce confusion and give you one clear next
            action.
          </p>
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          {featureCards.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-3">
        {[
          {
            title: "Simple English",
            text: "Interface copy stays direct and easy to scan, especially on mobile screens.",
          },
          {
            title: "Mock-first workflow",
            text: "The frontend works now with mock data and is ready to connect to real APIs later.",
          },
          {
            title: "Official confirmation built in",
            text: "Important results always remind users to verify deadlines and procedures with trusted sources.",
          },
        ].map((item) => (
          <article
            key={item.title}
            className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm"
          >
            <h3 className="text-lg font-semibold text-slate-900">{item.title}</h3>
            <p className="mt-3 text-sm leading-6 text-slate-600">{item.text}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
