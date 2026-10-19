import type { DocumentTemplate } from "../types";

export const documentTemplateResults = {
  nationalHealthInsurance: {
    id: "national-health-insurance-notice",
    source: "template",
    documentType: "National Health Insurance Notice",
    matchKeywords: ["国民健康保険", "保険料", "保険証", "insurance notice", "health insurance"],
    strongMatchKeywords: ["国民健康保険料", "国民健康保険納付", "National Health Insurance"],
    relatedTopicId: "national-health-insurance",
    trustedSummary:
      "This notice is about national health insurance. It may explain payment, enrollment, or a required confirmation step.",
    summary:
      "This notice is about national health insurance. It may explain payment, enrollment, or a required confirmation step.",
    deadline: null,
    defaultUrgency: "important",
    urgency: "important",
    importantPoints: [
      "Check whether the notice asks for payment or another action.",
      "Look for the amount, deadline, and contact information.",
      "The final details should be confirmed with your city office.",
    ],
    nextSteps: [
      "Read the payment or procedure section carefully.",
      "Confirm the deadline and payment method with your city office.",
      "Keep the notice and any receipt or reply document.",
    ],
    relatedGuide: "health-insurance-payment",
    officialWarning:
      "This is a support explanation, not a final decision. Please confirm health insurance procedures with your city office or official sources.",
  },
  nationalPension: {
    id: "national-pension-notice",
    source: "template",
    documentType: "National Pension Notice",
    matchKeywords: ["国民年金", "年金", "保険料", "免除", "猶予", "pension"],
    strongMatchKeywords: ["国民年金保険料", "年金納付", "National Pension"],
    relatedTopicId: "national-pension",
    trustedSummary:
      "This notice is about Japan's national pension system. It may explain payment, exemption, or a required pension procedure.",
    summary:
      "This notice is about Japan's national pension system. It may explain payment, exemption, or a required pension procedure.",
    deadline: null,
    defaultUrgency: "important",
    urgency: "important",
    importantPoints: [
      "Check whether the notice asks you to pay, apply, or confirm information.",
      "Look for any payment deadline or application deadline.",
      "Pension procedures can depend on your status and income situation.",
    ],
    nextSteps: [
      "Check the deadline area and required documents.",
      "Contact the pension office or city office if you are unsure.",
      "Ask official support before assuming you qualify for exemption or delay.",
    ],
    relatedGuide: "national-pension",
    officialWarning:
      "This is a support explanation, not a final pension decision. Please confirm pension procedures with the official pension office or city office.",
  },
  residenceTax: {
    id: "residence-tax-notice",
    source: "template",
    documentType: "Residence Tax Notice",
    matchKeywords: ["住民税", "市民税", "県民税", "納税通知書", "residence tax", "resident tax"],
    strongMatchKeywords: [
      "住民税納税通知書",
      "住民税のお知らせ",
      "市民税県民税",
      "Residence Tax Notice",
      "Resident Tax Notice",
    ],
    relatedTopicId: "residence-tax",
    trustedSummary:
      "This notice is about residence tax. It may show the amount to pay, payment periods, and where to ask questions.",
    summary:
      "This notice is about residence tax. It may show the amount to pay, payment periods, and where to ask questions.",
    deadline: null,
    defaultUrgency: "important",
    urgency: "important",
    importantPoints: [
      "Check the total amount and each payment due date.",
      "Look for the payment slip or payment method instructions.",
      "Late payment may create extra steps or fees.",
    ],
    nextSteps: [
      "Confirm the amount and deadline on the notice.",
      "Check official payment options from your city office.",
      "Ask the city tax desk if the amount or deadline is unclear.",
    ],
    relatedGuide: "residence-tax-payment",
    officialWarning:
      "This is a support explanation, not final tax advice. Please confirm residence tax details with your city office or official government sources.",
  },
  addressRegistration: {
    id: "address-registration-moving-notice",
    source: "template",
    documentType: "Address Registration Notice",
    matchKeywords: ["住所", "転入", "転出", "転居", "住民登録", "address registration", "moving notice"],
    strongMatchKeywords: [
      "転入届",
      "転出届",
      "転居届",
      "住所変更届",
      "住所登録",
      "moving notice",
      "moving procedures",
    ],
    relatedTopicId: "address-registration-moving",
    trustedSummary:
      "This notice is about registering or changing your address after moving in Japan.",
    summary:
      "This notice is about registering or changing your address after moving in Japan.",
    deadline: null,
    defaultUrgency: "important",
    urgency: "important",
    importantPoints: [
      "Address procedures are usually handled at the city office.",
      "You may need your residence card and other identification.",
      "The required timing can depend on your moving situation.",
    ],
    nextSteps: [
      "Confirm whether the notice is about moving in, moving out, or address change.",
      "Prepare your residence card and related documents.",
      "Contact your city office to confirm the deadline and required forms.",
    ],
    relatedGuide: "moving-address-registration",
    officialWarning:
      "This is a support explanation. Please confirm address registration deadlines and required documents with your city office.",
  },
  immigrationResidenceStatus: {
    id: "immigration-residence-status-notice",
    source: "template",
    documentType: "Immigration / Residence Status Notice",
    matchKeywords: ["在留資格", "在留期間", "入国在留管理局", "追加資料", "residence status", "immigration"],
    strongMatchKeywords: ["在留期間更新", "在留資格更新", "更新申請"],
    relatedTopicId: "residence-status-renewal",
    trustedSummary:
      "This notice is about an immigration or residence-status procedure. It may ask for documents, confirmation, or an official visit.",
    summary:
      "This notice is about an immigration or residence-status procedure. It may ask for documents, confirmation, or an official visit.",
    deadline: null,
    defaultUrgency: "urgent",
    urgency: "urgent",
    importantPoints: [
      "Check whether the notice asks for additional documents or an office visit.",
      "Look for a deadline, reference number, and official contact information.",
      "This notice does not guarantee approval or a final result.",
    ],
    nextSteps: [
      "Confirm the request with the Immigration Services Agency or official support.",
      "Prepare only the documents clearly requested by the official notice.",
      "Do not assume approval, denial, or status change from this explanation.",
    ],
    relatedGuide: "residence-status-renewal",
    officialWarning:
      "This is a support explanation, not immigration advice or an approval decision. Please confirm all residence-status procedures with official immigration sources.",
  },
  schoolAdministrativePayment: {
    id: "school-administrative-payment-notice",
    source: "template",
    documentType: "School Administrative / Payment Notice",
    matchKeywords: ["学校", "学生課", "事務室", "授業料", "学生証", "tuition", "school notice"],
    strongMatchKeywords: ["授業料納入", "学生課からのお知らせ", "school payment"],
    relatedTopicId: "school-administrative-notices",
    trustedSummary:
      "This notice is about a school administrative task, payment, student ID update, or document submission.",
    summary:
      "This notice is about a school administrative task, payment, student ID update, or document submission.",
    deadline: null,
    defaultUrgency: "important",
    urgency: "important",
    importantPoints: [
      "Check whether the school is asking for payment, documents, or confirmation.",
      "Look for the deadline, required items, and student office contact details.",
      "School-specific rules should be confirmed with the school office.",
    ],
    nextSteps: [
      "Confirm the request with the student office or listed department.",
      "Prepare only the documents or payment information shown on the notice.",
      "Keep a copy of the notice and any reply or receipt.",
    ],
    relatedGuide: null,
    officialWarning:
      "This is a support explanation. Please confirm school-specific requirements with the school office or official school source.",
  },
  employmentWorkingConditions: {
    id: "employment-working-conditions-notice",
    source: "template",
    documentType: "Employment / Working Conditions Notice",
    matchKeywords: ["労働条件", "雇用契約", "賃金", "勤務時間", "休日", "employment contract", "working conditions"],
    strongMatchKeywords: ["労働条件通知書", "雇用契約書", "working conditions notice"],
    relatedTopicId: "employment-working-conditions",
    trustedSummary:
      "This document appears to describe employment terms such as contract period, wages, working hours, holidays, or workplace rules.",
    summary:
      "This document appears to describe employment terms such as contract period, wages, working hours, holidays, or workplace rules.",
    deadline: null,
    defaultUrgency: "important",
    urgency: "important",
    importantPoints: [
      "Check contract period, wages, working hours, holidays, and workplace rules.",
      "Do not treat this explanation as a legal review of the contract.",
      "Unclear or risky terms should be confirmed with official labor support.",
    ],
    nextSteps: [
      "List any unclear conditions before signing or agreeing.",
      "Ask the employer for clarification when needed.",
      "Contact official labor support if the document seems risky or confusing.",
    ],
    relatedGuide: null,
    officialWarning:
      "This is a support explanation, not legal advice or a final contract decision. Please confirm working-conditions questions with official labor support or a trusted adviser.",
  },
  studentToWorkerTransition: {
    id: "student-to-worker-transition-notice",
    source: "template",
    documentType: "Student to Worker Status Change Notice",
    matchKeywords: [
      "在留資格変更",
      "留学",
      "就労",
      "卒業",
      "内定",
      "student to worker",
      "change status after graduation",
    ],
    strongMatchKeywords: [
      "留学から就労資格への変更",
      "留学から就労",
      "在留資格変更許可申請",
      "student to work visa",
    ],
    relatedTopicId: "student-to-worker-transition",
    trustedSummary:
      "This document appears to concern changing from Student residence status to a work-related status after graduation or a job offer.",
    summary:
      "This document appears to concern changing from Student residence status to a work-related status after graduation or a job offer.",
    deadline: null,
    defaultUrgency: "important",
    urgency: "important",
    importantPoints: [
      "A job offer does not automatically change residence status.",
      "Check graduation timing, the planned job start date, and the current period of stay together.",
      "The school, employer, and immigration office may each need to provide or confirm documents.",
    ],
    nextSteps: [
      "Confirm the job duties and start date with the employer.",
      "Ask the school which graduation or support documents it can provide.",
      "Confirm the final application and timing with official immigration sources.",
    ],
    relatedGuide: "job-hunting-before-graduation",
    officialWarning:
      "This is a support explanation, not an immigration decision or approval guarantee. Confirm the status-change procedure with the Immigration Services Agency or a regional immigration office.",
  },
  partTimeWorkPermission: {
    id: "part-time-work-permission-notice",
    source: "template",
    documentType: "Student Part-Time Work Permission Notice",
    matchKeywords: [
      "資格外活動",
      "アルバイト許可",
      "学生のアルバイト",
      "part-time work permission",
      "activity outside status",
    ],
    strongMatchKeywords: [
      "資格外活動許可",
      "資格外活動許可申請",
      "activity outside status",
      "permission to engage in activity outside status",
    ],
    relatedTopicId: "part-time-work-permission",
    trustedSummary:
      "This document appears to concern immigration permission for paid activity outside a student's current residence status.",
    summary:
      "This document appears to concern immigration permission for paid activity outside a student's current residence status.",
    deadline: null,
    defaultUrgency: "important",
    urgency: "important",
    importantPoints: [
      "A job offer or work schedule is not the same as immigration permission.",
      "Check the residence card and official immigration documents for permission details.",
      "School rules and employer paperwork are separate from immigration permission.",
    ],
    nextSteps: [
      "Check the residence card and any immigration permission document.",
      "Ask the school whether students must report part-time work.",
      "Confirm unclear permission details with official immigration sources before starting work.",
    ],
    relatedGuide: "part-time-work-permission",
    officialWarning:
      "This is a support explanation, not immigration permission. Confirm whether work is allowed with the Immigration Services Agency or a regional immigration office before relying on this result.",
  },
  generalCityHall: {
    id: "general-city-hall-notice",
    source: "template",
    documentType: "City Hall Administrative Notice",
    matchKeywords: ["市役所", "区役所", "通知", "案内", "手続き", "窓口", "city hall", "ward office"],
    strongMatchKeywords: ["市役所からのお知らせ", "区役所からのお知らせ", "municipal notice"],
    relatedTopicId: "city-hall-general-notices",
    trustedSummary:
      "This appears to be a general city or ward office notice. It may be informational or may request a procedure.",
    summary:
      "This appears to be a general city or ward office notice. It may be informational or may request a procedure.",
    deadline: null,
    defaultUrgency: "important",
    urgency: "important",
    importantPoints: [
      "Check the sender, department, and purpose of the notice.",
      "Look for any deadline, required documents, or contact desk.",
      "Details can vary by city, so official confirmation is important.",
    ],
    nextSteps: [
      "Identify the issuing office and department.",
      "Check whether the notice requires action or is only information.",
      "Contact the listed office if the purpose or deadline is unclear.",
    ],
    relatedGuide: null,
    officialWarning:
      "This is a support explanation. Please confirm city hall procedures with the issuing city or ward office.",
  },
} satisfies Record<string, DocumentTemplate>;

export const documentTemplates = Object.values(documentTemplateResults);
