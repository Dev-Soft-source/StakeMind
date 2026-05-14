export type WalletEntitlement = {
  plan: "free" | "premium" | string;
  source: string | null;
  valid_until: string | null;
};

export type RedeemInviteResponse = {
  plan: string;
  source: string;
  message: string;
};

export type OptimizationHintsResponse = {
  hints: string[];
  limitations: string[];
};

export type InAppNotification = {
  id: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
};

export type PriorityRefreshResponse = {
  invalidated_namespaces: string[];
};
