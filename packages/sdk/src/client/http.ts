export interface HttpConfig {
  params?: Record<string, unknown>;
  headers?: Record<string, string>;
}

export interface HttpClient {
  get<T>(url: string, config?: HttpConfig): Promise<T>;
  post<T>(url: string, body?: unknown, config?: HttpConfig): Promise<T>;
  put<T>(url: string, body?: unknown, config?: HttpConfig): Promise<T>;
  patch<T>(url: string, body?: unknown, config?: HttpConfig): Promise<T>;
  delete<T>(url: string, config?: HttpConfig): Promise<T>;
}
