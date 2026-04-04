import axios, { AxiosInstance, AxiosError } from 'axios';
import axiosRetry from 'axios-retry';
import { logger } from './logger';
import { v4 as uuidv4 } from 'uuid';

export interface HttpClientConfig {
  baseURL: string;
  timeout?: number;
}

export class HttpClient {
  private client: AxiosInstance;

  constructor(config: HttpClientConfig) {
    this.client = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout || 30000, // 30 second default
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Configure exponential backoff retry (per D-05)
    axiosRetry(this.client, {
      retries: 3,
      retryDelay: (retryCount) => {
        // Exponential backoff: 1s, 2s, 4s
        const delay = Math.pow(2, retryCount - 1) * 1000;
        logger.warn(`Retrying request (attempt ${retryCount}/3) after ${delay}ms`);
        return delay;
      },
      retryCondition: (error: AxiosError) => {
        // Retry on rate limit, server errors, or connection reset
        const shouldRetry = (
          error.response?.status === 429 ||
          (error.response?.status ?? 0) >= 500 ||
          error.code === 'ECONNRESET' ||
          error.code === 'ETIMEDOUT'
        );
        if (shouldRetry) {
          logger.warn(`Retrying due to: ${error.response?.status || error.code}`);
        }
        return shouldRetry;
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        logger.debug(`HTTP request: ${config.method?.toUpperCase()} ${config.url}`, {
          request_id: uuidv4(),
        });
        return config;
      },
      (error) => {
        logger.error('HTTP request error', { error: error.message });
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        logger.debug(`HTTP response: ${response.status} from ${response.config.url}`);
        return response;
      },
      (error: AxiosError) => {
        if (error.response) {
          logger.error('HTTP response error', {
            status: error.response.status,
            url: error.config?.url,
            data: error.response.data,
          });
        } else if (error.request) {
          logger.error('HTTP no response', {
            url: error.config?.url,
            message: error.message,
          });
        } else {
          logger.error('HTTP error', { message: error.message });
        }
        return Promise.reject(error);
      }
    );
  }

  async post<T>(url: string, data?: unknown): Promise<T> {
    const response = await this.client.post<T>(url, data);
    return response.data;
  }

  async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
    const response = await this.client.get<T>(url, { params });
    return response.data;
  }
}