import type {
  AnalysisUrgency,
  DocumentAnalysisRequest,
  DocumentAnalysisResult,
  TrustedTopic,
} from "../types";
import { trustedTopicsById } from "./trustedTopics";

type KnownMockTopic = {
  topicId: string;
  documentType: string;
  relatedGuide: string | null;
  urgency: AnalysisUrgency;
  triggers: string[];
};

const knownMockTopics: KnownMockTopic[] = [
  {
    topicId: "residence-tax",
    documentType: "Residence Tax Notice",
    relatedGuide: "residence-tax-payment",
    urgency: "important",
    triggers: ["residence tax", "resident tax", "municipal tax", "inhabitant tax", "住民税", "市民税", "県民税", "tax"],
  },
  {
    topicId: "national-health-insurance",
    documentType: "National Health Insurance Notice",
    relatedGuide: "health-insurance-payment",
    urgency: "important",
    triggers: ["national health insurance", "health insurance", "insurance", "nhi", "国民健康保険", "国保", "健康保険", "保険"],
  },
  {
    topicId: "national-pension",
    documentType: "National Pension Notice",
    relatedGuide: "national-pension",
    urgency: "important",
    triggers: ["national pension", "pension", "国民年金", "年金", "学生納付特例"],
  },
  {
    topicId: "address-registration-moving",
    documentType: "Address Registration Notice",
    relatedGuide: "moving-address-registration",
    urgency: "important",
    triggers: ["address registration", "moving", "change address", "住所変更", "転入", "転出", "転居", "住民登録"],
  },
  {
    topicId: "residence-status-renewal",
    documentType: "Immigration / Residence Status Notice",
    relatedGuide: "residence-status-renewal",
    urgency: "urgent",
    triggers: ["residence status", "visa renewal", "immigration", "在留期間更新", "在留資格", "入国在留管理局", "出入国在留管理庁"],
  },
  {
    topicId: "student-to-worker-transition",
    documentType: "Student to Worker Status Change Notice",
    relatedGuide: "job-hunting-before-graduation",
    urgency: "important",
    triggers: ["student to worker", "work status", "change status", "在留資格変更", "留学", "就労", "内定", "卒業"],
  },
  {
    topicId: "part-time-work-permission",
    documentType: "Part-Time Work Permission Notice",
    relatedGuide: "part-time-work-permission",
    urgency: "important",
    triggers: ["part-time work", "work permission", "activity outside status", "資格外活動", "アルバイト許可", "アルバイト"],
  },
  {
    topicId: "employment-working-conditions",
    documentType: "Employment / Working Conditions Notice",
    relatedGuide: "employment-working-conditions",
    urgency: "important",
    triggers: ["employment contract", "working conditions", "labor notice", "雇用契約", "労働条件", "賃金", "勤務時間"],
  },
];

const createUnknownResult = (): DocumentAnalysisResult => ({
  source: "ai",
  documentType: "Unknown Official Document",
  summary:
    "This looks like an official or administrative notice, but the exact topic cannot be determined from the provided text. The document may still require attention if it includes a sender, contact desk, deadline, or request for action. Because the purpose is unclear, use this result only as a cautious starting point.",
  deadline: null,
  urgency: "important",
  importantPoints: [
    "The exact purpose is unclear from the provided text.",
    "No clear deadline detected.",
    "The sender, department, and requested action need official confirmation.",
    "Missing or damaged text can change the meaning of an official notice.",
  ],
  nextSteps: [
    "Check the sender name, department, phone number, and address on the document.",
    "Look again for words such as deadline, payment, submit, visit, or reply.",
    "Contact the issuing organization or bring the document to a trusted support desk.",
    "Ask for help before paying money, submitting documents, or ignoring the notice.",
  ],
  relatedGuide: null,
  officialWarning:
    "This result may be incomplete because the document topic is unclear. Confirm the meaning, deadline, and required action with the official sender or a trusted support desk before acting.",
});

const datePatterns = [
  /(?:deadline|due date|by|until)[^\d]{0,20}(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})/i,
  /(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})[^\n。]{0,20}(?:deadline|due date|by|until)/i,
  /(?:納期限|提出期限|期限|まで)[^\d]{0,20}(20\d{2})年(\d{1,2})月(\d{1,2})日/,
  /(20\d{2})年(\d{1,2})月(\d{1,2})日[^\n。]{0,20}(?:まで|納期限|提出期限|期限)/,
];

const toIsoDate = (year: string, month: string, day: string) =>
  `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;

const extractClearDeadline = (text: string): string | null => {
  for (const pattern of datePatterns) {
    const match = text.match(pattern);

    if (match) {
      return toIsoDate(match[1], match[2], match[3]);
    }
  }

  return null;
};

const findKnownTopic = (combinedInput: string) =>
  knownMockTopics.find((topic) =>
    topic.triggers.some((trigger) => combinedInput.includes(trigger.toLowerCase())),
  );

const buildOfficialWarning = (topic: TrustedTopic, isFileOnly: boolean) => {
  const baseWarning =
    topic.warnings?.join(" ") ??
    "Confirm important details with the official organization before acting.";
  const confirmation =
    "Important tax, immigration, pension, labor, insurance, or municipal details should be confirmed with official sources.";
  const fileWarning = isFileOnly
    ? " Mock mode did not read the uploaded file with OCR, so use this only as a filename-based demo result."
    : "";

  return `${baseWarning} ${confirmation}${fileWarning}`;
};

const buildSummary = (
  topic: TrustedTopic,
  documentType: string,
  hasDeadline: boolean,
  isFileOnly: boolean,
) => {
  const deadlineSentence = hasDeadline
    ? "A clear deadline was detected in the provided text."
    : "No clear deadline was detected in the provided text.";
  const fileSentence = isFileOnly
    ? "In mock mode, the uploaded file was not read with OCR; this result is based on the file name and mock routing only."
    : "This mock result uses JapanxTheWorld trusted topic content to explain the likely meaning.";

  return `${documentType}: ${topic.summary} ${deadlineSentence} ${fileSentence}`;
};

const createTopicResult = (
  topicConfig: KnownMockTopic,
  request: DocumentAnalysisRequest,
  combinedInput: string,
): DocumentAnalysisResult => {
  const topic = trustedTopicsById[topicConfig.topicId];
  const isFileOnly = Boolean(request.documentFile) && !request.documentText?.trim();
  const deadline = isFileOnly ? null : extractClearDeadline(combinedInput);
  const filePoint = isFileOnly
    ? ["Mock mode did not perform OCR on the uploaded file, so no deadline, amount, or specific instruction was read from the file."]
    : [];

  return {
    source: "template",
    documentType: topicConfig.documentType,
    summary: buildSummary(topic, topicConfig.documentType, Boolean(deadline), isFileOnly),
    deadline,
    urgency: topicConfig.urgency,
    importantPoints: [
      ...topic.importantPoints,
      ...filePoint,
      "Any missing amount, deadline, sender, or eligibility detail must be confirmed from the actual notice or official source.",
    ].slice(0, 6),
    nextSteps: topic.nextSteps.slice(0, 6),
    relatedGuide: topicConfig.relatedGuide,
    officialWarning: buildOfficialWarning(topic, isFileOnly),
  };
};

export const mockAnalysisResults: DocumentAnalysisResult[] = [
  createTopicResult(
    knownMockTopics[0],
    {
      documentText:
        "住民税のお知らせです。2026年7月31日までに内容を確認してください。お問い合わせは市役所へお願いします。",
    },
    "住民税のお知らせです。2026年7月31日までに内容を確認してください。",
  ),
  createTopicResult(
    knownMockTopics[1],
    {
      documentText:
        "国民健康保険のお知らせです。2026年8月10日までに内容を確認してください。お問い合わせは市役所へお願いします。",
    },
    "国民健康保険のお知らせです。2026年8月10日までに内容を確認してください。",
  ),
  createUnknownResult(),
];

export const getMockAnalysisResult = (
  request: DocumentAnalysisRequest,
): DocumentAnalysisResult => {
  const text = request.documentText ?? "";
  const hint = request.documentTypeHint?.toLowerCase() ?? "";
  const fileName = request.documentFile?.name.toLowerCase() ?? "";
  const combinedInput = `${text} ${hint} ${fileName}`.toLowerCase();
  const knownTopic = findKnownTopic(combinedInput);

  if (knownTopic) {
    return createTopicResult(knownTopic, request, `${text} ${hint}`);
  }

  return createUnknownResult();
};
