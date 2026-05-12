import { apiRequest } from "@/lib/api/client";
import type {
  PaginatedValidators,
  RewardHistoryPoint,
  RewardSummary,
  StakingPortfolio,
  Validator,
} from "@/lib/api/dashboard";

type WalletOptions = {
  walletAddress?: string;
};

function walletHeaders(walletAddress?: string): HeadersInit | undefined {
  if (!walletAddress) {
    return undefined;
  }
  return { "X-Wallet-Address": walletAddress };
}

export function fetchValidators(params: {
  page?: number;
  page_size?: number;
  subnet_id?: number;
  search?: string;
  sort?: "score" | "apy" | "hotkey";
  direction?: "asc" | "desc";
}) {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  if (params.subnet_id !== undefined) query.set("subnet_id", String(params.subnet_id));
  if (params.search) query.set("search", params.search);
  if (params.sort) query.set("sort", params.sort);
  if (params.direction) query.set("direction", params.direction);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<PaginatedValidators>(`/api/v1/validators${suffix}`);
}

export function fetchValidator(hotkey: string, subnetId?: number) {
  const suffix = subnetId !== undefined ? `?subnet_id=${subnetId}` : "";
  return apiRequest<Validator>(`/api/v1/validators/${encodeURIComponent(hotkey)}${suffix}`);
}

export function createWalletSession(walletAddress: string) {
  return apiRequest<{ wallet_address: string; expires_at: string }>("/api/v1/wallets/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ wallet_address: walletAddress }),
  });
}

export function syncCatalog() {
  return apiRequest<Record<string, number>>("/api/v1/ingestion/catalog-sync", {
    method: "POST",
  });
}

export function syncPortfolio(walletAddress: string) {
  return apiRequest<Record<string, number | string>>("/api/v1/ingestion/portfolio-sync", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ wallet_address: walletAddress }),
  });
}

export function fetchStakingPortfolio(walletAddress: string, options?: WalletOptions) {
  return apiRequest<StakingPortfolio>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/staking`,
    { headers: walletHeaders(options?.walletAddress ?? walletAddress) },
  );
}

export function fetchRewardSummary(walletAddress: string, options?: WalletOptions) {
  return apiRequest<RewardSummary>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/rewards/summary`,
    { headers: walletHeaders(options?.walletAddress ?? walletAddress) },
  );
}

export function fetchRewardHistory(walletAddress: string, days: number, options?: WalletOptions) {
  return apiRequest<RewardHistoryPoint[]>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/rewards/history?days=${days}`,
    { headers: walletHeaders(options?.walletAddress ?? walletAddress) },
  );
}
