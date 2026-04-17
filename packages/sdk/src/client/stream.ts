export interface StreamHandlers {
  onMessage: (event: MessageEvent) => void;
  onError: (error: Error) => void;
  onDone?: (payload?: unknown) => void;
}

export interface StreamConnection {
  connect: (url: string, handlers: StreamHandlers, body?: Record<string, unknown>) => void;
  disconnect: () => void;
}
