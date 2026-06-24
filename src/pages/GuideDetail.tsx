import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import { getGuideById, getResources } from "../api/client";
import { OfficialResourceCard } from "../components/OfficialResourceCard";
import type { ApiError, GuideDetail as GuideDetailType, OfficialResource, UiStatus } from "../types";

export function GuideDetail() {
  const { guideId = "" } = useParams();
  const [status, setStatus] = useState<UiStatus>("loading");
  const [guide, setGuide] = useState<GuideDetailType | null>(null);
  const [resources, setResources] = useState<OfficialResource[]>([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let active = true;

    const loadGuide = async () => {
      setStatus("loading");
      setErrorMessage("");

      try {
        const [nextGuide, nextResources] = await Promise.all([
          getGuideById(guideId),
          getResources(),
        ]);
        if (!active) {
          return;
        }
        setGuide(nextGuide);
        setResources(nextResources);
        setStatus("success");
      } catch (error) {
        if (!active) {
          return;
        }
        const apiError = error as ApiError;
        setErrorMessage(apiError.message || "Guide data could not be loaded.");
        setStatus(apiError.code === "GUIDE_NOT_FOUND" ? "empty" : "error");
      }
    };

    void loadGuide();

    return () => {
      active = false;
    };
  }, [guideId]);

  const relatedResources = useMemo<OfficialResource[]>(() => {
    if (!guide) {
      return [];
    }
    return resources.filter((resource) =>
      guide.officialResourceIds.includes(resource.id),
    );
  }, [guide, resources]);

  if (status === "loading") {
    return (
      <div className="space-y-5">
        <div className="h-44 animate-pulse rounded-[32px] bg-white ring-1 ring-slate-200" />
        <div className="h-72 animate-pulse rounded-[32px] bg-white ring-1 ring-slate-200" />
      </div>
    );
  }

  if (status === "empty") {
    return (
      <section className="rounded-[32px] border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-lg font-semibold text-slate-900">Guide not found</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">{errorMessage}</p>
        <Link
          to="/life-guides"
          className="mt-6 inline-flex rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700"
        >
          Back to guides
        </Link>
      </section>
    );
  }

  if (status === "error" || !guide) {
    return (
      <section className="rounded-[32px] border border-red-100 bg-red-50 p-8 shadow-sm">
        <p className="text-lg font-semibold text-red-700">
          Guide data could not be loaded
        </p>
        <p className="mt-2 text-sm leading-6 text-red-700/90">{errorMessage}</p>
      </section>
    );
  }

  return (
    <div className="space-y-8">
      <section className="rounded-[36px] bg-white px-6 py-8 ring-1 ring-slate-200 sm:px-8">
        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-blue-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-blue-700">
            {guide.category}
          </span>
          <span className="text-sm font-medium text-slate-500">
            {guide.estimatedReadMinutes} min read
          </span>
        </div>
        <h1 className="mt-4 text-3xl font-semibold text-slate-900 sm:text-4xl">
          {guide.title}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
          {guide.summary}
        </p>
        <div className="mt-5 rounded-[28px] border border-slate-200 bg-slate-50 px-5 py-4">
          <p className="text-sm font-semibold text-slate-900">Who this is for</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{guide.audience}</p>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <article className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">
            Required documents
          </h2>
          <ul className="mt-4 space-y-3">
            {guide.requiredDocuments.map((document) => (
              <li
                key={document}
                className="rounded-2xl bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700"
              >
                {document}
              </li>
            ))}
          </ul>
        </article>

        <article className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Steps</h2>
          <ol className="mt-4 space-y-4">
            {guide.steps.map((step, index) => (
              <li key={step} className="flex gap-3 rounded-2xl bg-slate-50 px-4 py-4">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
                  {index + 1}
                </span>
                <span className="text-sm leading-6 text-slate-700">{step}</span>
              </li>
            ))}
          </ol>
        </article>
      </section>

      <section className="space-y-5">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-red-700">
            Official resources
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">
            Confirm important steps with trusted sources
          </h2>
        </div>
        <div className="grid gap-5 md:grid-cols-2">
          {relatedResources.map((resource) => (
            <OfficialResourceCard key={resource.id} resource={resource} />
          ))}
        </div>
      </section>
    </div>
  );
}
