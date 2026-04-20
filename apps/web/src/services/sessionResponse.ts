export interface SessionMessagesEnvelope<T = unknown> {
  data?: {
    messages?: T[];
  };
  messages?: T[];
}

export function extractSessionMessages<T>(response: SessionMessagesEnvelope<T>): T[] {
  if (Array.isArray(response?.data?.messages)) {
    return response.data.messages;
  }

  if (Array.isArray(response?.messages)) {
    return response.messages;
  }

  return [];
}