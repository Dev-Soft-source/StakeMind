import { apiRequest } from "@/lib/api/client";
import type {
  CompareValidators,
  PaginatedRankings,
  RewardForecast,
  WalletRiskProfile,
} from "@/lib/api/intelligence";

type WalletOptions = {
  walletAddress?: string;
};

function walletHeaders(walletAddress?: string): HeadersInit | undefined {
  if (!walletAddress) {
    return undefined;
  }
  return { "X-Wallet-Address": walletAddress };
}

export function fetchValidatorRankings(params: {
  page?: number;
  page_size?: number;
  subnet_id?: number;
  sort?: "score" | "apy" | "rank";
  direction?: "asc" | "desc";
}) {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  if (params.subnet_id !== undefined) query.set("subnet_id", String(params.subnet_id));
  if (params.sort) query.set("sort", params.sort);
  if (params.direction) query.set("direction", params.direction);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<PaginatedRankings>(`/api/v1/intelligence/validators/rankings${suffix}`);
}

export function fetchWalletRisk(walletAddress: string, options?: WalletOptions) {
  return apiRequest<WalletRiskProfile>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/risk`,
    { headers: walletHeaders(options?.walletAddress ?? walletAddress) },
  );
}

export function fetchRewardForecast(
  walletAddress: string,
  days = 30,
  horizonDays = 14,
  options?: WalletOptions,
) {
  return apiRequest<RewardForecast>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/rewards/forecast?days=${days}&horizon_days=${horizonDays}`,
    { headers: walletHeaders(options?.walletAddress ?? walletAddress) },
  );
}

export function compareValidators(hotkeys: string[], subnetId?: number) {
  const query = new URLSearchParams();
  for (const hotkey of hotkeys) {
    query.append("hotkeys", hotkey);
  }
  if (subnetId !== undefined) {
    query.set("subnet_id", String(subnetId));
  }
  return apiRequest<CompareValidators>(`/api/v1/intelligence/validators/compare?${query.toString()}`);
}
