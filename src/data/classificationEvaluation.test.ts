import { describe, expect, it } from "vitest";
import { evaluateClassification, formatEvaluation } from "./classificationEvaluation";

describe("Trusted Result Generation V2 evaluation", () => {
  it("derives measurable metrics from the synthetic dataset", () => {
    const evaluation = evaluateClassification();
    console.info(`\n${formatEvaluation(evaluation)}\n`);
    console.info("Evaluation failures:", evaluation.failures);

    expect(evaluation.totalCases).toBeGreaterThanOrEqual(40);
    expect(evaluation.totalCases).toBeLessThanOrEqual(60);
    expect(evaluation.classificationCorrectness.passed).toBeGreaterThanOrEqual(45);
    expect(evaluation.falseTrustedMatches).toBe(0);
    expect(evaluation.unknownRejectionAccuracy.passed).toBe(
      evaluation.unknownRejectionAccuracy.total,
    );
    expect(evaluation.deadlineExtractionCorrectness.passed).toBe(
      evaluation.deadlineExtractionCorrectness.total,
    );
    expect(evaluation.schemaValidity.passed).toBe(evaluation.schemaValidity.total);
    expect(evaluation.officialWarningPresence.passed).toBe(
      evaluation.officialWarningPresence.total,
    );
    expect(evaluation.relatedGuideCorrectness.passed).toBe(
      evaluation.relatedGuideCorrectness.total,
    );
  });
});
