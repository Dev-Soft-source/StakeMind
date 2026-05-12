"use client";

import { useWallet } from "@/components/wallet/WalletProvider";
import { PanelCard } from "@/components/ui/PanelCard";

export function WalletBar() {
  const { walletAddress, isConnecting, connectDemoWallet, disconnectWallet } = useWallet();

  return (
    <PanelCard
      eyebrow="Wallet"
      title="Read-only staking visibility"
      description="StakeMind never stores private keys. Connect a demo wallet to load portfolio snapshots from the API."
    >
      {walletAddress ? (
        <div className="space-y-3">
          <p className="break-all text-sm text-slate-200">{walletAddress}</p>
          <button
            type="button"
            onClick={disconnectWallet}
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-100 hover:border-teal-500"
          >
            Disconnect
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => void connectDemoWallet()}
          disabled={isConnecting}
          className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
        >
          {isConnecting ? "Connecting..." : "Connect demo wallet"}
        </button>
      )}
    </PanelCard>
  );
}
