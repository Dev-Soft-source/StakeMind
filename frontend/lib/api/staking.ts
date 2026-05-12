export type StakingAction = "delegate" | "undelegate" | "redelegate";

export type StakingSimulation = {
  supported: boolean;
  status: string;
  message: string;
  estimated_fee_rao?: number | null;
  block_number?: number | null;
};

export type StakingTransactionPreview = {
  action: StakingAction;
  subnet_id: number;
  amount_rao: number;
  source_validator_hotkey: string | null;
  dest_validator_hotkey: string | null;
  estimated_fee_rao?: number | null;
};

export type StakingTransaction = {
  id: string;
  wallet_address: string;
  action: StakingAction;
  subnet_id: number;
  amount_rao: number;
  source_validator_hotkey: string | null;
  dest_validator_hotkey: string | null;
  status: string;
  unsigned_payload: Record<string, unknown>;
  simulation: StakingSimulation | null;
  tx_hash: string | null;
  failure_reason: string | null;
  expires_at: string;
  submitted_at: string | null;
  confirmed_at: string | null;
  preview: StakingTransactionPreview;
};

export type BuildStakingTransactionInput = {
  wallet_address: string;
  action: StakingAction;
  subnet_id: number;
  amount_rao: number;
  source_validator_hotkey?: string;
  dest_validator_hotkey?: string;
};

export type PaginatedStakingTransactions = {
  data: StakingTransaction[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
  };
};
