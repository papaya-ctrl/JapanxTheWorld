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
const CHECKLIST_STORAGE_KEY = "japanxtheworld.checklist";

const delay = async (ms = 450) =>
  new Promise((resolve) => {
    window.setTimeout(resolve, ms);
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

const fetchJson = async <T>(
  path: string,
  init?: RequestInit,
): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
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

export const analyzeDocument = async (
  request: DocumentAnalysisRequest,
): Promise<DocumentAnalysisResult> => {
  if (USE_MOCK_API) {
    await delay(900);
    if (!request.documentText.trim()) {
      throw createApiError(
        "EMPTY_DOCUMENT",
        "Please paste document text before starting analysis.",
      );
    }
    return getMockAnalysisResult(request);
  }

  return fetchJson<DocumentAnalysisResult>("/documents/analyze", {
    method: "POST",
    body: JSON.stringify(request),
  });
};

export const getGuides = async (): Promise<GuideSummary[]> => {
  if (USE_MOCK_API) {
    await delay();
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
    const items = readChecklistStorage();
    writeChecklistStorage(items.filter((item) => item.id !== id));
    return { success: true, id };
  }

  return fetchJson<{ success: true; id: string }>(`/checklist/${id}`, {
    method: "DELETE",
  });
};
