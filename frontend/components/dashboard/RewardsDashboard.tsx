"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useWallet } from "@/components/wallet/WalletProvider";
import { PanelCard } from "@/components/ui/PanelCard";
import { fetchRewardHistory, fetchRewardSummary } from "@/lib/api/dashboard-client";
import { formatRao } from "@/lib/format";

const dayOptions = [7, 30, 90] as const;

export function RewardsDashboard() {
  const { walletAddress } = useWallet();
  const [days, setDays] = useState<(typeof dayOptions)[number]>(30);

  const summaryQuery = useQuery({
    queryKey: ["rewards-summary", walletAddress],
    queryFn: () => fetchRewardSummary(walletAddress!),
    enabled: Boolean(walletAddress),
  });

  const historyQuery = useQuery({
    queryKey: ["rewards-history", walletAddress, days],
    queryFn: () => fetchRewardHistory(walletAddress!, days),
    enabled: Boolean(walletAddress),
  });

  const chartData = useMemo(() => {
    const points = historyQuery.data ?? [];
    const grouped = new Map<string, number>();
    for (const point of points) {
      const day = point.captured_at.slice(0, 10);
      grouped.set(day, (grouped.get(day) ?? 0) + point.amount_rao);
    }
    return Array.from(grouped.entries()).map(([day, amountRao]) => ({
      day,
      amountRao,
    }));
  }, [historyQuery.data]);

  if (!walletAddress) {
    return (
      <PanelCard
        eyebrow="Rewards"
        title="Rewards dashboard"
        description="Track reward totals and trends from stored snapshots after connecting a wallet."
      >
        <p className="text-sm text-muted">No wallet connected.</p>
      </PanelCard>
    );
  }

  const summary = summaryQuery.data;

  return (
    <PanelCard
      eyebrow="Rewards"
      title="Rewards dashboard"
      description="Totals and trend lines from stored reward snapshots, not live RPC on every page load."
    >
      <div className="flex flex-wrap items-center gap-2">
        {dayOptions.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setDays(option)}
            className={[
              "rounded-lg border px-3 py-1.5 text-sm",
              days === option
                ? "border-teal-500 bg-teal-500/10 text-teal-100"
                : "border-slate-700 text-slate-200 hover:border-slate-500",
            ].join(" ")}
          >
            {option} days
          </button>
        ))}
      </div>

      {summary ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-accent">Total rewards</p>
            <p className="mt-1 text-lg font-semibold text-slate-50">{formatRao(summary.total_rewards_rao)}</p>
          </div>
          <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-accent">Total stake</p>
            <p className="mt-1 text-lg font-semibold text-slate-50">{formatRao(summary.total_stake_rao)}</p>
          </div>
        </div>
      ) : null}

      <div className="h-64 min-h-64 w-full min-w-0">
        {historyQuery.isLoading ? (
          <p className="text-sm text-muted">Loading reward history...</p>
        ) : chartData.length === 0 ? (
          <p className="text-sm text-muted">No reward history available for this range.</p>
        ) : (
          <ResponsiveContainer width="100%" height={256} minWidth={0}>
            <LineChart data={chartData}>
              <CartesianGrid stroke="#1f2937" strokeDasharray="4 4" />
              <XAxis dataKey="day" stroke="#94a3b8" tick={{ fontSize: 12 }} />
              <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#111827",
                  border: "1px solid #334155",
                  borderRadius: "0.75rem",
                }}
                formatter={(value) => [formatRao(Number(value)), "Rewards"]}
              />
              <Line type="monotone" dataKey="amountRao" stroke="#14b8a6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm text-slate-300">
          <thead className="text-xs uppercase tracking-[0.16em] text-accent">
            <tr>
              <th className="px-2 py-2">Captured</th>
              <th className="px-2 py-2">Subnet</th>
              <th className="px-2 py-2">Amount</th>
            </tr>
          </thead>
          <tbody>
            {(historyQuery.data ?? []).slice(-12).reverse().map((point) => (
              <tr
                key={`${point.captured_at}-${point.subnet_id}-${point.validator_hotkey ?? "none"}`}
                className="border-t border-slate-800/80"
              >
                <td className="px-2 py-2">{point.captured_at.slice(0, 10)}</td>
                <td className="px-2 py-2">{point.subnet_id}</td>
                <td className="px-2 py-2">{formatRao(point.amount_rao)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PanelCard>
  );
}
