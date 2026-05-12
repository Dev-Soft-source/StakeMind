import { apiRequest } from "@/lib/api/client";
import type { HealthResponse } from "@/lib/api/types";

export function fetchHealth(options?: { server?: boolean }) {
  return apiRequest<HealthResponse>("/api/v1/health", { server: options?.server });
}
