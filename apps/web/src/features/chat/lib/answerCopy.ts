const ABSTAIN_MESSAGE_PATTERNS = [
  /^insufficient evidence to answer confidently\.?$/i,
  /^cannot answer confidently based on the available evidence\.?$/i,
  /^insufficient evidence\.?$/i,
];

const ERROR_STATE_LABELS = {
  abstain: {
    zh: '当前证据不足，已转为谨慎拒答。',
    en: 'Evidence is currently insufficient, so the answer was withheld.',
  },
  insufficient_evidence: {
    zh: '当前证据不足，已转为谨慎拒答。',
    en: 'Evidence is currently insufficient, so the answer was withheld.',
  },
  fallback_used: {
    zh: '已启用回退检索路径，请结合证据面板审阅回答。',
    en: 'Fallback retrieval was used. Review the evidence panel before relying on this answer.',
  },
  search_evidence_unavailable: {
    zh: '证据检索暂时不可用，本次未给出可验证回答。',
    en: 'Evidence retrieval is temporarily unavailable, so no verifiable answer was returned.',
  },
} satisfies Record<string, { zh: string; en: string }>;

function localeKey(isZh: boolean): 'zh' | 'en' {
  return isZh ? 'zh' : 'en';
}

export function normalizeAnswerDisplayCopy(content: string | null | undefined, answerMode: string | null | undefined, isZh: boolean): string {
  const raw = content?.trim();
  if (!raw) {
    return '';
  }

  const isAbstain = answerMode === 'abstain';
  const matchedAbstainCopy = ABSTAIN_MESSAGE_PATTERNS.some((pattern) => pattern.test(raw));
  if (isAbstain && matchedAbstainCopy) {
    return isZh ? '当前证据不足以给出可靠回答。' : 'The available evidence is not sufficient for a reliable answer.';
  }

  return content ?? '';
}

export function normalizeAnswerClaimCopy(claim: string | null | undefined, answerMode: string | null | undefined, isZh: boolean): string {
  const raw = claim?.trim();
  if (!raw) {
    return '';
  }

  return normalizeAnswerDisplayCopy(raw, answerMode, isZh);
}

export function resolveAnswerErrorStateLabel(errorState: string | null | undefined, isZh: boolean): string | null {
  if (!errorState) {
    return null;
  }

  const normalized = errorState.trim().toLowerCase();
  const label = ERROR_STATE_LABELS[normalized as keyof typeof ERROR_STATE_LABELS];
  if (!label) {
    return null;
  }

  return label[localeKey(isZh)];
}
