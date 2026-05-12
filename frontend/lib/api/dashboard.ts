export type Validator = {
  hotkey: string;
  subnet_id: number;
  uid: number | null;
  display_name: string;
  reliability_score: number;
  apy_estimate: number;
  uptime_percent: number;
  reward_consistency: number;
  delegated_stake_rao: number;
};

export type PaginatedValidators = {
  data: Validator[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
  };
};

export type StakingPortfolio = {
  wallet_address: string;
  total_stake_rao: number;
  positions: Array<{
    validator_hotkey: string;
    subnet_id: number;
    amount_rao: number;
  }>;
  subnet_exposure: Record<string, number>;
};

export type RewardSummary = {
  wallet_address: string;
  total_rewards_rao: number;
  total_stake_rao: number;
};

export type RewardHistoryPoint = {
  captured_at: string;
  amount_rao: number;
  subnet_id: number;
  validator_hotkey: string | null;
};
