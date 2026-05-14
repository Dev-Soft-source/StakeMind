"use client";

import { useQuery } from "@tanstack/react-query";

import { useCompareHotkeys } from "@/components/dashboard/CompareHotkeysContext";
import { PanelCard } from "@/components/ui/PanelCard";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import { compareValidators } from "@/lib/api/intelligence-client";

export function ValidatorComparePanel() {
  const { compareHotkeys } = useCompareHotkeys();

  const compareQuery = useQuery({
    queryKey: ["validator-compare", compareHotkeys],
    queryFn: () => compareValidators(compareHotkeys),
    enabled: compareHotkeys.length >= 2,
  });

  return (
    <PanelCard
      eyebrow="Compare"
      title="Validator compare"
      description="Select up to three validators in the explorer to compare intelligence rollups side by side."
    >
      {compareHotkeys.length < 2 ? (
        <p className="text-sm text-muted">Add at least two validators from the explorer to compare.</p>
      ) : null}

      {compareQuery.isLoading ? <p className="text-sm text-muted">Loading comparison...</p> : null}
      {compareQuery.isError ? (
        <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          Unable to compare validators. Ensure intelligence rollups exist for each hotkey.
        </p>
      ) : null}

      <div className="space-y-3">
        {(compareQuery.data?.validators ?? []).map((validator) => (
          <div
            key={`${validator.subnet_id}-${validator.hotkey}`}
            className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-3"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-50">{validator.hotkey}</p>
                <p className="text-xs text-muted">Subnet {validator.subnet_id}</p>
              </div>
              <ScoreBadge value={validator.composite_score} />
            </div>
            <div className="mt-2 grid gap-1 text-xs text-slate-300 sm:grid-cols-2">
              <p>APY estimate: {validator.apy_estimate}%</p>
              <p>Uptime: {validator.uptime_percent}%</p>
              <p>Consistency: {validator.reward_consistency}</p>
              <p>Reputation: {validator.reputation_signal}</p>
            </div>
          </div>
        ))}
      </div>

      {compareQuery.data?.limitations[0] ? (
        <p className="mt-3 text-xs text-muted">{compareQuery.data.limitations[0]}</p>
      ) : null}
    </PanelCard>
  );
}
