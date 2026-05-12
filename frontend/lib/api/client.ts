import { getPublicApiBaseUrl, getServerApiBaseUrl } from "@/lib/env";
import type { ApiErrorResponse } from "@/lib/api/types";

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: ApiErrorResponse["error"]["details"];

  constructor(status: number, code: string, message: string, details?: ApiErrorResponse["error"]["details"]) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type ApiRequestOptions = RequestInit & {
  server?: boolean;
};

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { server = false, ...init } = options;
  const baseUrl = server ? getServerApiBaseUrl() : getPublicApiBaseUrl();

  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ApiErrorResponse | null;
    throw new ApiClientError(
      response.status,
      payload?.error.code ?? "unknown_error",
      payload?.error.message ?? response.statusText,
      payload?.error.details,
    );
  }

  return (await response.json()) as T;
}
