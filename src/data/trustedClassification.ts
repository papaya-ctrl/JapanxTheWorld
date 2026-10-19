import type {
  DocumentTemplate,
  TopicClassificationResult,
  TrustedTopic,
} from "../types";
import { documentTemplates } from "./documentTemplates";
import { trustedTopics } from "./trustedTopics";

export const TRUSTED_CONFIDENCE_THRESHOLD = 0.68;

type MatchSignal = {
  term: string;
  weight: number;
  kind: "alias" | "keyword" | "template" | "strong-template";
};

type ScoredTopic = {
  topic: TrustedTopic;
  rawScore: number;
  confidence: number;
  hasSpecificEvidence: boolean;
  matchedAliases: string[];
  matchedKeywords: string[];
};

type ScoredTemplate = {
  template: DocumentTemplate;
  rawScore: number;
  confidence: number;
  strongMatches: string[];
  ordinaryMatches: string[];
};

const BROAD_TERMS = new Set([
  "住所",
  "市役所",
  "区役所",
  "在留カード",
  "保険料",
  "納付",
  "納期限",
  "納付書",
  "年金",
  "免除",
  "猶予",
  "在留資格",
  "追加資料",
  "提出期限",
  "許可",
  "卒業",
  "就職",
  "内定",
  "就労",
  "留学",
  "学生",
  "雇用",
  "アルバイト",
  "勤務",
  "シフト",
  "賃金",
  "勤務時間",
  "休日",
  "学校",
  "申請",
  "通知",
  "案内",
  "手続き",
  "窓口",
  "支払い",
  "請求",
  "payment notice",
  "administrative notice",
  "work permission",
  "work status",
  "moving",
  "insurance notice",
  "tax notice",
]);

const DOCUMENT_MARKERS = [
  "通知",
  "通知書",
  "お知らせ",
  "案内",
  "納付書",
  "申請書",
  "契約書",
  "はがき",
  "届",
  "notice",
  "letter",
  "document",
  "form",
  "payment slip",
];

const NEGATION_MARKERS = [
  "ではありません",
  "ではない",
  "と異なります",
  "not a",
  "not an",
  "not about",
  "unrelated to",
];

const AMBIGUITY_MARKERS = [
  "どちら",
  "不明",
  "分かりません",
  "わかりません",
  "はっきりしません",
  "unclear which",
  "cannot tell which",
];

export const normalizeClassificationText = (input: string) =>
  input
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[\u3000\t\r\n]+/g, " ")
    .replace(/[、。・「」『』（）()［］\[\]【】,:;!?！？]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const compactJapaneseWhitespace = (value: string) =>
  value.replace(/(?<=[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}])\s+(?=[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}])/gu, "");

const hasLatinCharacters = (value: string) => /[a-z]/i.test(value);

const findTermIndex = (normalizedText: string, rawTerm: string) => {
  const term = normalizeClassificationText(rawTerm);
  const text = compactJapaneseWhitespace(normalizedText);
  const compactTerm = compactJapaneseWhitespace(term);

  if (hasLatinCharacters(compactTerm)) {
    const escaped = compactTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return text.search(new RegExp(`(?:^|[^a-z0-9])${escaped}(?:$|[^a-z0-9])`, "i"));
  }

  return text.indexOf(compactTerm);
};

const isNegatedMatch = (normalizedText: string, rawTerm: string) => {
  const term = normalizeClassificationText(rawTerm);
  const index = findTermIndex(normalizedText, term);
  if (index < 0) {
    return false;
  }

  const localContext = compactJapaneseWhitespace(normalizedText).slice(
    Math.max(0, index - 12),
    index + compactJapaneseWhitespace(term).length + 24,
  );
  return NEGATION_MARKERS.some((marker) => localContext.includes(marker));
};

const hasTerm = (normalizedText: string, term: string) =>
  findTermIndex(normalizedText, term) >= 0 && !isNegatedMatch(normalizedText, term);

const keepIndependentSignals = (signals: MatchSignal[]) => {
  const bestByTerm = new Map<string, MatchSignal>();

  for (const signal of signals) {
    const term = normalizeClassificationText(signal.term);
    const previous = bestByTerm.get(term);
    if (!previous || signal.weight > previous.weight) {
      bestByTerm.set(term, { ...signal, term });
    }
  }

  return [...bestByTerm.values()].filter((signal, _, all) => {
    return !all.some(
      (other) =>
        other.term !== signal.term &&
        other.term.includes(signal.term) &&
        other.weight >= signal.weight,
    );
  });
};

const scoreToConfidence = (score: number) => {
  if (score <= 0) return 0;
  if (score === 1) return 0.18;
  if (score === 2) return 0.32;
  if (score === 3) return 0.45;
  if (score === 4) return 0.58;
  if (score === 5) return 0.7;
  if (score === 6) return 0.76;
  if (score === 7) return 0.8;
  if (score === 8) return 0.84;
  if (score === 9) return 0.87;
  return Math.min(0.98, 0.89 + (score - 10) * 0.015);
};

const scoreTopic = (normalizedText: string, topic: TrustedTopic): ScoredTopic => {
  const signals: MatchSignal[] = [];

  for (const alias of topic.aliases) {
    if (hasTerm(normalizedText, alias)) {
      signals.push({
        term: alias,
        weight: BROAD_TERMS.has(normalizeClassificationText(alias)) ? 2 : 5,
        kind: "alias",
      });
    }
  }

  for (const keyword of topic.keywords) {
    if (hasTerm(normalizedText, keyword)) {
      signals.push({
        term: keyword,
        weight: BROAD_TERMS.has(normalizeClassificationText(keyword)) ? 1 : 2,
        kind: "keyword",
      });
    }
  }

  const independentSignals = keepIndependentSignals(signals);
  const rawScore = independentSignals.reduce((total, signal) => total + signal.weight, 0);

  return {
    topic,
    rawScore,
    confidence: scoreToConfidence(rawScore),
    hasSpecificEvidence: independentSignals.some((signal) => signal.weight >= 5),
    matchedAliases: independentSignals
      .filter((signal) => signal.kind === "alias")
      .map((signal) => signal.term),
    matchedKeywords: independentSignals
      .filter((signal) => signal.kind === "keyword")
      .map((signal) => signal.term),
  };
};

const scoreTemplate = (
  normalizedText: string,
  template: DocumentTemplate,
): ScoredTemplate => {
  const signals: MatchSignal[] = [];

  for (const phrase of template.strongMatchKeywords) {
    if (hasTerm(normalizedText, phrase)) {
      signals.push({ term: phrase, weight: 8, kind: "strong-template" });
    }
  }

  for (const keyword of template.matchKeywords) {
    if (hasTerm(normalizedText, keyword)) {
      signals.push({
        term: keyword,
        weight: BROAD_TERMS.has(normalizeClassificationText(keyword)) ? 1 : 3,
        kind: "template",
      });
    }
  }

  const independentSignals = keepIndependentSignals(signals);
  const rawScore = independentSignals.reduce((total, signal) => total + signal.weight, 0);

  return {
    template,
    rawScore,
    confidence: scoreToConfidence(rawScore),
    strongMatches: independentSignals
      .filter((signal) => signal.kind === "strong-template")
      .map((signal) => signal.term),
    ordinaryMatches: independentSignals
      .filter((signal) => signal.kind === "template")
      .map((signal) => signal.term),
  };
};

const hasDocumentMarker = (normalizedText: string) =>
  DOCUMENT_MARKERS.some((marker) => hasTerm(normalizedText, marker));

const isAmbiguous = (first?: ScoredTopic, second?: ScoredTopic) => {
  if (
    !first ||
    !second ||
    !first.hasSpecificEvidence ||
    !second.hasSpecificEvidence ||
    second.rawScore < 5
  ) {
    return false;
  }

  return first.rawScore - second.rawScore < 3 || second.rawScore / first.rawScore >= 0.72;
};

export const classifyTrustedInput = (input: string): TopicClassificationResult => {
  const normalizedText = normalizeClassificationText(input);
  if (normalizedText.length < 2) {
    return {
      topicId: null,
      documentTemplateId: null,
      confidence: 0,
      reason: "Input is empty or too short to classify safely.",
      candidateScores: [],
    };
  }

  const topicScores = trustedTopics
    .map((topic) => scoreTopic(normalizedText, topic))
    .filter((candidate) => candidate.rawScore > 0)
    .sort((a, b) => b.rawScore - a.rawScore || a.topic.id.localeCompare(b.topic.id));
  let bestTopic: ScoredTopic | undefined = topicScores[0];
  let secondTopic: ScoredTopic | undefined = topicScores[1];

  const templateScores = documentTemplates
    .map((template) => scoreTemplate(normalizedText, template))
    .filter((candidate) => candidate.rawScore > 0)
    .sort((a, b) => b.rawScore - a.rawScore || a.template.id.localeCompare(b.template.id));

  const [topTemplate, secondTemplate] = templateScores;
  const decisiveTemplate = Boolean(
    topTemplate &&
      topTemplate.strongMatches.length > 0 &&
      topTemplate.rawScore >= 8 &&
      !AMBIGUITY_MARKERS.some((marker) => normalizedText.includes(marker)) &&
      (!secondTemplate || topTemplate.rawScore - secondTemplate.rawScore >= 3),
  );
  if (decisiveTemplate && topTemplate) {
    const templateTopic = topicScores.find(
      (candidate) => candidate.topic.id === topTemplate.template.relatedTopicId,
    );
    if (templateTopic?.hasSpecificEvidence) {
      bestTopic = templateTopic;
      secondTopic = topicScores.find((candidate) => candidate.topic.id !== templateTopic.topic.id);
    }
  }

  const ambiguous = !decisiveTemplate && isAmbiguous(bestTopic, secondTopic);
  if (
    !bestTopic ||
    !bestTopic.hasSpecificEvidence ||
    bestTopic.confidence < TRUSTED_CONFIDENCE_THRESHOLD ||
    ambiguous
  ) {
    const confidence = bestTopic
      ? Math.min(bestTopic.confidence, ambiguous ? 0.59 : TRUSTED_CONFIDENCE_THRESHOLD - 0.01)
      : 0;
    return {
      topicId: null,
      documentTemplateId: null,
      confidence,
      reason: ambiguous
        ? `Ambiguous evidence between ${bestTopic?.topic.id ?? "unknown"} and ${secondTopic?.topic.id ?? "unknown"}.`
        : "No topic had enough specific, independent evidence for trusted routing.",
      matchedAliases: bestTopic?.matchedAliases ?? [],
      matchedKeywords: bestTopic?.matchedKeywords ?? [],
      candidateScores: topicScores.slice(0, 4).map((candidate) => ({
        topicId: candidate.topic.id,
        score: candidate.rawScore,
      })),
    };
  }

  const bestRelatedTemplate = templateScores.find(
    (candidate) => candidate.template.relatedTopicId === bestTopic.topic.id,
  );
  const templateHasEnoughEvidence = Boolean(
    bestRelatedTemplate &&
      bestRelatedTemplate.confidence >= TRUSTED_CONFIDENCE_THRESHOLD &&
      (bestRelatedTemplate.strongMatches.length > 0 || hasDocumentMarker(normalizedText)),
  );

  return {
    topicId: bestTopic.topic.id,
    documentTemplateId: templateHasEnoughEvidence
      ? bestRelatedTemplate?.template.id ?? null
      : null,
    confidence: bestTopic.confidence,
    reason: templateHasEnoughEvidence
      ? "Specific topic evidence and document-template evidence passed the trusted threshold."
      : "Specific topic evidence passed the trusted threshold, but no precise document template was proven.",
    matchedAliases: bestTopic.matchedAliases,
    matchedKeywords: bestTopic.matchedKeywords,
    candidateScores: topicScores.slice(0, 4).map((candidate) => ({
      topicId: candidate.topic.id,
      score: candidate.rawScore,
    })),
  };
};

const validDate = (year: number, month: number, day: number) => {
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
};

const formatDate = (year: number, month: number, day: number) =>
  validDate(year, month, day)
    ? `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`
    : null;

const DEADLINE_CONTEXT = "(?:納期限|支払期限|提出期限|申請期限|締切(?:日)?|期限|due date|deadline|by|until)";
const ACTION_CONTEXT = "(?:までに|まで|が期限|です|:|：)";

export const extractExplicitDeadline = (input: string): string | null => {
  const text = input.normalize("NFKC");
  const gregorianPatterns = [
    new RegExp(`${DEADLINE_CONTEXT}[^\\d令]{0,20}(20\\d{2})[年\\-/.](\\d{1,2})[月\\-/.](\\d{1,2})日?`, "i"),
    new RegExp(`(20\\d{2})[年\\-/.](\\d{1,2})[月\\-/.](\\d{1,2})日?[^。\\n]{0,16}${ACTION_CONTEXT}`, "i"),
  ];

  for (const pattern of gregorianPatterns) {
    const match = text.match(pattern);
    if (match) {
      return formatDate(Number(match[1]), Number(match[2]), Number(match[3]));
    }
  }

  const reiwaPatterns = [
    new RegExp(`${DEADLINE_CONTEXT}[^令\\d]{0,20}令和(\\d{1,2})年(\\d{1,2})月(\\d{1,2})日`),
    new RegExp(`令和(\\d{1,2})年(\\d{1,2})月(\\d{1,2})日[^。\\n]{0,16}${ACTION_CONTEXT}`),
  ];

  for (const pattern of reiwaPatterns) {
    const match = text.match(pattern);
    if (match) {
      const reiwaYear = Number(match[1]);
      if (reiwaYear < 1) {
        return null;
      }
      return formatDate(2018 + reiwaYear, Number(match[2]), Number(match[3]));
    }
  }

  return null;
};
