"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { PanelCard } from "@/components/ui/PanelCard";
import { ScoreBadge } from "@/components/ui/ScoreBadge";
import { StatusRow } from "@/components/ui/StatusRow";
import { fetchValidator, fetchValidators } from "@/lib/api/dashboard-client";
import type { Validator } from "@/lib/api/dashboard";

export function ValidatorExplorer() {
  const [search, setSearch] = useState("");
  const [subnetId, setSubnetId] = useState("");
  const [sort, setSort] = useState<"score" | "apy" | "hotkey">("score");
  const [selectedHotkey, setSelectedHotkey] = useState<string | null>(null);

  const validatorsQuery = useQuery({
    queryKey: ["validators", search, subnetId, sort],
    queryFn: () =>
      fetchValidators({
        page: 1,
        page_size: 12,
        search: search || undefined,
        subnet_id: subnetId ? Number(subnetId) : undefined,
        sort,
        direction: "desc",
      }),
  });

  const validators = useMemo(() => validatorsQuery.data?.data ?? [], [validatorsQuery.data?.data]);
  const selectedKey = useMemo(
    () => selectedHotkey ?? validators[0]?.hotkey ?? null,
    [selectedHotkey, validators],
  );

  const detailQuery = useQuery({
    queryKey: ["validator", selectedKey, subnetId],
    queryFn: () => fetchValidator(selectedKey!, subnetId ? Number(subnetId) : undefined),
    enabled: Boolean(selectedKey),
  });

  const activeValidator: Validator | undefined = detailQuery.data ?? validators[0];

  return (
    <PanelCard
      eyebrow="Validators"
      title="Validator explorer"
      description="Compare reliability, APY estimates, and subnet context from stored snapshots."
    >
      <div className="grid gap-3 md:grid-cols-3">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search validators"
          className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100"
        />
        <input
          value={subnetId}
          onChange={(event) => setSubnetId(event.target.value)}
          placeholder="Subnet ID"
          className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100"
        />
        <select
          value={sort}
          onChange={(event) => setSort(event.target.value as "score" | "apy" | "hotkey")}
          className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100"
        >
          <option value="score">Sort by score</option>
          <option value="apy">Sort by APY</option>
          <option value="hotkey">Sort by hotkey</option>
        </select>
      </div>

      <div className="mt-4 space-y-3">
        {validatorsQuery.isLoading ? <p className="text-sm text-muted">Loading validators...</p> : null}
        {validatorsQuery.isError ? (
          <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            Unable to load validators. Run catalog sync after chain-head ingestion.
          </p>
        ) : null}
        {validators.map((validator) => (
          <button
            key={`${validator.subnet_id}-${validator.hotkey}`}
            type="button"
            onClick={() => setSelectedHotkey(validator.hotkey)}
            className="block w-full text-left"
          >
            <StatusRow
              score={validator.reliability_score}
              title={validator.display_name}
              subtitle={`Subnet ${validator.subnet_id} · APY ${validator.apy_estimate}%`}
              active={selectedKey === validator.hotkey}
            />
          </button>
        ))}
      </div>

      {activeValidator ? (
        <div className="mt-4 rounded-xl border border-slate-800/80 bg-slate-900/40 p-4">
          <div className="flex items-center gap-3">
            <ScoreBadge value={activeValidator.reliability_score} />
            <div>
              <p className="text-sm font-semibold text-slate-50">{activeValidator.display_name}</p>
              <p className="text-xs text-muted">{activeValidator.hotkey}</p>
            </div>
          </div>
          <div className="mt-4 grid gap-2 text-sm text-slate-300 sm:grid-cols-2">
            <p>Subnet: {activeValidator.subnet_id}</p>
            <p>APY estimate: {activeValidator.apy_estimate}%</p>
            <p>Uptime: {activeValidator.uptime_percent}%</p>
            <p>Reward consistency: {activeValidator.reward_consistency}</p>
          </div>
        </div>
      ) : null}
    </PanelCard>
  );
}
