export interface ImportBenchmarkCase {
  id: string;
  title: string;
  input: { sourceType: 'pdf_url' | 'arxiv' };
  expected: { supportsCancel: boolean; expectsRefresh: boolean };
}

export const importFlowCases: ImportBenchmarkCase[] = [
  {
    id: 'import.flow',
    title: 'Import to completed and refresh',
    input: { sourceType: 'pdf_url' },
    expected: { supportsCancel: true, expectsRefresh: true },
  },
  {
    id: 'import.cancel',
    title: 'Import cancel flow',
    input: { sourceType: 'pdf_url' },
    expected: { supportsCancel: true, expectsRefresh: false },
  },
];
