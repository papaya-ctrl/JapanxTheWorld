import type {
  AnalysisUrgency,
  DocumentAnalysisRequest,
  LegacyDocumentAnalysisResult,
  DocumentTemplate,
  TrustedTopic,
} from "../types";
import { documentTemplates } from "./documentTemplates";
import {
  classifyTrustedInput,
  extractExplicitDeadline,
} from "./trustedClassification";
import { trustedTopicsById } from "./trustedTopics";

const templatesById = Object.fromEntries(
  documentTemplates.map((template) => [template.id, template]),
) as Record<string, DocumentTemplate>;

const relatedGuideByTopicId: Record<string, string | null> = {
  "address-registration-moving": "moving-address-registration",
  "national-health-insurance": "health-insurance-payment",
  "national-pension": "national-pension",
  "residence-tax": "residence-tax-payment",
  "residence-status-renewal": "residence-status-renewal",
  "student-to-worker-transition": "job-hunting-before-graduation",
  "part-time-work-permission": "part-time-work-permission",
  "employment-working-conditions": "employment-working-conditions",
};

const fileDemoTopics = [
  { terms: ["residence-tax", "resident-tax", "住民税"], topicId: "residence-tax" },
  { terms: ["health-insurance", "nhi", "国民健康保険"], topicId: "national-health-insurance" },
  { terms: ["national-pension", "pension", "国民年金"], topicId: "national-pension" },
  { terms: ["address", "moving", "転入", "転出"], topicId: "address-registration-moving" },
  { terms: ["residence-status", "visa-renewal", "在留期間更新"], topicId: "residence-status-renewal" },
] as const;

const uniqueStrings = (items: string[]) => {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = item.trim().toLowerCase().replace(/[.!。]/g, "");
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const createUnknownResult = (fileOnly = false): LegacyDocumentAnalysisResult => ({
  source: "ai",
  documentType: "Unknown Official Document",
  summary: fileOnly
    ? "Mock mode cannot read the uploaded file because OCR is not active. The filename alone is not enough to verify the document's topic, deadline, amount, or required action. This result therefore remains unclassified."
    : "The provided text does not contain enough specific, consistent evidence for a trusted topic or document template. A cautious fallback is safer than guessing a tax, pension, insurance, immigration, or work category. No clear deadline was established.",
  deadline: null,
  urgency: "important",
  importantPoints: fileOnly
    ? [
        "Mock mode did not perform OCR on the uploaded file.",
        "No deadline, amount, sender, or instruction was read from the file.",
        "A filename can be used only as an explicit demo label and does not verify file contents.",
        "The actual document must be checked directly or processed by future OCR.",
      ]
    : [
        "The exact document topic is unclear from the available text.",
        "No clear deadline was safely extracted.",
        "The sender, department, and requested action need official confirmation.",
        "Missing, damaged, or conflicting text can change the meaning of a notice.",
      ],
  nextSteps: [
    "Check the sender name, department, phone number, and address on the document.",
    "Look for a full procedure name, notice title, deadline, or requested action.",
    "Contact the issuing organization or bring the document to a trusted support desk.",
    "Ask for help before paying money, submitting documents, or ignoring the notice.",
  ],
  relatedGuide: null,
  officialWarning:
    "This is an unverified fallback explanation because a trusted match was not established. Confirm the document's meaning, deadline, amount, and required action with the official sender or another official source before acting.",
});

const buildOfficialWarning = (topic: TrustedTopic, fileOnly: boolean) => {
  const topicWarnings = topic.warnings?.join(" ") ?? "Do not rely on unverified details.";
  const sourceNames = topic.officialSources.map((source) => source.organization);
  const organizations = [...new Set(sourceNames)].slice(0, 2).join(" or ");
  const confirmation = organizations
    ? `Confirm the final requirements with ${organizations} or the organization that issued the document.`
    : "Confirm the final requirements with the organization that issued the document.";
  const fileWarning = fileOnly
    ? " Mock mode did not read the uploaded file with OCR; this is only a filename-based demo label and not a reading of the file."
    : "";

  return `${topicWarnings} ${confirmation}${fileWarning}`;
};

const buildSummary = (
  topic: TrustedTopic,
  documentType: string,
  deadline: string | null,
  fileOnly: boolean,
) => {
  const deadlineSentence = deadline
    ? `The provided text clearly states a deadline of ${deadline}.`
    : "No clear deadline was safely established from the provided text.";
  const sourceSentence = fileOnly
    ? "The uploaded file was not read with OCR in mock mode, so the category is only a filename-based demo label."
    : "The explanation uses maintained JapanxTheWorld trusted content; document-specific details still require official confirmation.";

  return `${documentType}: ${topic.summary} ${deadlineSentence} ${sourceSentence}`;
};

const determineUrgency = (text: string, deadline: string | null): AnalysisUrgency => {
  const normalized = text.normalize("NFKC").toLowerCase();
  if (/(至急|直ちに|本日中|最終督促|最終通知|immediately|urgent|final notice)/i.test(normalized)) {
    return "urgent";
  }

  const informational =
    /(情報のみ|参考情報|制度に関する案内|説明しています|information only|for your information)/i.test(
      normalized,
    );
  const actionLanguage = /(支払|納付|提出|申請|持参|訪問|連絡|確認してください|must|required)/i.test(
    normalized,
  );
  if (!deadline && informational && !actionLanguage) {
    return "low";
  }

  return "important";
};

const createTrustedResult = (
  topic: TrustedTopic,
  template: DocumentTemplate | null,
  text: string,
  fileOnly = false,
): LegacyDocumentAnalysisResult => {
  const deadline = fileOnly ? null : extractExplicitDeadline(text);
  const documentType = template?.documentType ?? topic.title;
  const deadlinePoint = deadline
    ? [`The explicit deadline shown in the provided text is ${deadline}.`]
    : ["No explicit deadline was safely detected; do not assume a date from the topic alone."];
  const filePoint = fileOnly
    ? [
        "Mock mode did not perform OCR, so no deadline, amount, sender, or instruction was read from the uploaded file.",
      ]
    : [];

  return {
    source: "template",
    documentType,
    summary: buildSummary(topic, documentType, deadline, fileOnly),
    deadline,
    urgency: fileOnly ? "important" : determineUrgency(text, deadline),
    importantPoints: uniqueStrings([
      ...deadlinePoint,
      ...filePoint,
      ...topic.importantPoints,
    ]).slice(0, 6),
    nextSteps: uniqueStrings(topic.nextSteps).slice(0, 6),
    relatedGuide: template?.relatedGuide ?? relatedGuideByTopicId[topic.id] ?? null,
    officialWarning: buildOfficialWarning(topic, fileOnly),
  };
};

const createFileOnlyDemoResult = (request: DocumentAnalysisRequest) => {
  const fileName = request.documentFile?.name.normalize("NFKC").toLowerCase() ?? "";
  const demoTopic = fileDemoTopics.find((candidate) =>
    candidate.terms.some((term) => fileName.includes(term.toLowerCase())),
  );

  if (!demoTopic) {
    return createUnknownResult(true);
  }

  const topic = trustedTopicsById[demoTopic.topicId];
  const template =
    documentTemplates.find((candidate) => candidate.relatedTopicId === demoTopic.topicId) ??
    null;
  return createTrustedResult(topic, template, "", true);
};

export const getMockAnalysisResult = (
  request: DocumentAnalysisRequest,
): LegacyDocumentAnalysisResult => {
  const text = request.documentText?.trim() ?? "";
  const hint = request.documentTypeHint?.trim() ?? "";

  if (!text && request.documentFile) {
    return createFileOnlyDemoResult(request);
  }

  const combinedInput = `${hint} ${text}`.trim();
  const classification = classifyTrustedInput(combinedInput);
  if (!classification.topicId) {
    return createUnknownResult();
  }

  const topic = trustedTopicsById[classification.topicId];
  const template = classification.documentTemplateId
    ? templatesById[classification.documentTemplateId] ?? null
    : null;
  return createTrustedResult(topic, template, combinedInput);
};

export const mockAnalysisResults: LegacyDocumentAnalysisResult[] = [
  getMockAnalysisResult({
    documentText:
      "住民税納税通知書です。納期限は2026年7月31日です。市役所の税務課へ確認してください。",
  }),
  getMockAnalysisResult({
    documentText:
      "国民健康保険料の納付書です。支払期限は2026年8月10日です。保険課へ確認してください。",
  }),
  getMockAnalysisResult({
    documentText: "重要なお知らせです。内容を確認してください。",
  }),
];
