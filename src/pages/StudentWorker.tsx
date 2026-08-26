import { useEffect, useState } from "react";
import { Link } from "react-router";
import { getResources } from "../api/client";
import { FeatureCard } from "../components/FeatureCard";
import { OfficialResourceCard } from "../components/OfficialResourceCard";
import type { ApiError, OfficialResource, UiStatus } from "../types";

const timeline = [
  "Prepare your resume, deadlines, and interview schedule early.",
  "Collect important school and residence documents in one place.",
  "Confirm work-related residence status information with official or trusted support.",
  "Keep a checklist for deadlines, applications, and official procedures.",
];

export function StudentWorker() {
  const [status, setStatus] = useState<UiStatus>("loading");
  const [relatedResources, setRelatedResources] = useState<OfficialResource[]>([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let active = true;

    const loadResources = async () => {
      try {
        const resources = await getResources();
        if (!active) {
          return;
        }
        const filteredResources = resources.filter((resource) =>
          ["isa-main", "hello-work"].includes(resource.id),
        );
        setRelatedResources(filteredResources);
        setStatus(filteredResources.length ? "success" : "empty");
      } catch (error) {
        if (!active) {
          return;
        }
        const apiError = error as ApiError;
        setErrorMessage(
          apiError.message || "Official support links could not be loaded.",
        );
        setStatus("error");
      }
    };

    void loadResources();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-10">
      <section className="grid gap-6 rounded-[36px] bg-gradient-to-br from-white to-blue-50 px-6 py-8 ring-1 ring-slate-200 sm:px-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <span className="inline-flex rounded-full bg-blue-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-blue-700">
            Student-to-Worker Guide
          </span>
          <h1 className="mt-4 text-3xl font-semibold text-slate-900 sm:text-4xl">
            Plan the move from student life to working life in Japan
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-600">
            This page helps you organize job hunting, document preparation, and
            official confirmation steps before graduation and employment.
          </p>
        </div>

        <div className="rounded-[28px] border border-red-100 bg-red-50 p-5">
          <p className="text-sm font-semibold text-red-700">Important note</p>
          <p className="mt-2 text-sm leading-6 text-red-700/90">
            Work status, visa-related procedures, and final legal requirements
            must always be confirmed with official immigration and career support
            sources.
          </p>
        </div>
      </section>

      <section className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-semibold text-slate-900">Suggested timeline</h2>
        <ol className="mt-5 space-y-4">
          {timeline.map((item, index) => (
            <li key={item} className="flex gap-4 rounded-2xl bg-slate-50 px-4 py-4">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white">
                {index + 1}
              </span>
              <span className="text-sm leading-6 text-slate-700">{item}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <FeatureCard
          title="Track deadlines in the dashboard"
          description="Use the checklist to keep interviews, office visits, and document tasks visible."
          ctaLabel="Open dashboard"
          ctaTo="/dashboard"
          accent="blue"
        />
        <FeatureCard
          title="Read more life guides"
          description="Review related practical guides before major procedures or deadline-heavy periods."
          ctaLabel="Browse life guides"
          ctaTo="/life-guides"
          accent="red"
        />
      </section>

      <section className="space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-red-700">
              Trusted support
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">
              Official places to confirm next steps
            </h2>
          </div>
          <Link
            to="/help-center"
            className="inline-flex rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
          >
            Open Help Center
          </Link>
        </div>
        {status === "loading" ? (
          <div className="grid gap-5 md:grid-cols-2" aria-live="polite">
            {Array.from({ length: 2 }).map((_, index) => (
              <div
                key={index}
                className="h-56 animate-pulse rounded-[28px] bg-white shadow-sm ring-1 ring-slate-200"
              />
            ))}
          </div>
        ) : null}

        {status === "error" ? (
          <div role="alert" className="rounded-[28px] border border-red-100 bg-red-50 px-6 py-5">
            <p className="text-sm font-semibold text-red-700">
              Support links could not be loaded
            </p>
            <p className="mt-2 text-sm text-red-700/90">{errorMessage}</p>
          </div>
        ) : null}

        {status === "empty" ? (
          <div className="rounded-[28px] border border-slate-200 bg-white px-6 py-5">
            <p className="text-sm font-semibold text-slate-900">
              No related support links are available yet.
            </p>
          </div>
        ) : null}

        {status === "success" ? (
          <div className="grid gap-5 md:grid-cols-2">
            {relatedResources.map((resource) => (
              <OfficialResourceCard key={resource.id} resource={resource} />
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
