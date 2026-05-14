"use client";

import { useQuery } from "@tanstack/react-query";

import { PanelCard } from "@/components/ui/PanelCard";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import { fetchValidatorRankings } from "@/lib/api/intelligence-client";

export function ValidatorRankingsPanel() {
  const rankingsQuery = useQuery({
    queryKey: ["intelligence-rankings"],
    queryFn: () => fetchValidatorRankings({ page: 1, page_size: 8, sort: "score", direction: "desc" }),
  });

  const rankings = rankingsQuery.data?.data ?? [];
  const limitations = rankings[0]?.meta.limitations ?? [];

  return (
    <PanelCard
      eyebrow="Intelligence"
      title="Validator rankings"
      description="Composite scores from stored rollups. Run intelligence recompute after catalog sync."
    >
      {rankingsQuery.isLoading ? <p className="text-sm text-muted">Loading rankings...</p> : null}
      {rankingsQuery.isError ? (
        <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          Rankings unavailable. Run intelligence recompute to populate rollups.
        </p>
      ) : null}

      <div className="space-y-2">
        {rankings.map((row) => (
          <div
            key={`${row.subnet_id}-${row.hotkey}`}
            className="flex items-center justify-between rounded-xl border border-slate-800/80 bg-slate-900/40 px-3 py-2"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-50">{row.hotkey}</p>
              <p className="text-xs text-muted">
                Subnet {row.subnet_id} · rank {row.rank_global} · APY {row.apy_estimate}%
              </p>
            </div>
            <ScoreBadge value={row.composite_score} />
          </div>
        ))}
      </div>

      {limitations.length > 0 ? (
        <p className="mt-3 text-xs text-muted">{limitations[0]}</p>
      ) : null}
    </PanelCard>
  );
}
