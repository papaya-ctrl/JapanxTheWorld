import { useEffect, useMemo, useState } from "react";
import { getResources } from "../api/client";
import { OfficialResourceCard } from "../components/OfficialResourceCard";
import type { ApiError, OfficialResource, UiStatus } from "../types";

export function HelpCenter() {
  const [status, setStatus] = useState<UiStatus>("loading");
  const [resources, setResources] = useState<OfficialResource[]>([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let active = true;

    const loadResources = async () => {
      setStatus("loading");

      try {
        const nextResources = await getResources();
        if (!active) {
          return;
        }
        setResources(nextResources);
        setStatus(nextResources.length ? "success" : "empty");
      } catch (error) {
        if (!active) {
          return;
        }
        const apiError = error as ApiError;
        setErrorMessage(
          apiError.message || "Support links could not be loaded right now.",
        );
        setStatus("error");
      }
    };

    void loadResources();

    return () => {
      active = false;
    };
  }, []);

  const groupedResources = useMemo(() => {
    return resources.reduce<Record<string, OfficialResource[]>>((groups, resource) => {
      groups[resource.category] = [...(groups[resource.category] ?? []), resource];
      return groups;
    }, {});
  }, [resources]);

  return (
    <div className="space-y-8">
      <section className="rounded-[36px] bg-white px-6 py-8 ring-1 ring-slate-200 sm:px-8">
        <span className="inline-flex rounded-full bg-red-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-red-700">
          Help Center
        </span>
        <h1 className="mt-4 text-3xl font-semibold text-slate-900 sm:text-4xl">
          Official support links in one place
        </h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-600">
          Use these links when you need the final answer from trusted sources
          about immigration, insurance, city hall procedures, or work support.
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
          <p className="text-sm font-semibold text-red-700">
            Support links could not be loaded
          </p>
          <p className="mt-2 text-sm text-red-700/90">{errorMessage}</p>
        </div>
      ) : null}

      {status === "empty" ? (
        <div className="rounded-[28px] border border-slate-200 bg-white px-6 py-8 text-center">
          <p className="text-lg font-semibold text-slate-900">
            No resources are available right now.
          </p>
          <p className="mt-2 text-sm text-slate-600">
            Official resource cards can be added here later through the backend.
          </p>
        </div>
      ) : null}

      {status === "success" ? (
        <div className="space-y-8">
          {Object.entries(groupedResources).map(([category, categoryResources]) => (
            <section key={category} className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-2xl font-semibold text-slate-900">
                  {category}
                </h2>
                <span className="text-sm text-slate-500">
                  {categoryResources.length} resource
                  {categoryResources.length > 1 ? "s" : ""}
                </span>
              </div>
              <div className="grid gap-5 md:grid-cols-2">
                {categoryResources.map((resource) => (
                  <OfficialResourceCard key={resource.id} resource={resource} />
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : null}
    </div>
  );
}
