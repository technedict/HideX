/**
 * TypeScript types for HideX frontend.
 * 
 * All types match the backend API schemas.
 */

export type WalletRole = 'funding' | 'transit' | 'destination';
export type WalletState = 'active' | 'used' | 'retired' | 'compromised';
export type RiskBand = 'LOW' | 'MEDIUM' | 'HIGH';
export type PlanType = 'simple' | 'multi_hop' | 'split';
export type TransactionStatus = 'planned' | 'simulated' | 'pending_confirmation' | 'confirmed' | 'executing' | 'executed' | 'failed' | 'cancelled';

export interface Wallet {
  id: string;
  address: string;
  role: WalletRole;
  state: WalletState;
  chain: string;
  label: string | null;
  created_at: string;
  transaction_count: number;
  is_one_time: boolean;
}

export interface TransactionStep {
  id: string;
  order: number;
  from_address: string;
  to_address: string;
  amount_formatted: string;
  delay_seconds: number;
  status: string;
  tx_hash: string | null;
  description: string | null;
}

export interface TransactionPlan {
  id: string;
  name: string | null;
  description: string | null;
  source_address: string;
  destination_address: string;
  total_amount_formatted: string;
  chain: string;
  steps: TransactionStep[];
  status: TransactionStatus;
  risk_score: number | null;
  risk_band: RiskBand | null;
  risk_explanation: string | null;
  is_policy_compliant: boolean;
  policy_violations: string[];
  policy_warnings: string[];
  created_at: string;
  simulated_at: string | null;
  executed_at: string | null;
  is_dry_run: boolean;
}

export interface RiskFactor {
  name: string;
  score: number;
  explanation: string;
  remediation: string | null;
}

export interface RiskScore {
  plan_id: string;
  score: number;
  band: RiskBand;
  summary: string;
  explanation: string;
  factors: RiskFactor[];
  recommendations: string[];
  warnings: string[];
  blockers: string[];
}

export interface PolicyRule {
  id: string;
  type: string;
  name: string;
  description: string;
  enabled: boolean;
  severity: 'warning' | 'error';
  parameters: Record<string, unknown>;
  rationale: string | null;
}

export interface Policy {
  id: string;
  name: string;
  version: string;
  description: string | null;
  strict_mode: boolean;
  allow_override: boolean;
  rules: PolicyRule[];
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  event_type: string;
  summary: string;
  plan_id: string | null;
  tx_hash: string | null;
}

export interface AuditLog {
  id: string;
  name: string | null;
  started_at: string;
  ended_at: string | null;
  total_entries: number;
  entries: AuditEntry[];
}

export interface CreatePlanRequest {
  source_address: string;
  destination_address: string;
  amount_wei: string;
  chain?: string;
  name?: string;
  plan_type: PlanType;
  num_hops?: number;
  num_splits?: number;
  min_delay_seconds?: number;
  max_delay_seconds?: number;
}

export interface ApiError {
  detail: string;
}
