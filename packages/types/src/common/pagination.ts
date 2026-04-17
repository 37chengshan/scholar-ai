export interface PaginationParams {
  limit?: number;
  offset?: number;
}

export interface ListMeta {
  limit: number;
  offset: number;
  total: number;
}
