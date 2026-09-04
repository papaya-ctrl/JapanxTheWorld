import { describe, expect, it } from "vitest";
import { aiTestCases } from "./aiTestCases";
import { documentTemplates } from "./documentTemplates";
import { getMockAnalysisResult, mockAnalysisResults } from "./mockAnalysis";
import { calculateEstimatedReadMinutes, mockGuideDetails } from "./mockGuides";
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

const requiredGuideSectionIds = [
  "what-this-is",
  "who-this-is-for",
  "why-this-matters",
  "what-to-check-first",
  "required-documents",
  "step-by-step-actions",
  "common-mistakes",
  "example-situation",
  "important-warning",
  "official-confirmation",
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

  it("expands Manual Trusted Content V1 topics into structured Life Guides", () => {
    expect(mockGuideDetails).toHaveLength(8);
    expect(mockGuideDetails.map((guide) => guide.topicId)).toEqual(
      manualTrustedContentV1TopicIds,
    );

    for (const guide of mockGuideDetails) {
      const sectionIds = guide.sections.map((section) => section.id);
      const trustedTopic = trustedTopicsById[guide.topicId ?? ""];

      expect(sectionIds).toEqual(requiredGuideSectionIds);
      expect(guide.sections.every((section) => section.body || section.items?.length)).toBe(
        true,
      );
      expect(guide.summary).toBe(trustedTopic.summary);
      expect(guide.requiredDocuments).toEqual(trustedTopic.requiredDocuments);
      expect(guide.steps).toEqual(trustedTopic.nextSteps);
      expect(guide.officialSources).toEqual(trustedTopic.officialSources);
      expect(guide.needsOfficialConfirmation).toBe(true);
      expect(guide.contentStatus).toBe("dynamic");
    }
  });

  it("calculates guide reading time from visible guide text", () => {
    for (const guide of mockGuideDetails) {
      const { estimatedReadMinutes, ...guideWithoutReadTime } = guide;

      expect(estimatedReadMinutes).toBeGreaterThanOrEqual(1);
      expect(estimatedReadMinutes).toBe(
        calculateEstimatedReadMinutes(guideWithoutReadTime),
      );
    }
  });

  it("keeps trusted mock analysis results rich without changing the result contract", () => {
    const trustedResults = mockAnalysisResults.filter((result) => result.source === "template");

    expect(trustedResults.length).toBeGreaterThanOrEqual(2);

    for (const result of trustedResults) {
      expect(result.summary.split(". ").length).toBeGreaterThanOrEqual(2);
      expect(result.importantPoints.length).toBeGreaterThanOrEqual(4);
      expect(result.nextSteps.length).toBeGreaterThanOrEqual(4);
      expect(result.officialWarning.length).toBeGreaterThan(120);
    }
  });

  it("does not invent file-only mock OCR details", () => {
    const result = getMockAnalysisResult({
      documentFile: {
        file: new File(["synthetic pdf"], "residence-tax.pdf", {
          type: "application/pdf",
        }),
        name: "residence-tax.pdf",
        type: "application/pdf",
        size: 13,
      },
    });

    expect(result.documentType).toBe("Residence Tax Notice");
    expect(result.deadline).toBeNull();
    expect(result.summary).toContain("not read with OCR");
    expect(result.importantPoints.join(" ")).toContain("did not perform OCR");
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
