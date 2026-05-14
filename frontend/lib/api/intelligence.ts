export type IntelligenceMeta = {
  methodology_version: string;
  as_of_block: number;
  computed_at: string;
  limitations: string[];
};

export type ValidatorRanking = {
  hotkey: string;
  subnet_id: number;
  composite_score: number;
  apy_estimate: number;
  reward_consistency: number;
  uptime_percent: number;
  rank_subnet: number;
  rank_global: number;
  delegation_trend: number;
  reputation_signal: number;
  meta: IntelligenceMeta;
};

export type ValidatorIntelligence = ValidatorRanking & {
  inputs: Record<string, number>;
};

export type PaginatedRankings = {
  data: ValidatorRanking[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
  };
};

export type WalletRiskProfile = {
  wallet_address: string;
  concentration_validator: number;
  concentration_subnet: number;
  hhi_validator: number;
  hhi_subnet: number;
  reward_volatility: number;
  downtime_risk_proxy: number;
  overall_risk_band: string;
  inputs: Record<string, number>;
  meta: IntelligenceMeta;
};

export type RewardForecast = {
  wallet_address: string;
  methodology_version: string;
  limitations: string[];
  is_estimate: boolean;
  implied_apy_pct: number;
  history_days: number;
  forecast: Array<{ day_offset: number; amount_rao: number }>;
};

export type CompareValidators = {
  validators: ValidatorIntelligence[];
  limitations: string[];
};
