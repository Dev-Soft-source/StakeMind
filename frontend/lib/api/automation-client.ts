import { apiRequest } from "@/lib/api/client";
import type { AutomationIncident, AutomationJob, AutomationPolicy } from "@/lib/api/automation";

function walletHeaders(walletAddress: string): HeadersInit {
  return { "X-Wallet-Address": walletAddress };
}

export function fetchAutomationPolicy(walletAddress: string) {
  return apiRequest<AutomationPolicy>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/automation/policy`,
    { headers: walletHeaders(walletAddress) },
  );
}

export function putAutomationPolicy(
  walletAddress: string,
  body: Partial<{
    opt_in: boolean;
    kill_switch_active: boolean;
    max_amount_rao_per_action: number;
    max_daily_jobs: number;
    allowed_validator_hotkeys: string[];
    allowed_subnet_ids: number[];
    compound_threshold_rao: number;
  }>,
) {
  return apiRequest<AutomationPolicy>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/automation/policy`,
    {
      method: "PUT",
      headers: { ...walletHeaders(walletAddress), "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

export function postKillSwitch(walletAddress: string, active: boolean) {
  return apiRequest<AutomationPolicy>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/automation/kill-switch`,
    {
      method: "POST",
      headers: { ...walletHeaders(walletAddress), "Content-Type": "application/json" },
      body: JSON.stringify({ active }),
    },
  );
}

export function enqueueAutomationJob(
  walletAddress: string,
  jobType: string,
  payload: Record<string, unknown> = {},
) {
  return apiRequest<AutomationJob>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/automation/jobs`,
    {
      method: "POST",
      headers: { ...walletHeaders(walletAddress), "Content-Type": "application/json" },
      body: JSON.stringify({ job_type: jobType, payload }),
    },
  );
}

export function fetchAutomationJobs(walletAddress: string, status?: string) {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<AutomationJob[]>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/automation/jobs${q}`,
    { headers: walletHeaders(walletAddress) },
  );
}

export function fetchAutomationIncidents(walletAddress: string) {
  return apiRequest<AutomationIncident[]>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/automation/incidents`,
    { headers: walletHeaders(walletAddress) },
  );
}
