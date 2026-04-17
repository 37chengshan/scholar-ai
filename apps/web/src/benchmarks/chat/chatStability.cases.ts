export interface ChatBenchmarkCase {
  id: string;
  title: string;
  input: { query: string };
  expected: { requiresStreaming: boolean; supportsCancel: boolean };
}

export const chatStabilityCases: ChatBenchmarkCase[] = [
  {
    id: 'chat.simple',
    title: 'Single round response',
    input: { query: 'summarize this paper' },
    expected: { requiresStreaming: true, supportsCancel: true },
  },
  {
    id: 'chat.confirmation',
    title: 'Confirmation required flow',
    input: { query: 'delete index' },
    expected: { requiresStreaming: true, supportsCancel: true },
  },
];
