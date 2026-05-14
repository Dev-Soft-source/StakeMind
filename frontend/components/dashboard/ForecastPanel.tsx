"use client";

import { useMemo } from "react";
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

import { PanelCard } from "@/components/ui/PanelCard";
import { useWallet } from "@/components/wallet/WalletProvider";
import { fetchRewardForecast } from "@/lib/api/intelligence-client";
import { formatRao } from "@/lib/format";

export function ForecastPanel() {
  const { walletAddress } = useWallet();

  const forecastQuery = useQuery({
    queryKey: ["reward-forecast", walletAddress],
    queryFn: () => fetchRewardForecast(walletAddress!, 30, 14),
    enabled: Boolean(walletAddress),
  });

  const chartData = useMemo(() => {
    return (forecastQuery.data?.forecast ?? []).map((point) => ({
      day: `+${point.day_offset}d`,
      amountRao: point.amount_rao,
    }));
  }, [forecastQuery.data?.forecast]);

  if (!walletAddress) {
    return (
      <PanelCard
        eyebrow="Forecast"
        title="Reward forecast"
        description="Short-horizon reward estimates from stored history."
      >
        <p className="text-sm text-muted">Connect a wallet to view forecast estimates.</p>
      </PanelCard>
    );
  }

  const forecast = forecastQuery.data;

  return (
    <PanelCard
      eyebrow="Forecast"
      title="Reward forecast"
      description="Estimates only — not guarantees of future rewards."
    >
      {forecastQuery.isLoading ? <p className="text-sm text-muted">Loading forecast...</p> : null}
      {forecastQuery.isError ? (
        <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          Forecast unavailable. Sync wallet rewards and run intelligence recompute.
        </p>
      ) : null}

      {forecast ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.16em] text-accent">Implied APY</p>
              <p className="mt-1 text-lg font-semibold text-slate-50">{forecast.implied_apy_pct}%</p>
            </div>
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.16em] text-accent">History window</p>
              <p className="mt-1 text-lg font-semibold text-slate-50">{forecast.history_days} days</p>
            </div>
          </div>

          <div className="mt-4 h-48 min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="day" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} width={72} />
                <Tooltip
                  formatter={(value) => [formatRao(Number(value)), "Forecast"]}
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155" }}
                />
                <Line type="monotone" dataKey="amountRao" stroke="#14b8a6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {forecast.is_estimate ? (
            <p className="mt-3 text-xs text-amber-200/90">Estimate — {forecast.limitations[0]}</p>
          ) : null}
        </>
      ) : null}
    </PanelCard>
  );
}
