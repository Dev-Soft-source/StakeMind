import { apiRequest } from "@/lib/api/client";
import { getPublicApiBaseUrl } from "@/lib/env";
import type {
  InAppNotification,
  OptimizationHintsResponse,
  PriorityRefreshResponse,
  RedeemInviteResponse,
  WalletEntitlement,
} from "@/lib/api/premium";

function walletHeaders(walletAddress: string): HeadersInit {
  return { "X-Wallet-Address": walletAddress };
}

export function fetchWalletEntitlements(walletAddress: string) {
  return apiRequest<WalletEntitlement>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/entitlements`,
    { headers: walletHeaders(walletAddress) },
  );
}

export function redeemPremiumInvite(walletAddress: string, code: string) {
  return apiRequest<RedeemInviteResponse>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/entitlements/redeem-invite`,
    {
      method: "POST",
      headers: { ...walletHeaders(walletAddress), "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    },
  );
}

export function fetchPremiumOptimizationHints(walletAddress: string) {
  return apiRequest<OptimizationHintsResponse>(
    `/api/v1/premium/wallets/${encodeURIComponent(walletAddress)}/optimization-hints`,
    { headers: walletHeaders(walletAddress) },
  );
}

export function fetchPremiumNotifications(walletAddress: string) {
  return apiRequest<InAppNotification[]>(
    `/api/v1/premium/wallets/${encodeURIComponent(walletAddress)}/notifications`,
    { headers: walletHeaders(walletAddress) },
  );
}

export function postPremiumPriorityRefresh(walletAddress: string) {
  return apiRequest<PriorityRefreshResponse>(
    `/api/v1/premium/wallets/${encodeURIComponent(walletAddress)}/priority-refresh`,
    { method: "POST", headers: walletHeaders(walletAddress) },
  );
}

export async function downloadPremiumPortfolioCsv(walletAddress: string): Promise<void> {
  const baseUrl = getPublicApiBaseUrl();
  const response = await fetch(
    `${baseUrl}/api/v1/premium/wallets/${encodeURIComponent(walletAddress)}/export/portfolio.csv`,
    { headers: walletHeaders(walletAddress), cache: "no-store" },
  );
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Export failed (${response.status})`);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `stakemind-portfolio-${walletAddress.slice(0, 12)}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}
