export type AnalysisSource = "template" | "ai";

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

export type DocumentAnalysisResult = {
  source: AnalysisSource;
  documentType: string;
  summary: string;
  deadline: string | null;
  urgency: AnalysisUrgency;
  importantPoints: string[];
  nextSteps: string[];
  relatedGuide: string | null;
  officialWarning: string;
};

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
};

export type DocumentTemplate = DocumentAnalysisResult & {
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
};

export type DocumentInputFormValues = {
  documentText: string;
  documentFile?: DocumentFileInput;
  documentTypeHint?: string;
  sourceLanguageHint?: string;
};
