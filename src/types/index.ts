export type AnalysisSource = "template" | "ai" | "deterministic";

export type AnalysisUrgency = "low" | "important" | "urgent";

export type UiStatus = "idle" | "loading" | "success" | "empty" | "error";

export type DocumentFileInput = {
  file: File;
  name: string;
  type: string;
  size: number;
};

export type DocumentAnalysisRequest = {
  documentText?: string;
  documentFile?: DocumentFileInput;
  documentTypeHint?: string;
  sourceLanguageHint?: string;
};

export type LegacyDocumentAnalysisResult = {
  source: "template" | "ai";
  documentType: string;
  summary: string;
  deadline: string | null;
  urgency: AnalysisUrgency;
  importantPoints: string[];
  nextSteps: string[];
  relatedGuide: string | null;
  officialWarning: string;
};

// Matches backend/models/schemas.py: DocumentUploadResultSchema.
export type ExtractedField = {
  label: string;
  kind: string;
  status: "verified" | "unverified";
  reasons: string[];
  evidenceIds: string[];
  ocrConfidence: number | null;
  association: "text_and_geometry" | "none";
  occurrences: number;
};
export type ExtractedDeadline = ExtractedField & { date: string | null };
export type ExtractedAmount = ExtractedField & { value: number | null; currency: "JPY" };
export type PageExtractionMethod = "paddleocr" | "pdf_embedded_text";
export type ExtractionStatus = "verified" | "partial" | "unverified" | "no_fields";
export type SourceEvidence = {
  id: string;
  text: string;
  confidence: number | null;
  bbox: [number, number, number, number];
  polygon: [number, number][] | null;
  page: number;
  originalIndex: number;
  readingOrder: number;
  extractionMethod: PageExtractionMethod;
};
export type ExtractionPage = {
  page: number;
  method: PageExtractionMethod;
  coordinateSystem: "image_pixels" | "rendered_pixels" | "pdf_points";
  width: number;
  height: number;
  auxiliaryFramesSkipped: number;
};
export type DocumentUploadResult = {
  source: "deterministic";
  extractionMethod: PageExtractionMethod | "mixed";
  documentType: string | null;
  summary: string | null;
  deadline: string | null;
  urgency: AnalysisUrgency | null;
  relatedGuide: string | null;
  officialWarning: string | null;
  primaryDeadline: string | null;
  deadlines: ExtractedDeadline[];
  primaryAmount: number | null;
  amounts: ExtractedAmount[];
  importantPoints: string[];
  nextSteps: string[];
  evidence: SourceEvidence[];
  warnings: string[];
  extractionStatus: ExtractionStatus;
  documentTypeEvidenceIds: string[];
  completedPaymentEvidenceIds: string[];
  pages: ExtractionPage[];
};
export type DocumentAnalysisResult = LegacyDocumentAnalysisResult | DocumentUploadResult;

export type TrustedTopicCategory =
  | "city-hall"
  | "immigration"
  | "tax"
  | "insurance"
  | "pension"
  | "work"
  | "school";

export type TrustedTopicUser = "student" | "worker" | "job-seeker";

export type TrustedTopicContentStatus = "verified" | "needs-review" | "dynamic";

export type TrustedTopic = {
  id: string;
  title: string;
  japaneseTitle: string;
  category: TrustedTopicCategory;
  targetUsers: TrustedTopicUser[];
  aliases: string[];
  keywords: string[];
  summary: string;
  importantPoints: string[];
  nextSteps: string[];
  requiredDocuments?: string[];
  warnings?: string[];
  officialSources: {
    title: string;
    url: string;
    organization: string;
  }[];
  lastReviewedAt: string;
  needsOfficialConfirmation: boolean;
  contentStatus?: TrustedTopicContentStatus;
};

export type TopicClassificationResult = {
  topicId: string | null;
  documentTemplateId: string | null;
  confidence: number;
  reason?: string;
  matchedAliases?: string[];
  matchedKeywords?: string[];
  candidateScores?: Array<{
    topicId: string;
    score: number;
  }>;
};

export type DocumentTemplate = LegacyDocumentAnalysisResult & {
  id: string;
  matchKeywords: string[];
  strongMatchKeywords: string[];
  relatedTopicId: string;
  trustedSummary: string;
  defaultUrgency: AnalysisUrgency;
};

export type GuideSummary = {
  id: string;
  title: string;
  category: string;
  summary: string;
  estimatedReadMinutes: number;
};

export type GuideOfficialSource = {
  title: string;
  organization: string;
  url: string;
};

export type GuideSection = {
  id: string;
  title: string;
  body?: string;
  items?: string[];
  variant?: "default" | "warning" | "confirmation";
};

export type GuideDetail = GuideSummary & {
  topicId?: string;
  japaneseTitle?: string;
  contentStatus?: TrustedTopicContentStatus;
  needsOfficialConfirmation?: boolean;
  lastReviewedAt?: string;
  audience: string;
  requiredDocuments: string[];
  steps: string[];
  sections: GuideSection[];
  commonMistakes?: string[];
  exampleSituation?: string;
  importantWarning?: string;
  officialSources?: GuideOfficialSource[];
  officialResourceIds: string[];
};

export type OfficialResource = {
  id: string;
  title: string;
  category: string;
  description: string;
  url: string;
};

export type ChecklistItem = {
  id: string;
  title: string;
  completed: boolean;
  dueDate: string | null;
  category: string;
};

export type ChecklistCreateInput = {
  title: string;
  dueDate?: string | null;
  category: string;
};

export type ChecklistUpdateInput = Partial<ChecklistCreateInput> & {
  completed?: boolean;
};

export type ApiError = {
  code: string;
  message: string;
  details?: string[];
  status?: number;
  retryAfterSeconds?: number;
};

export type DocumentInputFormValues = { documentFile?: DocumentFileInput };
