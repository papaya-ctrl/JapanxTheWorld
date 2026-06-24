import type { DocumentAnalysisRequest, DocumentAnalysisResult } from "../types";

export const mockAnalysisResults: DocumentAnalysisResult[] = [
  {
    source: "template",
    documentType: "Residence Tax Notice",
    summary:
      "This document explains your residence tax amount and payment schedule.",
    deadline: "2026-07-31",
    urgency: "important",
    importantPoints: [
      "Check the total amount you need to pay.",
      "Look for the official payment deadline on the notice.",
      "Keep the notice because you may need it later.",
    ],
    nextSteps: [
      "Confirm the payment deadline written on the notice.",
      "Review official payment options from your city office.",
      "Ask official support if you are unsure about the amount.",
    ],
    relatedGuide: "residence-tax-payment",
    officialWarning:
      "Please confirm important tax procedures with your city office or official government sources.",
  },
  {
    source: "template",
    documentType: "National Health Insurance Payment Notice",
    summary:
      "This notice tells you the amount you need to pay for national health insurance.",
    deadline: "2026-08-10",
    urgency: "important",
    importantPoints: [
      "The document includes a payment amount.",
      "There is a due date for payment.",
      "Late payment may cause problems.",
    ],
    nextSteps: [
      "Check the due date on the notice.",
      "Review official payment options from your city office.",
      "Ask your city office if you do not understand the notice.",
    ],
    relatedGuide: "health-insurance-payment",
    officialWarning:
      "Please confirm health insurance payment details with your city office or official government sources.",
  },
  {
    source: "ai",
    documentType: "Unknown municipal notice",
    summary:
      "This looks like a city office notice about a required response, but the exact purpose is not fully clear from the text provided.",
    deadline: null,
    urgency: "important",
    importantPoints: [
      "The document appears to request action from you.",
      "The exact deadline is not clear from the text.",
      "You should verify the purpose with official support.",
    ],
    nextSteps: [
      "Check the sender name and contact information on the document.",
      "Contact the city office or listed support desk.",
      "Bring the document to official support if you need confirmation.",
    ],
    relatedGuide: null,
    officialWarning:
      "This result may be incomplete. Please confirm the document meaning and any deadlines with the official sender.",
  },
];

export const getMockAnalysisResult = (
  request: DocumentAnalysisRequest,
): DocumentAnalysisResult => {
  const text = request.documentText.toLowerCase();
  const hint = request.documentTypeHint?.toLowerCase() ?? "";

  if (
    text.includes("residence tax") ||
    text.includes("住民税") ||
    hint.includes("tax")
  ) {
    return mockAnalysisResults[0];
  }

  if (
    text.includes("insurance") ||
    text.includes("保険") ||
    hint.includes("insurance")
  ) {
    return mockAnalysisResults[1];
  }

  return mockAnalysisResults[2];
};
