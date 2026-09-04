import type { GuideDetail, GuideSection, GuideSummary, TrustedTopic } from "../types";
import { trustedTopicsById } from "./trustedTopics";

export const GUIDE_WORDS_PER_MINUTE = 180;

type GuideConfig = {
  id: string;
  topicId: string;
  title: string;
  category: string;
  audience: string;
  whyThisMatters: string[];
  commonMistakes: string[];
  exampleSituation: string;
  officialResourceIds?: string[];
};

const countWords = (text: string) =>
  text
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;

const getGuideVisibleText = (
  guide: Omit<GuideDetail, "estimatedReadMinutes">,
) => [
  guide.title,
  guide.category,
  guide.summary,
  ...guide.sections.flatMap((section) => [
    section.title,
    section.body ?? "",
    ...(section.items ?? []),
  ]),
  ...(guide.officialSources ?? []).flatMap((source) => [
    source.title,
    source.organization,
  ]),
].join(" ");

export const calculateEstimatedReadMinutes = (
  guide: Omit<GuideDetail, "estimatedReadMinutes">,
) => Math.max(1, Math.ceil(countWords(getGuideVisibleText(guide)) / GUIDE_WORDS_PER_MINUTE));

const requireTrustedTopic = (topicId: string): TrustedTopic => {
  const topic = trustedTopicsById[topicId];

  if (!topic) {
    throw new Error(`Missing trusted topic for guide: ${topicId}`);
  }

  return topic;
};

const createSections = (
  topic: TrustedTopic,
  config: GuideConfig,
): GuideSection[] => [
  {
    id: "what-this-is",
    title: "What this is",
    body: topic.summary,
  },
  {
    id: "who-this-is-for",
    title: "Who this is for",
    body: config.audience,
  },
  {
    id: "why-this-matters",
    title: "Why this matters / why you may receive it",
    items: config.whyThisMatters,
  },
  {
    id: "what-to-check-first",
    title: "What to check first",
    items: topic.importantPoints,
  },
  {
    id: "required-documents",
    title: "Required documents",
    items: topic.requiredDocuments ?? [],
  },
  {
    id: "step-by-step-actions",
    title: "Step-by-step actions",
    items: topic.nextSteps,
  },
  {
    id: "common-mistakes",
    title: "Common mistakes",
    items: config.commonMistakes,
  },
  {
    id: "example-situation",
    title: "Example situation",
    body: config.exampleSituation,
  },
  {
    id: "important-warning",
    title: "Important warning",
    items: topic.warnings ?? [],
    variant: "warning",
  },
  {
    id: "official-confirmation",
    title: "Official confirmation / source section",
    body:
      topic.needsOfficialConfirmation
        ? "This topic can change by municipality, school, employer, personal status, or official review. Confirm the final answer with the official organization before acting."
        : "Confirm important details with the official organization before acting.",
    variant: "confirmation",
  },
];

const createGuide = (config: GuideConfig): GuideDetail => {
  const topic = requireTrustedTopic(config.topicId);
  const guideWithoutReadTime: Omit<GuideDetail, "estimatedReadMinutes"> = {
    id: config.id,
    topicId: topic.id,
    title: config.title,
    japaneseTitle: topic.japaneseTitle,
    category: config.category,
    summary: topic.summary,
    audience: config.audience,
    requiredDocuments: topic.requiredDocuments ?? [],
    steps: topic.nextSteps,
    sections: createSections(topic, config),
    commonMistakes: config.commonMistakes,
    exampleSituation: config.exampleSituation,
    importantWarning: topic.warnings?.join(" "),
    officialSources: topic.officialSources,
    officialResourceIds: config.officialResourceIds ?? [],
    contentStatus: topic.contentStatus,
    needsOfficialConfirmation: topic.needsOfficialConfirmation,
    lastReviewedAt: topic.lastReviewedAt,
  };

  return {
    ...guideWithoutReadTime,
    estimatedReadMinutes: calculateEstimatedReadMinutes(guideWithoutReadTime),
  };
};

export const mockGuideDetails: GuideDetail[] = [
  createGuide({
    id: "moving-address-registration",
    topicId: "address-registration-moving",
    title: "Address Registration / Moving",
    category: "City Hall",
    audience:
      "Foreign students, workers, and job seekers who moved, will move, or received a city or ward office notice about their address.",
    whyThisMatters: [
      "City and ward offices use your registered address for important notices.",
      "Moving-in, moving-out, and moving within the same municipality can use different forms.",
      "Your city or ward office may ask you to update other services after the address change.",
    ],
    commonMistakes: [
      "Using another municipality's checklist as the final rule for your own city.",
      "Forgetting to check whether the notice is about moving in, moving out, or moving within the same municipality.",
      "Arriving at the office without the residence card or forms listed on the notice.",
    ],
    exampleSituation:
      "You move from one ward to another and receive a notice with words like 転入, 転出, or 転居. First identify which moving procedure the notice names, then confirm the current documents and deadline with the office shown on the notice.",
    officialResourceIds: ["city-hall-moving-guide"],
  }),
  createGuide({
    id: "health-insurance-payment",
    topicId: "national-health-insurance",
    title: "National Health Insurance",
    category: "Insurance",
    audience:
      "Students, workers, and job seekers who are not sure whether a National Health Insurance notice asks them to enroll, pay, reply, or update information.",
    whyThisMatters: [
      "You may receive a notice after moving, leaving a job, starting school, or changing insurance coverage.",
      "The notice may include payment slips, a deadline, or a request to confirm your insurance situation.",
      "Employer health insurance and National Health Insurance are different systems, so coverage should be checked when work changes.",
    ],
    commonMistakes: [
      "Assuming the amount is wrong because it differs from another person's notice.",
      "Ignoring a city notice after starting or leaving a job.",
      "Paying or discarding slips before confirming what period the notice covers.",
    ],
    exampleSituation:
      "You receive an envelope from the city insurance desk after starting a new job. Check whether your employer health insurance has started, then ask the city insurance desk how the notice applies to your current coverage.",
    officialResourceIds: ["mhlw-insurance", "city-insurance-helpdesk"],
  }),
  createGuide({
    id: "national-pension",
    topicId: "national-pension",
    title: "National Pension",
    category: "Pension",
    audience:
      "Students, workers, and job seekers who received a pension notice, payment slip, exemption form, postponement form, or request for confirmation.",
    whyThisMatters: [
      "Pension notices can ask for payment, enrollment, exemption, postponement, or a reply.",
      "Student payment postponement and other exemptions are not the same as simply ignoring a payment notice.",
      "Your employer or school situation may affect which office can help you confirm the next step.",
    ],
    commonMistakes: [
      "Assuming student status automatically stops pension payment notices.",
      "Thinking exemption or postponement is accepted before an official result is issued.",
      "Mixing up National Pension and employee pension coverage through work.",
    ],
    exampleSituation:
      "You are a student and receive a National Pension payment notice. Check whether the notice mentions 学生納付特例, then ask your school or pension office what application is needed before assuming payment can wait.",
  }),
  createGuide({
    id: "residence-tax-payment",
    topicId: "residence-tax",
    title: "Residence Tax",
    category: "Tax",
    audience:
      "Students, workers, and job seekers who received a residence tax notice, payment slip, salary deduction notice, or question from a city tax desk.",
    whyThisMatters: [
      "Residence tax is handled locally, so the municipality named on the notice matters.",
      "A notice may ask you to pay directly, or it may explain tax deducted from salary.",
      "A person may receive a notice even after moving if the tax period relates to a previous municipality.",
    ],
    commonMistakes: [
      "Treating residence tax as the same thing as income tax.",
      "Looking only at the total amount and missing separate payment deadlines.",
      "Ignoring a notice because it came from a city where you no longer live.",
    ],
    exampleSituation:
      "You receive several payment slips from a city where you lived before. Check the municipality, tax year, and each due date, then ask that city tax desk whether direct payment is required.",
    officialResourceIds: ["soumu-tax", "city-tax-helpdesk"],
  }),
  createGuide({
    id: "residence-status-renewal",
    topicId: "residence-status-renewal",
    title: "Residence Status Renewal",
    category: "Immigration",
    audience:
      "Students, workers, and job seekers whose period of stay may need renewal or who received an immigration notice about renewal, added documents, or an office visit.",
    whyThisMatters: [
      "Residence status affects whether you can continue staying in Japan under your current status.",
      "Immigration may ask for additional documents or confirmation before giving a result.",
      "Requirements depend on your status and personal situation, so generic advice is not enough.",
    ],
    commonMistakes: [
      "Assuming an application, postcard, or notice means renewal is approved.",
      "Waiting until the last day to handle missing or additional documents.",
      "Submitting guessed information instead of confirming unclear requirements.",
    ],
    exampleSituation:
      "Immigration sends a postcard asking you to bring additional documents. Read the deadline and office name carefully, prepare only the requested documents, and confirm unclear points with immigration or trusted support.",
    officialResourceIds: ["isa-main"],
  }),
  createGuide({
    id: "job-hunting-before-graduation",
    topicId: "student-to-worker-transition",
    title: "Student to Worker",
    category: "Immigration",
    audience:
      "International students and job seekers who plan to change from Student residence status to a work-related residence status after receiving a job offer.",
    whyThisMatters: [
      "A job offer does not automatically change residence status.",
      "School documents, employer documents, and immigration timing may all be needed.",
      "The job start date, graduation timing, and current period of stay should be checked together.",
    ],
    commonMistakes: [
      "Starting work before confirming that the residence status allows it.",
      "Assuming the employer alone can decide immigration requirements.",
      "Leaving school and employer documents until the application deadline is close.",
    ],
    exampleSituation:
      "You receive a job offer before graduation. Confirm the job duties and start date with the employer, ask your school what documents it can provide, and check the change-of-status procedure with immigration.",
    officialResourceIds: ["isa-main", "hello-work"],
  }),
  createGuide({
    id: "part-time-work-permission",
    topicId: "part-time-work-permission",
    title: "Part-Time Work Permission",
    category: "Immigration",
    audience:
      "International students who want to start, continue, or confirm part-time paid work while staying in Japan under Student residence status.",
    whyThisMatters: [
      "A student job, shift request, or employer offer is separate from immigration permission.",
      "Permission may be shown on immigration documents, but unclear cases need official confirmation.",
      "School rules and employer paperwork can add extra steps even when immigration permission exists.",
    ],
    commonMistakes: [
      "Assuming student residence status always allows paid work.",
      "Relying only on an employer's explanation of immigration permission.",
      "Forgetting to recheck permission when school status or residence status changes.",
    ],
    exampleSituation:
      "A restaurant asks you to start next week. Before accepting shifts, check your residence card and immigration documents for permission, then ask your school or immigration if anything is unclear.",
    officialResourceIds: ["isa-main"],
  }),
  createGuide({
    id: "employment-working-conditions",
    topicId: "employment-working-conditions",
    title: "Employment Contract / Working Conditions",
    category: "Work",
    audience:
      "Workers, job seekers, and students reviewing a job offer, employment contract, working conditions notice, or workplace rule document.",
    whyThisMatters: [
      "This document explains important job conditions such as wages, hours, holidays, workplace, and contract period.",
      "Written conditions help you compare what the employer promised with the actual job.",
      "Unclear terms should be checked before signing or before problems become harder to solve.",
    ],
    commonMistakes: [
      "Signing before checking wages, hours, overtime, holidays, and contract period.",
      "Relying only on spoken explanations when the written document is different.",
      "Waiting too long to ask official labor support when work conditions seem risky.",
    ],
    exampleSituation:
      "You receive a contract before your first day. Mark unclear wages, overtime, holidays, and contract period, ask HR for written clarification, and contact official labor support if the answers do not match the document.",
    officialResourceIds: ["hello-work"],
  }),
];

export const mockGuides: GuideSummary[] = mockGuideDetails.map(
  ({ id, title, category, summary, estimatedReadMinutes }) => ({
    id,
    title,
    category,
    summary,
    estimatedReadMinutes,
  }),
);

export const mockGuideDetailsById = Object.fromEntries(
  mockGuideDetails.map((guide) => [guide.id, guide]),
) as Record<string, GuideDetail>;
