export type InlineToken =
  | { kind: 'text'; text: string }
  | { kind: 'citation'; text: string; sourceId: string }
  | { kind: 'evidence'; text: string; sourceChunkId: string }
  | { kind: 'code'; text: string }
  | { kind: 'tag'; text: string };

const citationPattern = /\[(\d+)\]/g;

export function tokenizeRichInline(input: string): InlineToken[] {
  if (!input) {
    return [];
  }

  const tokens: InlineToken[] = [];
  let last = 0;
  let match: RegExpExecArray | null = citationPattern.exec(input);

  while (match) {
    if (match.index > last) {
      tokens.push({ kind: 'text', text: input.slice(last, match.index) });
    }
    tokens.push({
      kind: 'citation',
      text: match[0],
      sourceId: `citation-${match[1]}`,
    });
    last = match.index + match[0].length;
    match = citationPattern.exec(input);
  }

  if (last < input.length) {
    tokens.push({ kind: 'text', text: input.slice(last) });
  }

  return tokens;
}

export function tokenizeEvidenceInline(input: {
  paperId: string;
  pageNum?: number | null;
  sectionPath?: string | null;
}): InlineToken[] {
  const tokens: InlineToken[] = [
    { kind: 'tag', text: input.paperId },
  ];

  if (input.pageNum) {
    tokens.push({ kind: 'text', text: ` p.${input.pageNum}` });
  }

  if (input.sectionPath) {
    tokens.push({
      kind: 'evidence',
      text: ` ${input.sectionPath}`,
      sourceChunkId: input.sectionPath,
    });
  }

  return tokens;
}
