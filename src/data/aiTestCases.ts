export type AiTestCaseGroup =
  | "strong"
  | "alternative"
  | "short"
  | "no-deadline"
  | "explicit-deadline"
  | "ambiguous"
  | "conflict"
  | "unrelated"
  | "malformed"
  | "format-variation";

export type AiTestCase = {
  id: string;
  name: string;
  group: AiTestCaseGroup;
  inputJapanese: string;
  expectedTopicId: string | null;
  expectedTemplateId: string | null;
  expectTrustedMatch: boolean;
  expectedDeadline: string | null;
  expectedRelatedGuide: string | null;
  forbiddenBehaviors?: string[];
  notes?: string;
};

const trustedCase = (
  id: string,
  name: string,
  group: AiTestCaseGroup,
  inputJapanese: string,
  expectedTopicId: string,
  expectedTemplateId: string | null,
  expectedDeadline: string | null,
  expectedRelatedGuide: string,
): AiTestCase => ({
  id,
  name,
  group,
  inputJapanese,
  expectedTopicId,
  expectedTemplateId,
  expectTrustedMatch: true,
  expectedDeadline,
  expectedRelatedGuide,
});

const rejectedCase = (
  id: string,
  name: string,
  group: AiTestCaseGroup,
  inputJapanese: string,
  notes: string,
): AiTestCase => ({
  id,
  name,
  group,
  inputJapanese,
  expectedTopicId: null,
  expectedTemplateId: null,
  expectTrustedMatch: false,
  expectedDeadline: null,
  expectedRelatedGuide: null,
  forbiddenBehaviors: [
    "must not force a trusted topic",
    "must not invent a document template",
    "must not invent a deadline",
  ],
  notes,
});

export const aiTestCases: AiTestCase[] = [
  // Address Registration / Moving
  trustedCase("v2-addr-01", "Address strong document", "strong", "転入届と住所登録の確認通知です。市役所の窓口に必要書類を持参してください。", "address-registration-moving", "address-registration-moving-notice", null, "moving-address-registration"),
  trustedCase("v2-addr-02", "Address alternative English", "alternative", "I received a moving notice and need to change address at city hall.", "address-registration-moving", "address-registration-moving-notice", null, "moving-address-registration"),
  trustedCase("v2-addr-03", "Address short sufficient", "short", "転出届", "address-registration-moving", "address-registration-moving-notice", null, "moving-address-registration"),
  trustedCase("v2-addr-04", "Address notice without deadline", "no-deadline", "住所変更について質問があります。転居後の市役所手続きを確認したいです。", "address-registration-moving", null, null, "moving-address-registration"),
  trustedCase("v2-addr-05", "Address explicit Reiwa deadline", "explicit-deadline", "転居届の提出期限は令和8年10月12日です。区役所に必要書類を持参してください。", "address-registration-moving", "address-registration-moving-notice", "2026-10-12", "moving-address-registration"),

  // National Health Insurance
  trustedCase("v2-nhi-01", "NHI strong payment notice", "strong", "国民健康保険料納付書です。保険課からのお知らせを確認してください。", "national-health-insurance", "national-health-insurance-notice", null, "health-insurance-payment"),
  trustedCase("v2-nhi-02", "NHI alternative English", "alternative", "National Health Insurance enrollment notice from the municipal insurance desk.", "national-health-insurance", "national-health-insurance-notice", null, "health-insurance-payment"),
  trustedCase("v2-nhi-03", "NHI short sufficient", "short", "国保について確認したいです。", "national-health-insurance", null, null, "health-insurance-payment"),
  trustedCase("v2-nhi-04", "NHI no deadline", "no-deadline", "国民健康保険のお知らせです。加入手続きと保険証について説明しています。", "national-health-insurance", "national-health-insurance-notice", null, "health-insurance-payment"),
  trustedCase("v2-nhi-05", "NHI explicit ISO deadline", "explicit-deadline", "国民健康保険料の納付書です。支払期限は2026-10-31です。", "national-health-insurance", "national-health-insurance-notice", "2026-10-31", "health-insurance-payment"),

  // National Pension
  trustedCase("v2-pension-01", "Pension strong payment notice", "strong", "国民年金保険料の納付書です。日本年金機構から届きました。", "national-pension", "national-pension-notice", null, "national-pension"),
  trustedCase("v2-pension-02", "Pension alternative terminology", "alternative", "学生納付特例と年金保険料の猶予について年金事務所に確認します。", "national-pension", null, null, "national-pension"),
  trustedCase("v2-pension-03", "Pension short sufficient", "short", "国民年金について質問があります。", "national-pension", null, null, "national-pension"),
  trustedCase("v2-pension-04", "Pension no deadline", "no-deadline", "国民年金制度に関する案内です。免除申請について説明していますが期限の記載はありません。", "national-pension", null, null, "national-pension"),
  trustedCase("v2-pension-05", "Pension explicit Reiwa deadline", "explicit-deadline", "国民年金保険料納付書。納期限は令和8年6月30日です。", "national-pension", "national-pension-notice", "2026-06-30", "national-pension"),

  // Residence Tax
  trustedCase("v2-tax-01", "Residence tax strong notice", "strong", "住民税納税通知書です。市民税・県民税の税額を確認してください。", "residence-tax", "residence-tax-notice", null, "residence-tax-payment"),
  trustedCase("v2-tax-02", "Residence tax English alias", "alternative", "I received a resident tax notice showing municipal tax installments.", "residence-tax", "residence-tax-notice", null, "residence-tax-payment"),
  trustedCase("v2-tax-03", "Residence tax short topic", "short", "住民税について質問があります。", "residence-tax", null, null, "residence-tax-payment"),
  trustedCase("v2-tax-04", "Residence tax no deadline", "no-deadline", "市民税と県民税の普通徴収についての案内です。支払日は書かれていません。", "residence-tax", "residence-tax-notice", null, "residence-tax-payment"),
  trustedCase("v2-tax-05", "Residence tax explicit slash deadline", "explicit-deadline", "住民税納税通知書。第1期の納期限は2026/07/31です。", "residence-tax", "residence-tax-notice", "2026-07-31", "residence-tax-payment"),

  // Residence Status Renewal
  trustedCase("v2-renew-01", "Renewal strong notice", "strong", "在留期間更新申請のお知らせです。入国在留管理局で手続きを確認してください。", "residence-status-renewal", "immigration-residence-status-notice", null, "residence-status-renewal"),
  trustedCase("v2-renew-02", "Renewal alternative English", "alternative", "Visa renewal notice: please confirm the period of stay renewal documents with immigration.", "residence-status-renewal", null, null, "residence-status-renewal"),
  trustedCase("v2-renew-03", "Renewal short sufficient", "short", "在留期間更新", "residence-status-renewal", "immigration-residence-status-notice", null, "residence-status-renewal"),
  trustedCase("v2-renew-04", "Renewal no deadline", "no-deadline", "在留資格更新について質問があります。追加資料の期限は書かれていません。", "residence-status-renewal", "immigration-residence-status-notice", null, "residence-status-renewal"),
  trustedCase("v2-renew-05", "Renewal explicit deadline", "explicit-deadline", "在留期間更新申請の追加資料提出期限は2026年9月15日です。", "residence-status-renewal", "immigration-residence-status-notice", "2026-09-15", "residence-status-renewal"),

  // Student to Worker
  trustedCase("v2-transition-01", "Transition strong application", "strong", "留学から就労資格への変更についての通知です。在留資格変更許可申請を確認してください。", "student-to-worker-transition", "student-to-worker-transition-notice", null, "job-hunting-before-graduation"),
  trustedCase("v2-transition-02", "Transition alternative English", "alternative", "Student to work visa after graduation: my employer sent a status change document.", "student-to-worker-transition", "student-to-worker-transition-notice", null, "job-hunting-before-graduation"),
  trustedCase("v2-transition-03", "Transition short sufficient", "short", "留学から就労資格への変更", "student-to-worker-transition", "student-to-worker-transition-notice", null, "job-hunting-before-graduation"),
  trustedCase("v2-transition-04", "Transition no deadline", "no-deadline", "卒業後の就職と在留資格変更について学校に相談します。申請期限はまだ不明です。", "student-to-worker-transition", null, null, "job-hunting-before-graduation"),
  trustedCase("v2-transition-05", "Transition explicit deadline", "explicit-deadline", "留学から就労への在留資格変更許可申請書です。提出期限は2026年12月1日です。", "student-to-worker-transition", "student-to-worker-transition-notice", "2026-12-01", "job-hunting-before-graduation"),

  // Student Part-Time Work Permission
  trustedCase("v2-parttime-01", "Part-time permission strong notice", "strong", "資格外活動許可申請のお知らせです。学生のアルバイト許可を確認してください。", "part-time-work-permission", "part-time-work-permission-notice", null, "part-time-work-permission"),
  trustedCase("v2-parttime-02", "Part-time permission English", "alternative", "Part-time work permission for a student: activity outside status application.", "part-time-work-permission", "part-time-work-permission-notice", null, "part-time-work-permission"),
  trustedCase("v2-parttime-03", "Part-time permission short", "short", "資格外活動許可", "part-time-work-permission", "part-time-work-permission-notice", null, "part-time-work-permission"),
  trustedCase("v2-parttime-04", "Part-time permission no deadline", "no-deadline", "アルバイト許可について学校と入国在留管理局に確認したいです。期限は不明です。", "part-time-work-permission", null, null, "part-time-work-permission"),
  trustedCase("v2-parttime-05", "Part-time permission explicit deadline", "explicit-deadline", "資格外活動許可申請書の提出期限は2026.11.05です。", "part-time-work-permission", "part-time-work-permission-notice", "2026-11-05", "part-time-work-permission"),

  // Employment Contract / Working Conditions
  trustedCase("v2-work-01", "Working conditions strong document", "strong", "労働条件通知書です。契約期間、賃金、勤務時間、休日を確認してください。", "employment-working-conditions", "employment-working-conditions-notice", null, "employment-working-conditions"),
  trustedCase("v2-work-02", "Employment contract English", "alternative", "Employment contract and working conditions notice showing wages and working hours.", "employment-working-conditions", "employment-working-conditions-notice", null, "employment-working-conditions"),
  trustedCase("v2-work-03", "Working conditions short", "short", "雇用契約書", "employment-working-conditions", "employment-working-conditions-notice", null, "employment-working-conditions"),
  trustedCase("v2-work-04", "Working conditions no deadline", "no-deadline", "労働条件について質問があります。賃金と休日は書かれていますが締切はありません。", "employment-working-conditions", null, null, "employment-working-conditions"),
  trustedCase("v2-work-05", "Employment explicit deadline", "explicit-deadline", "雇用契約書の確認期限は2026年10月20日です。勤務時間と賃金を確認してください。", "employment-working-conditions", "employment-working-conditions-notice", "2026-10-20", "employment-working-conditions"),

  // Required negative and confusion cases
  rejectedCase("v2-neg-01", "Ambiguous payment deadline", "ambiguous", "納付期限があります。期限までに支払ってください。", "Generic payment wording has no topic-specific evidence."),
  rejectedCase("v2-neg-02", "Generic important notice", "unrelated", "重要なお知らせです。内容を確認してください。", "Generic notice words must not trigger city-hall or another topic."),
  rejectedCase("v2-neg-03", "School culture festival", "unrelated", "学校の文化祭は来週の日曜日です。参加したい学生は先生に連絡してください。", "School event text is not an official procedure."),
  rejectedCase("v2-neg-04", "Generic insurance question", "ambiguous", "保険について確認してください。", "The word insurance alone does not establish National Health Insurance."),
  rejectedCase("v2-neg-05", "Generic tax question", "ambiguous", "税金について質問があります。", "Generic tax wording does not establish residence tax."),
  rejectedCase("v2-neg-06", "Tax and pension conflict", "conflict", "住民税と国民年金のどちらの納付書か分かりません。期限も読めません。", "Two equally specific payment topics conflict."),
  rejectedCase("v2-neg-07", "Pension and health insurance conflict", "conflict", "国民年金と国民健康保険の保険料について書かれていますが、通知の目的が不明です。", "Two specific social-insurance topics conflict."),
  rejectedCase("v2-neg-08", "Renewal and status-change conflict", "conflict", "在留期間更新と留学から就労への在留資格変更のどちらを申請する通知か不明です。", "Renewal and change-of-status are distinct procedures."),
  rejectedCase("v2-neg-09", "Status-change and part-time conflict", "conflict", "就労資格への変更と資格外活動許可の両方が書かれ、どちらの申請書か分かりません。", "Student work routes conflict and must not be guessed."),
  rejectedCase("v2-neg-10", "General school job fair", "unrelated", "学校の就職説明会を開催します。企業の話を聞きたい学生は参加してください。", "A job fair is not an employment contract or immigration application."),
  rejectedCase("v2-neg-11", "Malformed short fragment", "malformed", "通...知...", "Unreadable fragments have insufficient evidence."),
  rejectedCase("v2-neg-12", "Advertisement with negated NHI", "unrelated", "自転車保険の広告です。国民健康保険の通知ではありません。", "A negated trusted phrase must not count as positive evidence."),

  // Format and bilingual robustness
  trustedCase("v2-format-01", "Tax punctuation variation", "format-variation", "  住民税、納税通知書；市民税！納期限：2026-10-31  ", "residence-tax", "residence-tax-notice", "2026-10-31", "residence-tax-payment"),
  trustedCase("v2-format-02", "Pension mixed language", "format-variation", "National Pension 国民年金 保険料 納付書 due date: 2026/10/31", "national-pension", "national-pension-notice", "2026-10-31", "national-pension"),
];
