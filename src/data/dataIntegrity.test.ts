import { describe, expect, it } from "vitest";
import { isDocumentAnalysisResult } from "../api/client";
import { aiTestCases } from "./aiTestCases";
import { documentTemplates } from "./documentTemplates";
import { getMockAnalysisResult, mockAnalysisResults } from "./mockAnalysis";
import { calculateEstimatedReadMinutes, mockGuideDetails } from "./mockGuides";
import { trustedTopicsById, trustedTopics } from "./trustedTopics";
import {
  classifyTrustedInput,
  extractExplicitDeadline,
} from "./trustedClassification";

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
    expect(aiTestCases.length).toBeGreaterThanOrEqual(40);
    expect(aiTestCases.length).toBeLessThanOrEqual(60);
    expect(aiTestCases.some((testCase) => testCase.expectedDeadline === null)).toBe(true);
    expect(aiTestCases.some((testCase) => testCase.expectedDeadline !== null)).toBe(true);
    expect(
      aiTestCases.some((testCase) => testCase.inputJapanese.includes("令和")),
    ).toBe(true);
    expect(aiTestCases.filter((testCase) => !testCase.expectTrustedMatch).length).toBeGreaterThanOrEqual(8);
  });
});

describe("Trusted Result Generation V2 classifier", () => {
  it("matches a strong example for every Manual Trusted Content V1 topic", () => {
    const strongTopicIds = aiTestCases
      .filter((testCase) => testCase.group === "strong")
      .map((testCase) => classifyTrustedInput(testCase.inputJapanese).topicId);

    expect(strongTopicIds).toEqual(manualTrustedContentV1TopicIds);
  });

  it("does not inflate confidence when the same keyword repeats", () => {
    const once = classifyTrustedInput("住民税");
    const repeated = classifyTrustedInput("住民税 住民税 住民税");

    expect(repeated.topicId).toBe("residence-tax");
    expect(repeated.confidence).toBe(once.confidence);
    expect(repeated.candidateScores).toEqual(once.candidateScores);
  });

  it.each([
    "納付期限があります。期限までに支払ってください。",
    "重要なお知らせです。内容を確認してください。",
    "学校の文化祭は来週の日曜日です。参加したい学生は先生に連絡してください。",
    "保険について確認してください。",
    "税金について質問があります。",
  ])("rejects ambiguous or unrelated input: %s", (input) => {
    expect(classifyTrustedInput(input)).toMatchObject({
      topicId: null,
      documentTemplateId: null,
    });
    expect(getMockAnalysisResult({ documentText: input }).source).toBe("ai");
  });

  it("rejects mixed conflicting topics without forcing a winner", () => {
    expect(
      classifyTrustedInput("住民税と国民年金のどちらの納付書か分かりません。"),
    ).toMatchObject({ topicId: null, documentTemplateId: null });
  });

  it("lets an exact document phrase beat weaker generic topic evidence", () => {
    expect(
      classifyTrustedInput("住民税納税通知書です。年金という参考語もあります。"),
    ).toMatchObject({
      topicId: "residence-tax",
      documentTemplateId: "residence-tax-notice",
    });
  });

  it("does not invent a precise template for broad topic wording", () => {
    expect(classifyTrustedInput("住民税について質問があります。"))
      .toMatchObject({
        topicId: "residence-tax",
        documentTemplateId: null,
      });
  });

  it("extracts only valid, explicit deadlines", () => {
    expect(extractExplicitDeadline("提出期限は2026年10月31日です。"))
      .toBe("2026-10-31");
    expect(extractExplicitDeadline("納期限は令和8年6月30日です。"))
      .toBe("2026-06-30");
    expect(extractExplicitDeadline("説明会は2026年10月31日に行われました。"))
      .toBeNull();
    expect(extractExplicitDeadline("提出期限は2026年2月30日です。"))
      .toBeNull();
  });

  it("returns rich trusted results and cautious low-confidence fallback results", () => {
    const trusted = getMockAnalysisResult({
      documentText: "国民年金保険料納付書。納期限は2026年10月31日です。",
    });
    const fallback = getMockAnalysisResult({ documentText: "重要なお知らせです。" });

    expect(trusted.source).toBe("template");
    expect(trusted.deadline).toBe("2026-10-31");
    expect(trusted.importantPoints.length).toBeGreaterThanOrEqual(4);
    expect(trusted.nextSteps.length).toBeGreaterThanOrEqual(4);
    expect(fallback.source).toBe("ai");
    expect(fallback.summary).toContain("does not contain enough");
    expect(fallback.deadline).toBeNull();
  });

  it("derives urgency from explicit wording instead of topic alone", () => {
    const normalImmigration = getMockAnalysisResult({
      documentText: "在留期間更新申請のお知らせです。期限は記載されていません。",
    });
    const urgentTax = getMockAnalysisResult({
      documentText: "住民税納税通知書。最終督促のため直ちに市役所へ確認してください。",
    });
    const informationalPension = getMockAnalysisResult({
      documentText: "国民年金制度に関する案内です。制度を説明しています。",
    });

    expect(normalImmigration.urgency).toBe("important");
    expect(urgentTax.urgency).toBe("urgent");
    expect(informationalPension.urgency).toBe("low");
  });

  it("keeps every evaluated result schema-valid, useful, unique, and safe", () => {
    const validGuideIds = new Set(mockGuideDetails.map((guide) => guide.id));

    for (const testCase of aiTestCases) {
      const result = getMockAnalysisResult({ documentText: testCase.inputJapanese });

      expect(isDocumentAnalysisResult(result)).toBe(true);
      expect(result.summary.trim()).not.toBe("");
      expect(result.importantPoints.length).toBeGreaterThanOrEqual(4);
      expect(result.nextSteps.length).toBeGreaterThanOrEqual(4);
      expect(new Set(result.importantPoints).size).toBe(result.importantPoints.length);
      expect(new Set(result.nextSteps).size).toBe(result.nextSteps.length);
      expect(`${result.summary} ${result.importantPoints.join(" ")} ${result.nextSteps.join(" ")}`)
        .not.toMatch(/lorem ipsum|\d[\d,]*円|will be approved|is guaranteed/i);
      expect(result.officialWarning.trim().length).toBeGreaterThan(20);
      if (result.relatedGuide) {
        expect(validGuideIds.has(result.relatedGuide)).toBe(true);
      }
    }
  });
});
