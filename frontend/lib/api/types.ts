export type ApiErrorBody = {
  code: string;
  message: string;
  details?: Record<string, unknown> | unknown[];
};

export type ApiErrorResponse = {
  error: ApiErrorBody;
};

export type HealthChecks = {
  api: string;
  database: string;
  redis: string;
};

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
  checks: HealthChecks;
};

export type PaginationMeta = {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
};

export type PaginatedResponse<T> = {
  data: T[];
  pagination: PaginationMeta;
};
