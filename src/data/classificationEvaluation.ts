import { isDocumentAnalysisResult } from "../api/client";
import { aiTestCases } from "./aiTestCases";
import { getMockAnalysisResult } from "./mockAnalysis";
import { classifyTrustedInput } from "./trustedClassification";

type Metric = {
  passed: number;
  total: number;
};

export type ClassificationEvaluation = {
  totalCases: number;
  classificationCorrectness: Metric;
  falseTrustedMatches: number;
  unknownRejectionAccuracy: Metric;
  deadlineExtractionCorrectness: Metric;
  schemaValidity: Metric;
  officialWarningPresence: Metric;
  relatedGuideCorrectness: Metric;
  failures: {
    classification: string[];
    unknownRejection: string[];
    deadline: string[];
    schema: string[];
    officialWarning: string[];
    relatedGuide: string[];
  };
};

export const evaluateClassification = (): ClassificationEvaluation => {
  const failures: ClassificationEvaluation["failures"] = {
    classification: [],
    unknownRejection: [],
    deadline: [],
    schema: [],
    officialWarning: [],
    relatedGuide: [],
  };
  let falseTrustedMatches = 0;
  let unknownTotal = 0;

  for (const testCase of aiTestCases) {
    const classification = classifyTrustedInput(testCase.inputJapanese);
    const result = getMockAnalysisResult({ documentText: testCase.inputJapanese });

    if (
      classification.topicId !== testCase.expectedTopicId ||
      classification.documentTemplateId !== testCase.expectedTemplateId
    ) {
      failures.classification.push(
        `${testCase.id} (expected ${testCase.expectedTopicId ?? "null"}/${testCase.expectedTemplateId ?? "null"}; received ${classification.topicId ?? "null"}/${classification.documentTemplateId ?? "null"}; ${classification.reason ?? "no reason"}; ${JSON.stringify(classification.candidateScores ?? [])})`,
      );
    }

    if (!testCase.expectTrustedMatch) {
      unknownTotal += 1;
      if (classification.topicId !== null || result.source !== "ai") {
        failures.unknownRejection.push(
          `${testCase.id} (received ${classification.topicId ?? "null"}, source ${result.source})`,
        );
      }
      if (result.source === "template") {
        falseTrustedMatches += 1;
      }
    }

    if (result.deadline !== testCase.expectedDeadline) {
      failures.deadline.push(
        `${testCase.id} (expected ${testCase.expectedDeadline ?? "null"}; received ${result.deadline ?? "null"})`,
      );
    }

    if (!isDocumentAnalysisResult(result)) {
      failures.schema.push(testCase.id);
    }

    if (result.officialWarning.trim().length < 20) {
      failures.officialWarning.push(testCase.id);
    }

    if (result.relatedGuide !== testCase.expectedRelatedGuide) {
      failures.relatedGuide.push(
        `${testCase.id} (expected ${testCase.expectedRelatedGuide ?? "null"}; received ${result.relatedGuide ?? "null"})`,
      );
    }
  }

  const totalCases = aiTestCases.length;
  return {
    totalCases,
    classificationCorrectness: {
      passed: totalCases - failures.classification.length,
      total: totalCases,
    },
    falseTrustedMatches,
    unknownRejectionAccuracy: {
      passed: unknownTotal - failures.unknownRejection.length,
      total: unknownTotal,
    },
    deadlineExtractionCorrectness: {
      passed: totalCases - failures.deadline.length,
      total: totalCases,
    },
    schemaValidity: {
      passed: totalCases - failures.schema.length,
      total: totalCases,
    },
    officialWarningPresence: {
      passed: totalCases - failures.officialWarning.length,
      total: totalCases,
    },
    relatedGuideCorrectness: {
      passed: totalCases - failures.relatedGuide.length,
      total: totalCases,
    },
    failures,
  };
};

export const formatEvaluation = (evaluation: ClassificationEvaluation) => {
  const percentage = (metric: Metric) =>
    metric.total === 0 ? 100 : Math.round((metric.passed / metric.total) * 1000) / 10;

  return [
    `Classification accuracy: ${evaluation.classificationCorrectness.passed} / ${evaluation.classificationCorrectness.total} (${percentage(evaluation.classificationCorrectness)}%)`,
    `Unknown rejection: ${evaluation.unknownRejectionAccuracy.passed} / ${evaluation.unknownRejectionAccuracy.total} (${percentage(evaluation.unknownRejectionAccuracy)}%)`,
    `False trusted matches: ${evaluation.falseTrustedMatches}`,
    `Deadline extraction: ${evaluation.deadlineExtractionCorrectness.passed} / ${evaluation.deadlineExtractionCorrectness.total} (${percentage(evaluation.deadlineExtractionCorrectness)}%)`,
    `Schema validity: ${evaluation.schemaValidity.passed} / ${evaluation.schemaValidity.total} (${percentage(evaluation.schemaValidity)}%)`,
    `Official warning presence: ${evaluation.officialWarningPresence.passed} / ${evaluation.officialWarningPresence.total} (${percentage(evaluation.officialWarningPresence)}%)`,
    `Related-guide correctness: ${evaluation.relatedGuideCorrectness.passed} / ${evaluation.relatedGuideCorrectness.total} (${percentage(evaluation.relatedGuideCorrectness)}%)`,
  ].join("\n");
};
