import type { EvidenceBlockDto } from '@scholar-ai/types';

export interface ReadingCardSlot {
  title: string;
  content?: string | null;
  evidence_blocks: EvidenceBlockDto[];
}

export interface ReadingCardEvidenceItem {
  label: string;
  content: string;
  evidence_blocks: EvidenceBlockDto[];
}

export interface ReadingCardDoc {
  research_question: ReadingCardSlot;
  method: ReadingCardSlot;
  experiment: ReadingCardSlot;
  result: ReadingCardSlot;
  conclusion: ReadingCardSlot;
  limitation: ReadingCardSlot;
  key_evidence: ReadingCardEvidenceItem[];
}
