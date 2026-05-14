"use client";

import { useEffect, type ComponentType } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { CompareHotkeysProvider } from "@/components/dashboard/CompareHotkeysContext";
import { ForecastPanel } from "@/components/dashboard/ForecastPanel";
import { RewardsDashboard } from "@/components/dashboard/RewardsDashboard";
import { RiskPanel } from "@/components/dashboard/RiskPanel";
import { StakingPanel } from "@/components/dashboard/StakingPanel";
import { ValidatorComparePanel } from "@/components/dashboard/ValidatorComparePanel";
import { ValidatorExplorer } from "@/components/dashboard/ValidatorExplorer";
import { ValidatorRankingsPanel } from "@/components/dashboard/ValidatorRankingsPanel";
import { WalletBar } from "@/components/wallet/WalletBar";
import { useWallet } from "@/components/wallet/WalletProvider";

type DashboardModule = ComponentType;

// Reorder rows or move modules between rows to change the dashboard layout.
const DASHBOARD_ROWS: readonly (readonly DashboardModule[])[] = [
  [WalletBar],
  [ValidatorExplorer, StakingPanel, RewardsDashboard],
  [ValidatorRankingsPanel, RiskPanel, ValidatorComparePanel, ForecastPanel],
];

function rowGridClass(moduleCount: number): string {
  if (moduleCount === 2) {
    return "grid w-full gap-4 lg:grid-cols-2";
  }
  if (moduleCount === 4) {
    return "grid w-full gap-4 lg:grid-cols-2 xl:grid-cols-4";
  }
  if (moduleCount >= 3) {
    return "grid w-full gap-4 lg:grid-cols-3";
  }
  return "grid w-full gap-4";
}

function DashboardContent() {
  const queryClient = useQueryClient();
  const { walletAddress } = useWallet();

  useEffect(() => {
    void queryClient.invalidateQueries({ queryKey: ["validators"] });
    void queryClient.invalidateQueries({ queryKey: ["validator"] });
    void queryClient.invalidateQueries({ queryKey: ["intelligence-rankings"] });
    void queryClient.invalidateQueries({ queryKey: ["validator-compare"] });

    if (!walletAddress) {
      return;
    }

    void queryClient.invalidateQueries({ queryKey: ["staking", walletAddress] });
    void queryClient.invalidateQueries({ queryKey: ["rewards-summary", walletAddress] });
    void queryClient.invalidateQueries({ queryKey: ["rewards-history", walletAddress] });
    void queryClient.invalidateQueries({ queryKey: ["wallet-risk", walletAddress] });
    void queryClient.invalidateQueries({ queryKey: ["reward-forecast", walletAddress] });
  }, [queryClient, walletAddress]);

  return (
    <div className="flex w-full flex-col gap-4">
      {DASHBOARD_ROWS.map((row, rowIndex) => {
        if (row.length === 1) {
          const Module = row[0];
          return (
            <div key={`dashboard-row-${rowIndex}`} className="w-full">
              <Module />
            </div>
          );
        }

        return (
          <div key={`dashboard-row-${rowIndex}`} className={rowGridClass(row.length)}>
            {row.map((Module, moduleIndex) => (
              <div key={`dashboard-row-${rowIndex}-module-${moduleIndex}`} className="min-w-0">
                <Module />
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

export function Dashboard() {
  return (
    <CompareHotkeysProvider>
      <DashboardContent />
    </CompareHotkeysProvider>
  );
}
