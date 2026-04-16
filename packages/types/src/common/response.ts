import type { ListMeta } from './pagination';
import type { ApiFailure } from './errors';

export interface ApiSuccess<T> {
  success: true;
  data: T;
  meta?: ListMeta;
}

export type ApiResult<T> = ApiSuccess<T> | ApiFailure;
