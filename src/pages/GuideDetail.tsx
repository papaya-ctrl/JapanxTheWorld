import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import {
  ActionNotice,
  ChecklistList,
  CommonMistakesList,
  DeadlineNotice,
  ImportantNotice,
  NumberedSteps,
  OfficialConfirmationCard,
  RequiredDocumentsList,
  WarningNotice,
} from "../components/GuideDetailBlocks";
import { getGuideById } from "../api/client";
import type { ApiError, GuideDetail as GuideDetailType, GuideSection, UiStatus } from "../types";

const timeSensitivePattern =
  /deadline|due date|period of stay|start date|timing|last day|before starting|before accepting|期限|納期限/i;

const getSection = (guide: GuideDetailType, sectionId: string) =>
  guide.sections.find((section) => section.id === sectionId);

const getSectionItems = (section?: GuideSection) => section?.items ?? [];

const getTimeSensitiveItems = (guide: GuideDetailType) =>
  guide.sections
    .flatMap((section) => [
      section.body ?? "",
      ...(section.items ?? []),
    ])
    .filter((item) => timeSensitivePattern.test(item))
    .slice(0, 3);

function StandardSection({ section }: { section: GuideSection }) {
  return (
    <article className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-xl font-semibold text-slate-950">{section.title}</h2>
      {section.body ? (
        <p className="mt-3 text-sm leading-7 text-slate-700">{section.body}</p>
      ) : null}
      {section.items?.length ? (
        <ul className="mt-4 space-y-3">
          {section.items.map((item) => (
            <li key={item} className="flex gap-3 text-sm leading-6 text-slate-700">
              <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-blue-500" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

export function GuideDetail() {
  const { guideId = "" } = useParams();
  const [status, setStatus] = useState<UiStatus>("loading");
  const [guide, setGuide] = useState<GuideDetailType | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let active = true;

    const loadGuide = async () => {
      setStatus("loading");
      setErrorMessage("");

      try {
        const nextGuide = await getGuideById(guideId);
        if (!active) {
          return;
        }
        setGuide(nextGuide);
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

  const guideSections = useMemo(() => {
    if (!guide) {
      return null;
    }

    return {
      whatThisIs: getSection(guide, "what-this-is"),
      whoThisIsFor: getSection(guide, "who-this-is-for"),
      whyThisMatters: getSection(guide, "why-this-matters"),
      whatToCheckFirst: getSection(guide, "what-to-check-first"),
      requiredDocuments: getSection(guide, "required-documents"),
      steps: getSection(guide, "step-by-step-actions"),
      commonMistakes: getSection(guide, "common-mistakes"),
      exampleSituation: getSection(guide, "example-situation"),
      importantWarning: getSection(guide, "important-warning"),
      officialConfirmation: getSection(guide, "official-confirmation"),
      timeSensitiveItems: getTimeSensitiveItems(guide),
    };
  }, [guide]);

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
          className="mt-6 inline-flex rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
        >
          Back to guides
        </Link>
      </section>
    );
  }

  if (status === "error" || !guide || !guideSections) {
    return (
      <section className="rounded-[32px] border border-red-100 bg-red-50 p-8 shadow-sm">
        <p className="text-lg font-semibold text-red-700">
          Guide data could not be loaded
        </p>
        <p className="mt-2 text-sm leading-6 text-red-700/90">{errorMessage}</p>
      </section>
    );
  }

  const firstAction = getSectionItems(guideSections.steps)[0];

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
        {guide.japaneseTitle ? (
          <p className="mt-2 text-base font-medium text-slate-500">
            {guide.japaneseTitle}
          </p>
        ) : null}
        <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
          {guide.summary}
        </p>
        <div className="mt-5 flex flex-wrap gap-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
          {guide.contentStatus ? (
            <span className="rounded-full bg-slate-100 px-3 py-2">
              {guide.contentStatus.replace("-", " ")}
            </span>
          ) : null}
          {guide.needsOfficialConfirmation ? (
            <span className="rounded-full bg-red-50 px-3 py-2 text-red-700 ring-1 ring-red-100">
              Official confirmation needed
            </span>
          ) : null}
          {guide.lastReviewedAt ? (
            <span className="rounded-full bg-slate-100 px-3 py-2">
              Reviewed {guide.lastReviewedAt}
            </span>
          ) : null}
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        {guideSections.importantWarning ? (
          <ImportantNotice title="Important">
            <ul className="space-y-2">
              {getSectionItems(guideSections.importantWarning).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </ImportantNotice>
        ) : null}

        {firstAction ? (
          <ActionNotice title="Start here">
            <p>{firstAction}</p>
          </ActionNotice>
        ) : null}
      </div>

      {guideSections.timeSensitiveItems.length ? (
        <DeadlineNotice title="Check timing before you act">
          <ul className="space-y-2">
            {guideSections.timeSensitiveItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </DeadlineNotice>
      ) : null}

      <section className="grid gap-5 lg:grid-cols-2">
        {guideSections.whatThisIs ? (
          <StandardSection section={guideSections.whatThisIs} />
        ) : null}
        {guideSections.whoThisIsFor ? (
          <StandardSection section={guideSections.whoThisIsFor} />
        ) : null}
        {guideSections.whyThisMatters ? (
          <ChecklistList
            title={guideSections.whyThisMatters.title}
            items={getSectionItems(guideSections.whyThisMatters)}
          />
        ) : null}
        {guideSections.whatToCheckFirst ? (
          <ChecklistList
            title={guideSections.whatToCheckFirst.title}
            items={getSectionItems(guideSections.whatToCheckFirst)}
          />
        ) : null}
      </section>

      <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        {guideSections.requiredDocuments ? (
          <RequiredDocumentsList
            title={guideSections.requiredDocuments.title}
            items={getSectionItems(guideSections.requiredDocuments)}
          />
        ) : null}
        {guideSections.steps ? (
          <NumberedSteps
            title={guideSections.steps.title}
            items={getSectionItems(guideSections.steps)}
          />
        ) : null}
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        {guideSections.commonMistakes ? (
          <CommonMistakesList
            title={guideSections.commonMistakes.title}
            items={getSectionItems(guideSections.commonMistakes)}
          />
        ) : null}
        {guideSections.exampleSituation ? (
          <StandardSection section={guideSections.exampleSituation} />
        ) : null}
      </section>

      {guideSections.importantWarning ? (
        <WarningNotice title={guideSections.importantWarning.title}>
          <ul className="space-y-2">
            {getSectionItems(guideSections.importantWarning).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </WarningNotice>
      ) : null}

      {guideSections.officialConfirmation ? (
        <OfficialConfirmationCard
          body={guideSections.officialConfirmation.body ?? ""}
          sources={guide.officialSources}
        />
      ) : null}
    </div>
  );
}
