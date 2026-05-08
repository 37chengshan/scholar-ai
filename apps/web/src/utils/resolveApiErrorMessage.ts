interface ApiErrorResponseData {
  detail?: string | { detail?: string };
  error?: { detail?: string };
  message?: string;
}

const GENERIC_TRANSPORT_MESSAGES = new Set([
  'Network Error',
  'Failed to fetch',
  'Load failed',
  'Auth bootstrap unavailable',
]);

function extractResponseDetail(data: ApiErrorResponseData | undefined): string | null {
  if (!data || typeof data !== 'object') {
    return null;
  }

  if (typeof data.detail === 'string' && data.detail.trim()) {
    return data.detail.trim();
  }

  if (typeof data.detail === 'object' && typeof data.detail?.detail === 'string' && data.detail.detail.trim()) {
    return data.detail.detail.trim();
  }

  if (typeof data.error?.detail === 'string' && data.error.detail.trim()) {
    return data.error.detail.trim();
  }

  if (typeof data.message === 'string' && data.message.trim()) {
    return data.message.trim();
  }

  return null;
}

function getResponse(error: unknown): { status?: number; data?: ApiErrorResponseData } | null {
  if (typeof error !== 'object' || error === null) {
    return null;
  }

  return (error as { response?: { status?: number; data?: ApiErrorResponseData } }).response ?? null;
}

export function isTransportLevelApiFailure(error: unknown): boolean {
  return getResponse(error) === null;
}

export function resolveApiErrorMessage(error: unknown, fallbackMessage: string): string {
  const response = getResponse(error);
  const responseDetail = extractResponseDetail(response?.data);

  if (responseDetail) {
    return responseDetail;
  }

  if (!response) {
    return fallbackMessage;
  }

  if (response.status && response.status >= 500) {
    return fallbackMessage;
  }

  if (typeof error === 'object' && error !== null) {
    const message = (error as { message?: string }).message?.trim();

    if (!message) {
      return fallbackMessage;
    }

    if (message.startsWith('Request failed with status code') || GENERIC_TRANSPORT_MESSAGES.has(message)) {
      return fallbackMessage;
    }

    return message;
  }

  return fallbackMessage;
}