import { describe, expect, it } from "vitest";
import { aiTestCases } from "./aiTestCases";
import { documentTemplates } from "./documentTemplates";
import { trustedTopicsById, trustedTopics } from "./trustedTopics";

const manualTrustedContentV1TopicIds = [
  "address-registration-moving",
  "national-health-insurance",
  "national-pension",
  "residence-tax",
  "residence-status-renewal",
  "student-to-worker-transition",
  "part-time-work-permission",
  "employment-working-conditions",
];

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

  it("keeps Manual Trusted Content V1 topics populated with reviewed source metadata", () => {
    for (const topicId of manualTrustedContentV1TopicIds) {
      const topic = trustedTopicsById[topicId];

      expect(topic).toBeTruthy();
      expect(topic.summary).not.toContain("Trusted content framework");
      expect(topic.summary.length).toBeGreaterThan(80);
      expect(topic.importantPoints.length).toBeGreaterThanOrEqual(4);
      expect(topic.nextSteps.length).toBeGreaterThanOrEqual(4);
      expect(topic.requiredDocuments?.length).toBeGreaterThanOrEqual(3);
      expect(topic.warnings?.length).toBeGreaterThanOrEqual(2);
      expect(topic.officialSources.length).toBeGreaterThanOrEqual(1);
      expect(topic.contentStatus).toBe("dynamic");
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
