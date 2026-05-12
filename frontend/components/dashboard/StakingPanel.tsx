"use client";

import { useQuery } from "@tanstack/react-query";

import { useWallet } from "@/components/wallet/WalletProvider";
import { PanelCard } from "@/components/ui/PanelCard";
import { fetchStakingPortfolio } from "@/lib/api/dashboard-client";
import { formatRao } from "@/lib/format";

export function StakingPanel() {
  const { walletAddress } = useWallet();

  const stakingQuery = useQuery({
    queryKey: ["staking", walletAddress],
    queryFn: () => fetchStakingPortfolio(walletAddress!),
    enabled: Boolean(walletAddress),
  });

  if (!walletAddress) {
    return (
      <PanelCard
        eyebrow="Staking"
        title="Portfolio visibility"
        description="Connect a wallet to load delegation positions and subnet exposure from stored snapshots."
      >
        <p className="text-sm text-muted">No wallet connected.</p>
      </PanelCard>
    );
  }

  const portfolio = stakingQuery.data;
  const exposure = portfolio
    ? Object.entries(portfolio.subnet_exposure).sort((left, right) => right[1] - left[1])
    : [];

  return (
    <PanelCard
      eyebrow="Staking"
      title="Portfolio visibility"
      description="Delegation breakdown and subnet exposure from synced portfolio snapshots."
    >
      {stakingQuery.isLoading ? <p className="text-sm text-muted">Loading staking positions...</p> : null}
      {stakingQuery.isError ? (
        <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          Unable to load staking positions for this wallet.
        </p>
      ) : null}
      {portfolio ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-200">
            Total stake: <span className="font-semibold text-slate-50">{formatRao(portfolio.total_stake_rao)}</span>
          </p>
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-accent">Subnet exposure</p>
            {exposure.length === 0 ? (
              <p className="text-sm text-muted">No subnet exposure recorded yet.</p>
            ) : (
              exposure.map(([subnet, amount]) => (
                <div
                  key={subnet}
                  className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/40 px-3 py-2 text-sm"
                >
                  <span className="text-slate-200">Subnet {subnet}</span>
                  <span className="font-medium text-slate-50">{formatRao(amount)}</span>
                </div>
              ))
            )}
          </div>
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-accent">Positions</p>
            {portfolio.positions.length === 0 ? (
              <p className="text-sm text-muted">No delegation positions recorded yet.</p>
            ) : (
              portfolio.positions.map((position) => (
                <div
                  key={`${position.subnet_id}-${position.validator_hotkey}`}
                  className="rounded-lg border border-slate-800/80 bg-slate-900/40 px-3 py-3 text-sm"
                >
                  <p className="font-medium text-slate-50">{formatRao(position.amount_rao)}</p>
                  <p className="text-xs text-muted">Subnet {position.subnet_id}</p>
                  <p className="mt-1 break-all text-xs text-slate-400">{position.validator_hotkey}</p>
                </div>
              ))
            )}
          </div>
        </div>
      ) : null}
    </PanelCard>
  );
}
