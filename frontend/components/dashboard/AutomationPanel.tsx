"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PanelCard } from "@/components/ui/PanelCard";
import { useWallet } from "@/components/wallet/WalletProvider";
import {
  enqueueAutomationJob,
  fetchAutomationIncidents,
  fetchAutomationJobs,
  fetchAutomationPolicy,
  postKillSwitch,
  putAutomationPolicy,
} from "@/lib/api/automation-client";

const JOB_TYPES = [
  { id: "compound_opportunity_scan", label: "Compound opportunity scan" },
  { id: "rebalance_scan", label: "Rebalance scan" },
  { id: "stuck_transaction_scan", label: "Stuck transaction scan" },
  { id: "schedule_tick", label: "Schedule tick (no-op)" },
] as const;

export function AutomationPanel() {
  const { walletAddress } = useWallet();
  const queryClient = useQueryClient();
  const [selectedJob, setSelectedJob] = useState<string>(JOB_TYPES[0].id);

  const policyQuery = useQuery({
    queryKey: ["automation-policy", walletAddress],
    queryFn: () => fetchAutomationPolicy(walletAddress!),
    enabled: Boolean(walletAddress),
  });

  const jobsQuery = useQuery({
    queryKey: ["automation-jobs", walletAddress],
    queryFn: () => fetchAutomationJobs(walletAddress!),
    enabled: Boolean(walletAddress),
  });

  const incidentsQuery = useQuery({
    queryKey: ["automation-incidents", walletAddress],
    queryFn: () => fetchAutomationIncidents(walletAddress!),
    enabled: Boolean(walletAddress),
  });

  const updatePolicy = useMutation({
    mutationFn: (body: Parameters<typeof putAutomationPolicy>[1]) =>
      putAutomationPolicy(walletAddress!, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["automation-policy", walletAddress] });
    },
  });

  const killMutation = useMutation({
    mutationFn: (active: boolean) => postKillSwitch(walletAddress!, active),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["automation-policy", walletAddress] });
    },
  });

  const enqueueMutation = useMutation({
    mutationFn: (jobType: string) => enqueueAutomationJob(walletAddress!, jobType, {}),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["automation-jobs", walletAddress] });
    },
  });

  if (!walletAddress) {
    return (
      <PanelCard
        eyebrow="Automation"
        title="Policy and jobs"
        description="Opt-in automation uses a Postgres job queue and a separate worker process. Nothing is signed server-side."
      >
        <p className="text-sm text-muted">Connect a wallet to configure automation policy.</p>
      </PanelCard>
    );
  }

  const policy = policyQuery.data;

  return (
    <PanelCard
      eyebrow="Automation"
      title="Policy and jobs"
      description={policy?.disclaimer}
    >
      {policyQuery.isLoading ? <p className="text-sm text-muted">Loading policy...</p> : null}
      {policyQuery.isError ? (
        <p className="text-sm text-rose-200">Could not load automation policy.</p>
      ) : null}

      {policy ? (
        <div className="mt-3 space-y-3 text-sm text-slate-200">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-slate-800 px-2 py-1 text-xs">
              opt-in: {policy.opt_in ? "on" : "off"}
            </span>
            <span className="rounded-full bg-slate-800 px-2 py-1 text-xs">
              kill switch: {policy.kill_switch_active ? "active (blocked)" : "inactive"}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => updatePolicy.mutate({ opt_in: !policy.opt_in })}
              className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs hover:border-teal-500"
            >
              Toggle opt-in
            </button>
            <button
              type="button"
              onClick={() => killMutation.mutate(!policy.kill_switch_active)}
              className="rounded-lg border border-rose-700/60 px-3 py-1.5 text-xs text-rose-100 hover:border-rose-500"
            >
              {policy.kill_switch_active ? "Release kill switch" : "Activate kill switch"}
            </button>
          </div>
          <p className="text-xs text-muted">
            Run worker: <code className="text-slate-300">python backend/scripts/run_automation_worker.py</code>
          </p>

          <div className="border-t border-slate-800/80 pt-3">
            <p className="text-xs uppercase tracking-[0.16em] text-accent">Enqueue job</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <select
                value={selectedJob}
                onChange={(e) => setSelectedJob(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-900/60 px-2 py-1 text-xs text-slate-100"
              >
                {JOB_TYPES.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={enqueueMutation.isPending}
                onClick={() => enqueueMutation.mutate(selectedJob)}
                className="rounded-lg bg-teal-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
              >
                Enqueue
              </button>
            </div>
            {enqueueMutation.isError ? (
              <p className="mt-2 text-xs text-rose-200">
                Enqueue rejected — enable opt-in, clear kill switch, and respect caps/allowlists.
              </p>
            ) : null}
          </div>

          <div className="border-t border-slate-800/80 pt-3">
            <p className="text-xs uppercase tracking-[0.16em] text-accent">Recent jobs</p>
            <ul className="mt-2 max-h-32 space-y-1 overflow-y-auto text-xs text-muted">
              {(jobsQuery.data ?? []).slice(0, 8).map((j) => (
                <li key={j.id}>
                  {j.job_type} · {j.status}
                  {j.error_message ? ` · ${j.error_message.slice(0, 80)}` : ""}
                </li>
              ))}
            </ul>
          </div>

          <div className="border-t border-slate-800/80 pt-3">
            <p className="text-xs uppercase tracking-[0.16em] text-accent">Incidents</p>
            <ul className="mt-2 max-h-40 space-y-2 overflow-y-auto text-xs">
              {(incidentsQuery.data ?? []).slice(0, 6).map((i) => (
                <li key={i.id} className="rounded border border-slate-800/80 bg-slate-900/40 p-2">
                  <span className="font-medium text-slate-100">{i.code}</span>{" "}
                  <span className="text-muted">({i.severity})</span>
                  <p className="text-muted">{i.message}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}
    </PanelCard>
  );
}
