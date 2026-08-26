import type { AnalysisUrgency } from "../types";

export type AiTestCase = {
  id: string;
  name: string;
  category: string;
  inputJapanese: string;
  expected: {
    documentTypeContains?: string[];
    topicId?: string | null;
    documentTemplateId?: string | null;
    confidenceRange?: {
      min: number;
      max: number;
    };
    deadline: string | null;
    urgency: AnalysisUrgency;
    requiredImportantPoints: string[];
    requiredNextSteps: string[];
  };
};

export const aiTestCases: AiTestCase[] = [
  {
    id: "ai-case-001",
    name: "Health insurance payment notice with clear deadline",
    category: "National Health Insurance notice",
    inputJapanese:
      "国民健康保険料のお知らせです。保険料12,000円を2026年8月10日までにお支払いください。納付方法は同封の案内をご確認ください。発行元は見本市保険課です。",
    expected: {
      documentTypeContains: ["Health Insurance"],
      deadline: "2026-08-10",
      urgency: "important",
      requiredImportantPoints: ["payment amount", "due date", "health insurance"],
      requiredNextSteps: ["confirm the deadline", "check payment methods"],
    },
  },
  {
    id: "ai-case-002",
    name: "National pension notice with Reiwa deadline",
    category: "National Pension notice",
    inputJapanese:
      "国民年金保険料に関する通知です。令和8年6月30日までに必要な手続きを行ってください。免除申請を希望する場合は、年金窓口で確認してください。",
    expected: {
      documentTypeContains: ["Pension"],
      deadline: "2026-06-30",
      urgency: "important",
      requiredImportantPoints: ["pension", "procedure", "deadline"],
      requiredNextSteps: ["confirm with the pension office", "check required documents"],
    },
  },
  {
    id: "ai-case-003",
    name: "Residence tax payment notice",
    category: "Residence Tax notice",
    inputJapanese:
      "住民税納税通知書。第1期分の納期限は2026年7月31日です。金額と納付場所を確認し、期限までに納付してください。",
    expected: {
      documentTypeContains: ["Residence Tax"],
      deadline: "2026-07-31",
      urgency: "important",
      requiredImportantPoints: ["residence tax", "payment", "deadline"],
      requiredNextSteps: ["confirm the amount", "check payment options"],
    },
  },
  {
    id: "ai-case-004",
    name: "Address registration reminder after moving",
    category: "Address registration / moving notice",
    inputJapanese:
      "転入届に関するご案内です。新しい住所に住み始めた方は、必要書類を持って見本市役所の窓口で住所登録の手続きをしてください。期限がある場合があります。",
    expected: {
      documentTypeContains: ["Address", "Registration"],
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["address registration", "city office", "required documents"],
      requiredNextSteps: ["visit city office", "confirm deadline"],
    },
  },
  {
    id: "ai-case-005",
    name: "Immigration residence-status notice",
    category: "Immigration / residence-status notice",
    inputJapanese:
      "在留資格に関するお知らせです。追加資料の提出が必要です。提出期限は2026年9月15日です。この通知は許可を保証するものではありません。",
    expected: {
      documentTypeContains: ["Immigration", "Residence Status"],
      deadline: "2026-09-15",
      urgency: "urgent",
      requiredImportantPoints: ["additional documents", "deadline", "not guaranteed"],
      requiredNextSteps: ["prepare documents", "confirm with immigration"],
    },
  },
  {
    id: "ai-case-006",
    name: "School payment notice",
    category: "School payment or administrative notice",
    inputJapanese:
      "授業料納入のお知らせです。2026年度前期分の授業料を2026年4月20日までに納入してください。不明な点は学校事務室で確認してください。",
    expected: {
      documentTypeContains: ["School", "Payment"],
      deadline: "2026-04-20",
      urgency: "important",
      requiredImportantPoints: ["tuition", "payment", "school office"],
      requiredNextSteps: ["confirm amount", "contact school office"],
    },
  },
  {
    id: "ai-case-007",
    name: "Employment working conditions notice",
    category: "Employment contract / working conditions notice",
    inputJapanese:
      "労働条件通知書。契約期間、勤務時間、賃金、休日について記載しています。内容を確認し、不明な点は会社担当者または公的相談窓口に確認してください。",
    expected: {
      documentTypeContains: ["Employment", "Working Conditions"],
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["working hours", "wages", "contract period"],
      requiredNextSteps: ["review conditions", "ask official support"],
    },
  },
  {
    id: "ai-case-008",
    name: "Part-time work shift warning",
    category: "Part-time work related notice",
    inputJapanese:
      "アルバイト勤務に関する連絡です。来月のシフト提出期限は2026年5月25日です。勤務可能時間を確認して担当者へ提出してください。",
    expected: {
      documentTypeContains: ["Part-Time", "Work"],
      deadline: "2026-05-25",
      urgency: "important",
      requiredImportantPoints: ["shift", "submission deadline", "work availability"],
      requiredNextSteps: ["confirm schedule", "submit to manager"],
    },
  },
  {
    id: "ai-case-009",
    name: "City hall information-only notice",
    category: "City hall general administrative notice",
    inputJapanese:
      "見本市役所からのお知らせです。窓口受付時間が来月から変更になります。手続きの内容により受付時間が異なる場合があります。",
    expected: {
      documentTypeContains: ["City Hall", "Administrative"],
      deadline: null,
      urgency: "low",
      requiredImportantPoints: ["office hours", "city office"],
      requiredNextSteps: ["check office hours", "confirm before visiting"],
    },
  },
  {
    id: "ai-case-010",
    name: "Unclear official document fragment",
    category: "Unknown/general official Japanese document",
    inputJapanese:
      "通知。確認してください。必要な場合は窓口へ。日付や手続き名の一部が読めません。発行元の一部も不明です。",
    expected: {
      documentTypeContains: ["Unknown"],
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["unclear", "official sender", "missing details"],
      requiredNextSteps: ["confirm with the sender", "bring the document"],
    },
  },
  {
    id: "ai-case-011",
    name: "Urgent final administrative reminder",
    category: "City hall general administrative notice",
    inputJapanese:
      "重要・最終確認のお願い。未提出の書類があります。2026年3月5日までに見本市役所へ提出してください。期限を過ぎると手続きが遅れる可能性があります。",
    expected: {
      documentTypeContains: ["City Hall", "Administrative"],
      deadline: "2026-03-05",
      urgency: "urgent",
      requiredImportantPoints: ["final reminder", "missing documents", "deadline"],
      requiredNextSteps: ["prepare documents", "contact city office"],
    },
  },
  {
    id: "ai-case-012",
    name: "Ambiguous date that should not become a deadline",
    category: "Unknown/general official Japanese document",
    inputJapanese:
      "説明会は2026年6月1日に行われました。今後の手続きについては別途お知らせします。提出期限はこの通知には記載されていません。",
    expected: {
      documentTypeContains: ["Unknown", "Administrative"],
      deadline: null,
      urgency: "low",
      requiredImportantPoints: ["no deadline", "future notice"],
      requiredNextSteps: ["wait for next notice", "confirm if unsure"],
    },
  },
  {
    id: "ai-case-013",
    name: "Immigration postcard with missing deadline",
    category: "Immigration / residence-status notice",
    inputJapanese:
      "在留手続きに関するはがきです。結果または追加案内について、入国在留管理局の窓口で確認してください。期限欄は空白です。",
    expected: {
      documentTypeContains: ["Immigration", "Residence Status"],
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["immigration", "deadline not shown", "confirm at office"],
      requiredNextSteps: ["contact immigration", "do not assume approval"],
    },
  },
  {
    id: "ai-case-014",
    name: "School administrative notice without payment",
    category: "School payment or administrative notice",
    inputJapanese:
      "学生課からのお知らせです。学生証の更新手続きが始まります。必要な持ち物は学生証と申請用紙です。具体的な締切日は掲示板で確認してください。",
    expected: {
      documentTypeContains: ["School", "Administrative"],
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["student ID", "required items", "deadline not clear"],
      requiredNextSteps: ["check school notice board", "ask student office"],
    },
  },
  {
    id: "ai-case-015",
    name: "Pension information-only notice",
    category: "National Pension notice",
    inputJapanese:
      "国民年金制度に関する案内です。保険料の納付方法や免除制度について説明しています。この案内には提出期限や支払期限は記載されていません。",
    expected: {
      documentTypeContains: ["Pension"],
      deadline: null,
      urgency: "low",
      requiredImportantPoints: ["pension system", "payment methods", "no deadline"],
      requiredNextSteps: ["review options", "confirm with pension office"],
    },
  },
  {
    id: "ai-case-016",
    name: "Moving-out notice with Reiwa date",
    category: "Address registration / moving notice",
    inputJapanese:
      "転出届の手続きについて。令和8年10月12日までに転出予定日と新住所を確認し、見本市役所で手続きを行ってください。",
    expected: {
      documentTypeContains: ["Address", "Registration", "Moving"],
      deadline: "2026-10-12",
      urgency: "important",
      requiredImportantPoints: ["moving-out", "new address", "deadline"],
      requiredNextSteps: ["visit city office", "bring required documents"],
    },
  },
  {
    id: "ai-case-017",
    name: "Exact known keyword for health insurance",
    category: "Known topic classification",
    inputJapanese:
      "国民健康保険について知りたいです。見本市から届いた案内の内容を確認したいです。",
    expected: {
      documentTypeContains: ["Health Insurance"],
      topicId: "national-health-insurance",
      documentTemplateId: "national-health-insurance-notice",
      confidenceRange: { min: 0.8, max: 1 },
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["health insurance", "city office"],
      requiredNextSteps: ["confirm with city office", "check notice"],
    },
  },
  {
    id: "ai-case-018",
    name: "Alias match for resident tax",
    category: "Known topic classification",
    inputJapanese:
      "resident tax notice と書かれた紙を受け取りました。支払い方法と確認先を知りたいです。",
    expected: {
      documentTypeContains: ["Residence Tax"],
      topicId: "residence-tax",
      documentTemplateId: "residence-tax-notice",
      confidenceRange: { min: 0.75, max: 1 },
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["tax", "payment"],
      requiredNextSteps: ["confirm amount", "contact city office"],
    },
  },
  {
    id: "ai-case-019",
    name: "Mixed English and Japanese immigration input",
    category: "Known topic classification",
    inputJapanese:
      "I received 在留期間更新のお知らせ from immigration. 追加資料 may be needed, but I cannot find a clear due date.",
    expected: {
      documentTypeContains: ["Immigration", "Residence Status"],
      topicId: "residence-status-renewal",
      documentTemplateId: "immigration-residence-status-notice",
      confidenceRange: { min: 0.75, max: 1 },
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["additional documents", "deadline not clear"],
      requiredNextSteps: ["confirm with immigration", "prepare documents"],
    },
  },
  {
    id: "ai-case-020",
    name: "Similar but unrelated insurance keyword",
    category: "Low-confidence classification",
    inputJapanese:
      "自転車保険の広告チラシです。キャンペーン期間は2026年12月までと書かれています。市役所や国民健康保険の通知ではありません。",
    expected: {
      documentTypeContains: ["Unknown"],
      topicId: null,
      documentTemplateId: null,
      confidenceRange: { min: 0, max: 0.3 },
      deadline: null,
      urgency: "low",
      requiredImportantPoints: ["not official", "advertisement"],
      requiredNextSteps: ["do not treat as city notice", "confirm sender"],
    },
  },
  {
    id: "ai-case-021",
    name: "Ambiguous topic with city hall and payment wording",
    category: "Ambiguous topic classification",
    inputJapanese:
      "見本市から支払いに関する通知が届きました。保険、税金、年金のどれかは文面からはっきり分かりません。納期限の欄も読めません。",
    expected: {
      documentTypeContains: ["Official Payment", "City Hall", "Unknown"],
      topicId: "official-payment-notices",
      documentTemplateId: null,
      confidenceRange: { min: 0.4, max: 0.65 },
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["payment", "unclear purpose", "deadline not clear"],
      requiredNextSteps: ["confirm sender", "contact issuing organization"],
    },
  },
  {
    id: "ai-case-022",
    name: "Conflicting keywords across tax and pension",
    category: "Conflicting keyword classification",
    inputJapanese:
      "この案内には住民税と国民年金という言葉がありますが、どちらの支払い通知なのか分かりません。詳しい金額や期限は見えません。",
    expected: {
      documentTypeContains: ["Unknown", "Official Payment"],
      topicId: "official-payment-notices",
      documentTemplateId: null,
      confidenceRange: { min: 0.35, max: 0.65 },
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["conflicting keywords", "unclear payment type"],
      requiredNextSteps: ["confirm with issuer", "avoid guessing"],
    },
  },
  {
    id: "ai-case-023",
    name: "No known topic",
    category: "AI fallback",
    inputJapanese:
      "地域イベントのお知らせです。外国人交流会を開催します。参加したい方は会場に来てください。行政手続きや支払いの案内ではありません。",
    expected: {
      documentTypeContains: ["Unknown", "Information"],
      topicId: null,
      documentTemplateId: null,
      confidenceRange: { min: 0, max: 0.3 },
      deadline: null,
      urgency: "low",
      requiredImportantPoints: ["event information", "not a procedure"],
      requiredNextSteps: ["confirm event details", "check sender"],
    },
  },
  {
    id: "ai-case-024",
    name: "Low-confidence classification from damaged notice",
    category: "Low-confidence classification",
    inputJapanese:
      "通知書の一部です。国...保... とだけ読めます。支払い、住所、学校のどれに関係するか分かりません。期限も見えません。",
    expected: {
      documentTypeContains: ["Unknown"],
      topicId: null,
      documentTemplateId: null,
      confidenceRange: { min: 0, max: 0.3 },
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["damaged text", "unclear topic", "no deadline"],
      requiredNextSteps: ["provide clearer text", "confirm with sender"],
    },
  },
  {
    id: "ai-case-025",
    name: "Known address document with clear deadline",
    category: "Known template with clear deadline",
    inputJapanese:
      "転入届の確認通知です。2026年11月2日までに必要書類を持参し、見本市役所の窓口で確認してください。",
    expected: {
      documentTypeContains: ["Address", "Registration"],
      topicId: "address-registration-moving",
      documentTemplateId: "address-registration-moving-notice",
      confidenceRange: { min: 0.8, max: 1 },
      deadline: "2026-11-02",
      urgency: "important",
      requiredImportantPoints: ["address registration", "deadline", "required documents"],
      requiredNextSteps: ["visit city office", "bring documents"],
    },
  },
  {
    id: "ai-case-026",
    name: "Known school document with no deadline",
    category: "Known template with no deadline",
    inputJapanese:
      "学生課からの案内です。学生証の再発行手続きについて説明しています。この案内には締切日は記載されていません。",
    expected: {
      documentTypeContains: ["School", "Administrative"],
      topicId: "school-administrative-notices",
      documentTemplateId: "school-administrative-payment-notice",
      confidenceRange: { min: 0.75, max: 1 },
      deadline: null,
      urgency: "important",
      requiredImportantPoints: ["student office", "no deadline"],
      requiredNextSteps: ["confirm with student office", "check required items"],
    },
  },
];
