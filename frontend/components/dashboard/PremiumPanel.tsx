"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PanelCard } from "@/components/ui/PanelCard";
import { useWallet } from "@/components/wallet/WalletProvider";
import {
  downloadPremiumPortfolioCsv,
  fetchPremiumNotifications,
  fetchPremiumOptimizationHints,
  fetchWalletEntitlements,
  postPremiumPriorityRefresh,
  redeemPremiumInvite,
} from "@/lib/api/premium-client";

export function PremiumPanel() {
  const { walletAddress } = useWallet();
  const queryClient = useQueryClient();
  const [inviteCode, setInviteCode] = useState("");

  const entitlementQuery = useQuery({
    queryKey: ["wallet-entitlements", walletAddress],
    queryFn: () => fetchWalletEntitlements(walletAddress!),
    enabled: Boolean(walletAddress),
  });

  const isPremium = entitlementQuery.data?.plan === "premium";

  const hintsQuery = useQuery({
    queryKey: ["premium-optimization-hints", walletAddress],
    queryFn: () => fetchPremiumOptimizationHints(walletAddress!),
    enabled: Boolean(walletAddress) && isPremium,
  });

  const notificationsQuery = useQuery({
    queryKey: ["premium-notifications", walletAddress],
    queryFn: () => fetchPremiumNotifications(walletAddress!),
    enabled: Boolean(walletAddress) && isPremium,
  });

  const redeemMutation = useMutation({
    mutationFn: () => redeemPremiumInvite(walletAddress!, inviteCode),
    onSuccess: async () => {
      setInviteCode("");
      await queryClient.invalidateQueries({ queryKey: ["wallet-entitlements", walletAddress] });
      await queryClient.invalidateQueries({ queryKey: ["premium-optimization-hints", walletAddress] });
      await queryClient.invalidateQueries({ queryKey: ["premium-notifications", walletAddress] });
    },
  });

  const refreshMutation = useMutation({
    mutationFn: () => postPremiumPriorityRefresh(walletAddress!),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["validators"] });
      await queryClient.invalidateQueries({ queryKey: ["intelligence-rankings"] });
    },
  });

  if (!walletAddress) {
    return (
      <PanelCard
        eyebrow="Premium"
        title="Plans and premium"
        description="Redeem an invite to unlock premium APIs, exports, and in-app alerts. Entitlements are enforced on the server."
      >
        <p className="text-sm text-muted">Connect a wallet to view your plan or redeem an invite.</p>
      </PanelCard>
    );
  }

  return (
    <PanelCard
      eyebrow="Premium"
      title="Plans and premium"
      description="Free tier keeps the full read dashboard. Premium adds deeper analytics, CSV export, priority cache refresh, and configurable alerts."
    >
      <div className="flex flex-wrap items-center gap-3">
        <span
          className={[
            "rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide",
            isPremium ? "bg-teal-500/20 text-teal-100" : "bg-slate-700 text-slate-200",
          ].join(" ")}
        >
          {entitlementQuery.data?.plan ?? "free"}
        </span>
        {entitlementQuery.data?.source ? (
          <span className="text-xs text-muted">via {entitlementQuery.data.source}</span>
        ) : null}
      </div>

      {!isPremium ? (
        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor="invite-code" className="text-xs text-muted">
              Invite code
            </label>
            <input
              id="invite-code"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              placeholder="Paste invite code"
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100"
            />
          </div>
          <button
            type="button"
            disabled={!inviteCode.trim() || redeemMutation.isPending}
            onClick={() => redeemMutation.mutate()}
            className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-50"
          >
            Redeem invite
          </button>
        </div>
      ) : null}

      {redeemMutation.isError ? (
        <p className="mt-2 text-sm text-rose-200">Could not redeem invite. Check the code or try again later.</p>
      ) : null}
      {redeemMutation.isSuccess ? (
        <p className="mt-2 text-sm text-emerald-200">{redeemMutation.data.message}</p>
      ) : null}

      {isPremium ? (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => refreshMutation.mutate()}
              disabled={refreshMutation.isPending}
              className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm text-slate-100 hover:border-teal-500 disabled:opacity-50"
            >
              Priority cache refresh
            </button>
            <button
              type="button"
              onClick={() => downloadPremiumPortfolioCsv(walletAddress)}
              className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm text-slate-100 hover:border-teal-500"
            >
              Download portfolio CSV
            </button>
          </div>
          <p className="text-xs text-muted">
            CSV and recommendations are informational only; StakeMind does not execute transactions or provide
            investment advice.
          </p>

          {hintsQuery.data ? (
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-accent">Optimization hints</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
                {hintsQuery.data.hints.map((hint) => (
                  <li key={hint}>{hint}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {notificationsQuery.data && notificationsQuery.data.length > 0 ? (
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-accent">In-app notifications</p>
              <ul className="mt-2 space-y-2 text-sm text-slate-200">
                {notificationsQuery.data.map((n) => (
                  <li key={n.id} className="rounded-lg border border-slate-800/80 bg-slate-900/40 px-3 py-2">
                    <p className="font-medium text-slate-50">{n.title}</p>
                    <p className="text-xs text-muted">{n.body}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </PanelCard>
  );
}
