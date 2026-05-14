"use client";

import { useQuery } from "@tanstack/react-query";

import { PanelCard } from "@/components/ui/PanelCard";
import { useWallet } from "@/components/wallet/WalletProvider";
import { fetchWalletRisk } from "@/lib/api/intelligence-client";

const bandStyles: Record<string, string> = {
  low: "border-emerald-500/30 bg-emerald-500/10 text-emerald-100",
  medium: "border-amber-500/30 bg-amber-500/10 text-amber-100",
  high: "border-rose-500/30 bg-rose-500/10 text-rose-100",
};

export function RiskPanel() {
  const { walletAddress } = useWallet();

  const riskQuery = useQuery({
    queryKey: ["wallet-risk", walletAddress],
    queryFn: () => fetchWalletRisk(walletAddress!),
    enabled: Boolean(walletAddress),
  });

  if (!walletAddress) {
    return (
      <PanelCard
        eyebrow="Risk"
        title="Allocation risk"
        description="Concentration and volatility signals from stored portfolio rollups."
      >
        <p className="text-sm text-muted">Connect a wallet to view risk context.</p>
      </PanelCard>
    );
  }

  const profile = riskQuery.data;
  const bandClass = bandStyles[profile?.overall_risk_band ?? "medium"] ?? bandStyles.medium;

  return (
    <PanelCard
      eyebrow="Risk"
      title="Allocation risk"
      description="Concentration, subnet exposure, and reward volatility from stored rollups."
    >
      {riskQuery.isLoading ? <p className="text-sm text-muted">Loading risk profile...</p> : null}
      {riskQuery.isError ? (
        <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          Risk rollup not found. Run portfolio sync and intelligence recompute.
        </p>
      ) : null}

      {profile ? (
        <>
          <div className={`rounded-xl border px-4 py-3 text-sm ${bandClass}`}>
            Overall band: <span className="font-semibold uppercase">{profile.overall_risk_band}</span>
          </div>
          <div className="mt-3 grid gap-2 text-sm text-slate-300 sm:grid-cols-2">
            <p>Validator concentration: {(profile.concentration_validator * 100).toFixed(1)}%</p>
            <p>Subnet concentration: {(profile.concentration_subnet * 100).toFixed(1)}%</p>
            <p>Reward volatility: {(profile.reward_volatility * 100).toFixed(1)}%</p>
            <p>Downtime proxy: {profile.downtime_risk_proxy.toFixed(1)}%</p>
          </div>
          {profile.meta.limitations[0] ? (
            <p className="mt-3 text-xs text-muted">{profile.meta.limitations[0]}</p>
          ) : null}
        </>
      ) : null}
    </PanelCard>
  );
}
