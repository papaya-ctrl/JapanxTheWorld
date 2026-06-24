import { useEffect, useState } from "react";
import { getGuides } from "../api/client";
import { GuideCard } from "../components/GuideCard";
import type { ApiError, GuideSummary, UiStatus } from "../types";

export function LifeGuides() {
  const [status, setStatus] = useState<UiStatus>("loading");
  const [guides, setGuides] = useState<GuideSummary[]>([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let active = true;

    const loadGuides = async () => {
      setStatus("loading");
      setErrorMessage("");

      try {
        const nextGuides = await getGuides();
        if (!active) {
          return;
        }
        setGuides(nextGuides);
        setStatus(nextGuides.length ? "success" : "empty");
      } catch (error) {
        if (!active) {
          return;
        }
        const apiError = error as ApiError;
        setErrorMessage(
          apiError.message || "Something went wrong while loading guides.",
        );
        setStatus("error");
      }
    };

    void loadGuides();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-4 rounded-[36px] bg-white px-6 py-8 ring-1 ring-slate-200 sm:px-8">
        <span className="inline-flex w-fit rounded-full bg-blue-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-blue-700">
          Life Guides
        </span>
        <h1 className="text-3xl font-semibold text-slate-900 sm:text-4xl">
          Practical guides for common procedures in Japan
        </h1>
        <p className="max-w-3xl text-sm leading-7 text-slate-600">
          Browse clear, step-by-step guides for city hall procedures, payment
          notices, insurance tasks, and career preparation.
        </p>
      </section>

      {status === "loading" ? (
        <div className="grid gap-5 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="h-56 animate-pulse rounded-[28px] bg-white shadow-sm ring-1 ring-slate-200"
            />
          ))}
        </div>
      ) : null}

      {status === "error" ? (
        <div className="rounded-[28px] border border-red-100 bg-red-50 px-6 py-5">
          <p className="text-sm font-semibold text-red-700">Could not load guides</p>
          <p className="mt-2 text-sm text-red-700/90">{errorMessage}</p>
        </div>
      ) : null}

      {status === "empty" ? (
        <div className="rounded-[28px] border border-slate-200 bg-white px-6 py-8 text-center">
          <p className="text-lg font-semibold text-slate-900">
            No guides are available yet.
          </p>
          <p className="mt-2 text-sm text-slate-600">
            New guide content can be added here later without changing the page
            structure.
          </p>
        </div>
      ) : null}

      {status === "success" ? (
        <div className="grid gap-5 md:grid-cols-2">
          {guides.map((guide) => (
            <GuideCard key={guide.id} guide={guide} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
