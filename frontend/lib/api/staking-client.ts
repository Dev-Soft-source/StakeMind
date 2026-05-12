import { apiRequest } from "@/lib/api/client";
import type {
  BuildStakingTransactionInput,
  PaginatedStakingTransactions,
  StakingTransaction,
} from "@/lib/api/staking";

type WalletOptions = {
  walletAddress?: string;
  idempotencyKey?: string;
};

function walletHeaders(walletAddress?: string): HeadersInit | undefined {
  if (!walletAddress) {
    return undefined;
  }
  return { "X-Wallet-Address": walletAddress };
}

export function buildStakingTransaction(
  payload: BuildStakingTransactionInput,
  options?: WalletOptions,
) {
  return apiRequest<StakingTransaction>("/api/v1/staking/transactions/build", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...walletHeaders(options?.walletAddress ?? payload.wallet_address),
    },
    body: JSON.stringify(payload),
  });
}

export function simulateStakingTransaction(transactionId: string) {
  return apiRequest<StakingTransaction>(
    `/api/v1/staking/transactions/${encodeURIComponent(transactionId)}/simulate`,
    { method: "POST" },
  );
}

export function submitStakingTransaction(
  transactionId: string,
  payload: { tx_hash: string; signed_extrinsic?: string },
  options: WalletOptions & { idempotencyKey: string },
) {
  return apiRequest<StakingTransaction>(
    `/api/v1/staking/transactions/${encodeURIComponent(transactionId)}/submit`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": options.idempotencyKey,
        ...walletHeaders(options.walletAddress),
      },
      body: JSON.stringify(payload),
    },
  );
}

export function fetchStakingTransaction(transactionId: string, options?: WalletOptions) {
  return apiRequest<StakingTransaction>(
    `/api/v1/staking/transactions/${encodeURIComponent(transactionId)}`,
    { headers: walletHeaders(options?.walletAddress) },
  );
}

export function fetchWalletTransactions(
  walletAddress: string,
  page = 1,
  options?: WalletOptions,
) {
  return apiRequest<PaginatedStakingTransactions>(
    `/api/v1/wallets/${encodeURIComponent(walletAddress)}/transactions?page=${page}`,
    { headers: walletHeaders(options?.walletAddress ?? walletAddress) },
  );
}
