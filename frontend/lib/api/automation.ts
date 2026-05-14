export type AutomationPolicy = {
  wallet_address: string;
  opt_in: boolean;
  kill_switch_active: boolean;
  max_amount_rao_per_action: number;
  max_daily_jobs: number;
  allowed_validator_hotkeys: string[];
  allowed_subnet_ids: number[];
  compound_threshold_rao: number;
  disclaimer: string;
};

export type AutomationJob = {
  id: string;
  wallet_address: string;
  job_type: string;
  payload: Record<string, unknown>;
  status: string;
  scheduled_for: string;
  attempts: number;
  max_attempts: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type AutomationIncident = {
  id: string;
  wallet_address: string;
  job_id: string | null;
  severity: string;
  code: string;
  message: string;
  meta: Record<string, unknown>;
  created_at: string;
  resolved_at: string | null;
};
