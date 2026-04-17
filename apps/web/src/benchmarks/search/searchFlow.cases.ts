export interface SearchBenchmarkCase {
  id: string;
  title: string;
  input: { query: string; page?: number };
  expected: { paginationStable: boolean };
}

export const searchFlowCases: SearchBenchmarkCase[] = [
  {
    id: 'search.empty',
    title: 'Empty result search',
    input: { query: 'zzzz-no-result' },
    expected: { paginationStable: true },
  },
  {
    id: 'search.paginated',
    title: 'Paginated search',
    input: { query: 'rag', page: 2 },
    expected: { paginationStable: true },
  },
];
