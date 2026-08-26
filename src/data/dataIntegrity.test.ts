import { describe, expect, it } from "vitest";
import { aiTestCases } from "./aiTestCases";
import { documentTemplates } from "./documentTemplates";
import { trustedTopicsById, trustedTopics } from "./trustedTopics";

describe("trusted knowledge data", () => {
  it("uses unique trusted topic IDs with review dates", () => {
    const ids = trustedTopics.map((topic) => topic.id);

    expect(new Set(ids).size).toBe(ids.length);
    expect(
      trustedTopics.every((topic) => /^\d{4}-\d{2}-\d{2}$/.test(topic.lastReviewedAt)),
    ).toBe(true);
    expect(
      trustedTopics.every((topic) => topic.needsOfficialConfirmation),
    ).toBe(true);
  });

  it("keeps document template topic references valid", () => {
    expect(documentTemplates.length).toBeGreaterThanOrEqual(8);

    for (const template of documentTemplates) {
      expect(template.id).toBeTruthy();
      expect(trustedTopicsById[template.relatedTopicId]).toBeTruthy();
      expect(template.source).toBe("template");
      expect(template.officialWarning.length).toBeGreaterThan(20);
    }
  });

  it("keeps AI test cases synthetic and broad enough for backend evaluation", () => {
    expect(aiTestCases.length).toBeGreaterThanOrEqual(20);
    expect(aiTestCases.some((testCase) => testCase.expected.deadline === null)).toBe(true);
    expect(aiTestCases.some((testCase) => testCase.expected.deadline !== null)).toBe(true);
    expect(
      aiTestCases.some((testCase) => testCase.inputJapanese.includes("令和")),
    ).toBe(true);
    expect(
      aiTestCases.some((testCase) => testCase.expected.confidenceRange),
    ).toBe(true);
  });
});
