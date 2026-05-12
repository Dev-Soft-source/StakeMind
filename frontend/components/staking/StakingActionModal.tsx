"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { createDemoSignedExtrinsic, createDemoTxHash } from "@/components/staking/signing";
import { PanelCard } from "@/components/ui/PanelCard";
import { useWallet } from "@/components/wallet/WalletProvider";
import { syncPortfolio } from "@/lib/api/dashboard-client";
import {
  buildStakingTransaction,
  fetchStakingTransaction,
  submitStakingTransaction,
} from "@/lib/api/staking-client";
import type { StakingAction, StakingTransaction } from "@/lib/api/staking";
import { formatRao } from "@/lib/format";

type StakingActionModalProps = {
  open: boolean;
  onClose: () => void;
  action: StakingAction;
  subnetId: number;
  sourceValidatorHotkey?: string;
  destValidatorHotkey?: string;
  defaultAmountRao?: number;
};

type Step = "form" | "preview" | "confirm" | "track";

export function StakingActionModal({
  open,
  onClose,
  action,
  subnetId,
  sourceValidatorHotkey,
  destValidatorHotkey,
  defaultAmountRao = 1_000_000_000,
}: StakingActionModalProps) {
  const { walletAddress } = useWallet();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>("form");
  const [amountRao, setAmountRao] = useState(defaultAmountRao);
  const [destinationHotkey, setDestinationHotkey] = useState(destValidatorHotkey ?? "");
  const [transaction, setTransaction] = useState<StakingTransaction | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setStep("form");
      setAmountRao(defaultAmountRao);
      setDestinationHotkey(destValidatorHotkey ?? "");
      setTransaction(null);
      setIdempotencyKey(null);
    }
  }, [defaultAmountRao, destValidatorHotkey, open]);

  const buildMutation = useMutation({
    mutationFn: () =>
      buildStakingTransaction(
        {
          wallet_address: walletAddress!,
          action,
          subnet_id: subnetId,
          amount_rao: amountRao,
          source_validator_hotkey: sourceValidatorHotkey,
          dest_validator_hotkey: (destValidatorHotkey ?? destinationHotkey) || undefined,
        },
        { walletAddress: walletAddress ?? undefined },
      ),
    onSuccess: (built) => {
      setTransaction(built);
      setStep("preview");
    },
  });

  const submitMutation = useMutation({
    mutationFn: (activeTransaction: StakingTransaction) => {
      const key = idempotencyKey ?? crypto.randomUUID();
      setIdempotencyKey(key);
      const txHash = createDemoTxHash(activeTransaction.unsigned_payload);
      return submitStakingTransaction(
        activeTransaction.id,
        {
          tx_hash: txHash,
          signed_extrinsic: createDemoSignedExtrinsic(activeTransaction.unsigned_payload),
        },
        { walletAddress: walletAddress ?? undefined, idempotencyKey: key },
      );
    },
    onSuccess: async (submitted) => {
      setTransaction(submitted);
      setStep("track");
      if (walletAddress) {
        await syncPortfolio(walletAddress);
        await queryClient.invalidateQueries({ queryKey: ["staking", walletAddress] });
        await queryClient.invalidateQueries({ queryKey: ["rewards-summary", walletAddress] });
        await queryClient.invalidateQueries({ queryKey: ["rewards-history", walletAddress] });
      }
    },
  });

  const statusQuery = useQuery({
    queryKey: ["staking-tx", transaction?.id],
    queryFn: () => fetchStakingTransaction(transaction!.id, { walletAddress: walletAddress ?? undefined }),
    enabled: open && step === "track" && Boolean(transaction?.id),
    refetchInterval: (query) => (query.state.data?.status === "submitted" ? 2_000 : false),
  });

  const activeTransaction = statusQuery.data ?? transaction;
  const title = useMemo(() => {
    if (action === "delegate") return "Delegate stake";
    if (action === "undelegate") return "Undelegate stake";
    return "Redelegate stake";
  }, [action]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
      <div className="w-full max-w-md">
        <PanelCard
        eyebrow="Staking action"
        title={title}
        description="StakeMind builds unsigned payloads only. Your wallet signs locally; the backend never stores private keys."
      >
        {!walletAddress ? (
          <p className="text-sm text-muted">Connect a wallet before submitting a staking action.</p>
        ) : null}

        {step === "form" ? (
          <div className="space-y-4">
            <label className="block text-sm text-slate-200">
              Amount (Rao)
              <input
                type="number"
                min={1}
                value={amountRao}
                onChange={(event) => setAmountRao(Number(event.target.value))}
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100"
              />
            </label>
            <p className="text-sm text-muted">Subnet {subnetId}</p>
            {sourceValidatorHotkey ? (
              <p className="break-all text-xs text-slate-400">Source: {sourceValidatorHotkey}</p>
            ) : null}
            {destValidatorHotkey ? (
              <p className="break-all text-xs text-slate-400">Destination: {destValidatorHotkey}</p>
            ) : null}
            {action === "redelegate" && !destValidatorHotkey ? (
              <label className="block text-sm text-slate-200">
                Destination validator hotkey
                <input
                  value={destinationHotkey}
                  onChange={(event) => setDestinationHotkey(event.target.value)}
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-100"
                />
              </label>
            ) : null}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void buildMutation.mutateAsync()}
                disabled={!walletAddress || buildMutation.isPending}
                className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
              >
                {buildMutation.isPending ? "Building preview..." : "Preview transaction"}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-100"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : null}

        {step === "preview" && activeTransaction ? (
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 text-sm text-slate-200">
              <p>Action: {activeTransaction.preview.action}</p>
              <p>Amount: {formatRao(activeTransaction.preview.amount_rao)}</p>
              <p>
                Estimated fee:{" "}
                {activeTransaction.preview.estimated_fee_rao
                  ? formatRao(activeTransaction.preview.estimated_fee_rao)
                  : "Unavailable"}
              </p>
              <p className="mt-2 text-xs text-muted">
                {activeTransaction.simulation?.message ?? "Simulation not available"}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep("confirm")}
                className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-600"
              >
                Continue to sign
              </button>
              <button
                type="button"
                onClick={() => setStep("form")}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-100"
              >
                Back
              </button>
            </div>
          </div>
        ) : null}

        {step === "confirm" && activeTransaction ? (
          <div className="space-y-4">
            <p className="text-sm text-slate-200">
              Confirm signing in your wallet. Demo mode uses a local signature stub and does not
              broadcast to Finney.
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void submitMutation.mutateAsync(activeTransaction)}
                disabled={submitMutation.isPending}
                className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
              >
                {submitMutation.isPending ? "Submitting..." : "Sign and submit"}
              </button>
              <button
                type="button"
                onClick={() => setStep("preview")}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-100"
              >
                Back
              </button>
            </div>
          </div>
        ) : null}

        {step === "track" && activeTransaction ? (
          <div className="space-y-4">
            <p className="text-sm text-slate-200">Status: {activeTransaction.status}</p>
            {activeTransaction.tx_hash ? (
              <p className="break-all text-xs text-slate-400">Tx hash: {activeTransaction.tx_hash}</p>
            ) : null}
            {activeTransaction.failure_reason ? (
              <p className="text-sm text-rose-200">{activeTransaction.failure_reason}</p>
            ) : null}
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-100"
            >
              Close
            </button>
          </div>
        ) : null}
      </PanelCard>
      </div>
    </div>
  );
}
