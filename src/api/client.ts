import { getMockAnalysisResult } from "../data/mockAnalysis";
import { mockChecklist } from "../data/mockChecklist";
import { mockGuideDetailsById, mockGuides } from "../data/mockGuides";
import { mockResources } from "../data/mockResources";
import type {
  ApiError,
  ChecklistCreateInput,
  ChecklistItem,
  ChecklistUpdateInput,
  DocumentAnalysisRequest,
  DocumentAnalysisResult,
  GuideDetail,
  GuideSummary,
  OfficialResource,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API !== "false";
const MOCK_API_SCENARIO = import.meta.env.VITE_MOCK_API_SCENARIO ?? "success";
const IS_TEST = import.meta.env.MODE === "test";
const CHECKLIST_STORAGE_KEY = "japanxtheworld.checklist";

const delay = async (ms = 450) =>
  new Promise((resolve) => {
    globalThis.setTimeout(resolve, IS_TEST ? 20 : ms);
  });

const createApiError = (
  code: string,
  message: string,
  details?: string[],
): ApiError => ({
  code,
  message,
  details,
});

const readChecklistStorage = (): ChecklistItem[] => {
  if (typeof window === "undefined") {
    return mockChecklist;
  }

  const raw = window.localStorage.getItem(CHECKLIST_STORAGE_KEY);
  if (!raw) {
    window.localStorage.setItem(CHECKLIST_STORAGE_KEY, JSON.stringify(mockChecklist));
    return mockChecklist;
  }

  try {
    const parsed = JSON.parse(raw) as ChecklistItem[];
    return Array.isArray(parsed) ? parsed : mockChecklist;
  } catch {
    return mockChecklist;
  }
};

const writeChecklistStorage = (items: ChecklistItem[]) => {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(CHECKLIST_STORAGE_KEY, JSON.stringify(items));
  }
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string");

export const isDocumentAnalysisResult = (
  value: unknown,
): value is DocumentAnalysisResult => {
  if (!isRecord(value)) {
    return false;
  }

  return (
    (value.source === "template" || value.source === "ai") &&
    typeof value.documentType === "string" &&
    typeof value.summary === "string" &&
    (typeof value.deadline === "string" || value.deadline === null) &&
    (value.urgency === "low" ||
      value.urgency === "important" ||
      value.urgency === "urgent") &&
    isStringArray(value.importantPoints) &&
    isStringArray(value.nextSteps) &&
    (typeof value.relatedGuide === "string" || value.relatedGuide === null) &&
    typeof value.officialWarning === "string"
  );
};

type MockScenario =
  | "success"
  | "trusted-template"
  | "ai-fallback"
  | "timeout"
  | "server-error"
  | "malformed"
  | "unknown-document"
  | "no-deadline"
  | "empty-guides"
  | "resources-error"
  | "checklist-mutation-error";

const scenarioFromRequest = (
  request?: Pick<DocumentAnalysisRequest, "documentText" | "documentTypeHint">,
): MockScenario => {
  const combinedInput =
    `${request?.documentTypeHint ?? ""} ${request?.documentText ?? ""}`.toLowerCase();
  const scenarioMatch = combinedInput.match(/simulate:([a-z-]+)/);
  return (scenarioMatch?.[1] as MockScenario | undefined) ?? MOCK_API_SCENARIO;
};

const createNoDeadlineResult = (): DocumentAnalysisResult => ({
  source: "ai",
  documentType: "Unknown Official Document",
  summary:
    "This document appears to be an official notice, but no clear deadline is written in the provided text.",
  deadline: null,
  urgency: "important",
  importantPoints: [
    "The document may require attention.",
    "No clear deadline was found.",
    "The issuing organization should confirm the details.",
  ],
  nextSteps: [
    "Check the sender and contact information.",
    "Ask the issuing organization whether a deadline applies.",
    "Keep the document until the procedure is confirmed.",
  ],
  relatedGuide: null,
  officialWarning:
    "This explanation is only a support tool. Please confirm important details with the issuing organization or an official source.",
});

const fetchJson = async <T>(
  path: string,
  init?: RequestInit,
): Promise<T> => {
  const headers =
    init?.body instanceof FormData
      ? init?.headers
      : {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let errorBody: ApiError | null = null;

    try {
      errorBody = (await response.json()) as ApiError;
    } catch {
      errorBody = null;
    }

    throw (
      errorBody ??
      createApiError(
        "REQUEST_FAILED",
        "The request could not be completed.",
      )
    );
  }

  return (await response.json()) as T;
};

const hasAnalyzeInput = (request: DocumentAnalysisRequest) =>
  Boolean(request.documentText?.trim()) || Boolean(request.documentFile);

const createAnalyzeRequestBody = (request: DocumentAnalysisRequest) => {
  if (!request.documentFile) {
    return JSON.stringify({
      documentText: request.documentText ?? "",
      documentTypeHint: request.documentTypeHint,
      sourceLanguageHint: request.sourceLanguageHint,
    });
  }

  const formData = new FormData();
  formData.append("file", request.documentFile.file, request.documentFile.name);

  if (request.documentText?.trim()) {
    formData.append("documentText", request.documentText.trim());
  }

  if (request.documentTypeHint) {
    formData.append("documentTypeHint", request.documentTypeHint);
  }

  if (request.sourceLanguageHint) {
    formData.append("sourceLanguageHint", request.sourceLanguageHint);
  }

  return formData;
};

export const analyzeDocument = async (
  request: DocumentAnalysisRequest,
): Promise<DocumentAnalysisResult> => {
  if (USE_MOCK_API) {
    await delay(900);
    if (!hasAnalyzeInput(request)) {
      throw createApiError(
        "EMPTY_DOCUMENT",
        "Please paste document text or choose a supported document file.",
      );
    }

    const scenario = scenarioFromRequest(request);

    if (scenario === "timeout") {
      throw createApiError(
        "ANALYSIS_TIMEOUT",
        "The analysis took too long. Please try again with clearer text.",
      );
    }

    if (scenario === "server-error") {
      throw createApiError(
        "REQUEST_FAILED",
        "Something went wrong while analyzing this document.",
      );
    }

    if (scenario === "malformed") {
      throw createApiError(
        "MALFORMED_ANALYSIS",
        "The analysis result could not be displayed safely. Please try again.",
      );
    }

    if (scenario === "trusted-template") {
      return getMockAnalysisResult({
        ...request,
        documentText: "住民税納税通知書です。納期限を確認してください。",
        documentTypeHint: "tax notice",
      });
    }

    if (scenario === "ai-fallback" || scenario === "unknown-document") {
      return getMockAnalysisResult({
        ...request,
        documentText: "通知。確認してください。日付や手続き名の一部が読めません。",
        documentTypeHint: "unknown",
      });
    }

    if (scenario === "no-deadline") {
      return createNoDeadlineResult();
    }

    return getMockAnalysisResult(request);
  }

  if (!hasAnalyzeInput(request)) {
    throw createApiError(
      "EMPTY_DOCUMENT",
      "Please paste document text or choose a supported document file.",
    );
  }

  const result = await fetchJson<unknown>("/documents/analyze", {
    method: "POST",
    body: createAnalyzeRequestBody(request),
  });

  if (!isDocumentAnalysisResult(result)) {
    throw createApiError(
      "MALFORMED_ANALYSIS",
      "The analysis result could not be displayed safely. Please try again.",
    );
  }

  return result;
};

export const getGuides = async (): Promise<GuideSummary[]> => {
  if (USE_MOCK_API) {
    await delay();
    if (MOCK_API_SCENARIO === "empty-guides") {
      return [];
    }
    return mockGuides;
  }

  return fetchJson<GuideSummary[]>("/guides");
};

export const getGuideById = async (guideId: string): Promise<GuideDetail> => {
  if (USE_MOCK_API) {
    await delay();
    const guide = mockGuideDetailsById[guideId];
    if (!guide) {
      throw createApiError("GUIDE_NOT_FOUND", "Guide not found.");
    }
    return guide;
  }

  return fetchJson<GuideDetail>(`/guides/${guideId}`);
};

export const getResources = async (): Promise<OfficialResource[]> => {
  if (USE_MOCK_API) {
    await delay();
    if (MOCK_API_SCENARIO === "resources-error") {
      throw createApiError(
        "RESOURCES_UNAVAILABLE",
        "Support links could not be loaded right now.",
      );
    }
    return mockResources;
  }

  return fetchJson<OfficialResource[]>("/resources");
};

export const getChecklist = async (): Promise<ChecklistItem[]> => {
  if (USE_MOCK_API) {
    await delay(250);
    return readChecklistStorage();
  }

  return fetchJson<ChecklistItem[]>("/checklist");
};

export const createChecklistItem = async (
  input: ChecklistCreateInput,
): Promise<ChecklistItem> => {
  if (USE_MOCK_API) {
    await delay(250);
    if (MOCK_API_SCENARIO === "checklist-mutation-error") {
      throw createApiError("CHECKLIST_SAVE_FAILED", "Your task could not be saved.");
    }
    const nextItem: ChecklistItem = {
      id: `task-${Date.now()}`,
      title: input.title.trim(),
      completed: false,
      dueDate: input.dueDate ?? null,
      category: input.category.trim(),
    };
    const items = [nextItem, ...readChecklistStorage()];
    writeChecklistStorage(items);
    return nextItem;
  }

  return fetchJson<ChecklistItem>("/checklist", {
    method: "POST",
    body: JSON.stringify(input),
  });
};

export const updateChecklistItem = async (
  id: string,
  input: ChecklistUpdateInput,
): Promise<ChecklistItem> => {
  if (USE_MOCK_API) {
    await delay(250);
    if (MOCK_API_SCENARIO === "checklist-mutation-error") {
      throw createApiError(
        "CHECKLIST_UPDATE_FAILED",
        "This task could not be updated right now.",
      );
    }
    const items = readChecklistStorage();
    const currentItem = items.find((item) => item.id === id);

    if (!currentItem) {
      throw createApiError("CHECKLIST_NOT_FOUND", "Task not found.");
    }

    const updatedItem: ChecklistItem = {
      ...currentItem,
      ...input,
      dueDate: input.dueDate === undefined ? currentItem.dueDate : input.dueDate,
    };

    writeChecklistStorage(
      items.map((item) => (item.id === id ? updatedItem : item)),
    );
    return updatedItem;
  }

  return fetchJson<ChecklistItem>(`/checklist/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
};

export const deleteChecklistItem = async (
  id: string,
): Promise<{ success: true; id: string }> => {
  if (USE_MOCK_API) {
    await delay(250);
    if (MOCK_API_SCENARIO === "checklist-mutation-error") {
      throw createApiError(
        "CHECKLIST_DELETE_FAILED",
        "This task could not be deleted right now.",
      );
    }
    const items = readChecklistStorage();
    writeChecklistStorage(items.filter((item) => item.id !== id));
    return { success: true, id };
  }

  return fetchJson<{ success: true; id: string }>(`/checklist/${id}`, {
    method: "DELETE",
  });
};
