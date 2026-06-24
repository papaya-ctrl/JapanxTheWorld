import type { GuideDetail, GuideSummary } from "../types";

export const mockGuides: GuideSummary[] = [
  {
    id: "moving-address-registration",
    title: "Address Registration After Moving",
    category: "City Hall",
    summary: "What to do after moving to a new address in Japan.",
    estimatedReadMinutes: 5,
  },
  {
    id: "residence-tax-payment",
    title: "How To Handle A Residence Tax Notice",
    category: "Tax",
    summary: "Understand the notice, the deadline, and where to confirm details.",
    estimatedReadMinutes: 6,
  },
  {
    id: "health-insurance-payment",
    title: "Paying National Health Insurance",
    category: "Insurance",
    summary:
      "Check what the notice means and what to confirm before paying.",
    estimatedReadMinutes: 4,
  },
  {
    id: "job-hunting-before-graduation",
    title: "Preparing For Job Hunting Before Graduation",
    category: "Career",
    summary: "A practical checklist for students who want to work in Japan.",
    estimatedReadMinutes: 7,
  },
];

export const mockGuideDetails: GuideDetail[] = [
  {
    ...mockGuides[0],
    audience: "Students and workers who changed residence in Japan",
    requiredDocuments: [
      "Residence card",
      "My Number card if available",
      "Any city hall moving forms you received",
    ],
    steps: [
      "Visit your city office soon after moving.",
      "Bring your residence card and any related identification.",
      "Complete the address registration form carefully.",
      "Ask the staff to confirm whether any other procedures are needed.",
    ],
    officialResourceIds: ["city-hall-moving-guide"],
  },
  {
    ...mockGuides[1],
    audience: "Students and workers who received a residence tax notice",
    requiredDocuments: [
      "Residence tax notice",
      "Any payment slips included with the notice",
    ],
    steps: [
      "Check the payment amount and deadline written on the notice.",
      "Review the payment method options from your city office.",
      "If the amount seems unclear, contact the official support desk shown on the notice.",
      "Keep the notice and payment record for later reference.",
    ],
    officialResourceIds: ["soumu-tax", "city-tax-helpdesk"],
  },
  {
    ...mockGuides[2],
    audience: "Residents who received a national health insurance payment notice",
    requiredDocuments: [
      "Health insurance notice",
      "Residence card",
      "Payment slip if attached",
    ],
    steps: [
      "Confirm the due date and amount on the notice.",
      "Check official payment options from your city office.",
      "Contact the official help desk if you think the amount is wrong.",
      "Pay before the deadline and keep the receipt if payment is required.",
    ],
    officialResourceIds: ["mhlw-insurance", "city-insurance-helpdesk"],
  },
  {
    ...mockGuides[3],
    audience: "International students planning to work in Japan",
    requiredDocuments: [
      "Resume or CV",
      "Residence card",
      "Graduation schedule information",
    ],
    steps: [
      "Start job research early and track company deadlines.",
      "Prepare your application documents and interview schedule.",
      "Confirm work-related residence status steps with official sources or school support.",
      "Keep all important employment and visa-related documents organized.",
    ],
    officialResourceIds: ["isa-main", "hello-work"],
  },
];

export const mockGuideDetailsById = Object.fromEntries(
  mockGuideDetails.map((guide) => [guide.id, guide]),
) as Record<string, GuideDetail>;
