/**
 * API client for HideX backend.
 * 
 * Local-first: All requests go to the local backend.
 * No external API calls or analytics.
 */

import type {
  Wallet,
  TransactionPlan,
  RiskScore,
  Policy,
  AuditLog,
  CreatePlanRequest,
  ApiError,
} from '../types';

const API_BASE = '/api';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail);
  }
  return response.json();
}

// Health
export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health`);
  return handleResponse(response);
}

// Wallets
export async function initializeWallet(mnemonic?: string): Promise<{ mnemonic: string; warning: string }> {
  const response = await fetch(`${API_BASE}/wallets/initialize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mnemonic }),
  });
  return handleResponse(response);
}

export async function loadWallet(): Promise<{ success: boolean }> {
  const response = await fetch(`${API_BASE}/wallets/load`, {
    method: 'POST',
  });
  return handleResponse(response);
}

export async function createWallet(
  role: 'funding' | 'transit' | 'destination',
  label?: string,
  chain = 'ethereum'
): Promise<Wallet> {
  const response = await fetch(`${API_BASE}/wallets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role, label, chain }),
  });
  return handleResponse(response);
}

export async function listWallets(role?: string): Promise<{ wallets: Wallet[]; total: number }> {
  const url = new URL(`${API_BASE}/wallets`, window.location.origin);
  if (role) url.searchParams.set('role', role);
  const response = await fetch(url.toString());
  return handleResponse(response);
}

export async function getWallet(walletId: string): Promise<Wallet> {
  const response = await fetch(`${API_BASE}/wallets/${walletId}`);
  return handleResponse(response);
}

export async function retireWallet(walletId: string): Promise<Wallet> {
  const response = await fetch(`${API_BASE}/wallets/${walletId}/retire`, {
    method: 'POST',
  });
  return handleResponse(response);
}

// Plans
export async function createPlan(request: CreatePlanRequest): Promise<TransactionPlan> {
  const response = await fetch(`${API_BASE}/plans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return handleResponse(response);
}

export async function getPlan(planId: string): Promise<TransactionPlan> {
  const response = await fetch(`${API_BASE}/plans/${planId}`);
  return handleResponse(response);
}

export async function simulatePlan(planId: string): Promise<TransactionPlan> {
  const response = await fetch(`${API_BASE}/plans/${planId}/simulate`, {
    method: 'POST',
  });
  return handleResponse(response);
}

export async function getPlanRisk(planId: string): Promise<RiskScore> {
  const response = await fetch(`${API_BASE}/plans/${planId}/risk`);
  return handleResponse(response);
}

export async function validatePlan(planId: string): Promise<unknown> {
  const response = await fetch(`${API_BASE}/plans/${planId}/validate`);
  return handleResponse(response);
}

export async function executePlan(
  planId: string,
  confirmation: boolean,
  acceptHighRisk = false,
  riskOverrideReason?: string
): Promise<TransactionPlan> {
  const response = await fetch(`${API_BASE}/plans/${planId}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      plan_id: planId,
      confirmation,
      accept_high_risk: acceptHighRisk,
      risk_override_reason: riskOverrideReason,
    }),
  });
  return handleResponse(response);
}

// Policies
export async function listPolicies(): Promise<{ policies: Policy[]; total: number }> {
  const response = await fetch(`${API_BASE}/policies`);
  return handleResponse(response);
}

export async function getPolicy(policyId: string): Promise<Policy> {
  const response = await fetch(`${API_BASE}/policies/${policyId}`);
  return handleResponse(response);
}

export async function getDefaultPolicyTemplate(): Promise<Policy> {
  const response = await fetch(`${API_BASE}/policies/default/template`);
  return handleResponse(response);
}

export async function activatePolicy(policyId: string): Promise<{ success: boolean }> {
  const response = await fetch(`${API_BASE}/policies/${policyId}/activate`, {
    method: 'POST',
  });
  return handleResponse(response);
}

// Audit
export async function getCurrentAuditLog(): Promise<AuditLog> {
  const response = await fetch(`${API_BASE}/audit/current`);
  return handleResponse(response);
}

export async function listAuditSessions(): Promise<{ sessions: string[]; total: number }> {
  const response = await fetch(`${API_BASE}/audit/sessions`);
  return handleResponse(response);
}

export async function getAuditSession(sessionId: string): Promise<AuditLog> {
  const response = await fetch(`${API_BASE}/audit/sessions/${sessionId}`);
  return handleResponse(response);
}

export async function getComplianceReport(planId: string): Promise<unknown> {
  const response = await fetch(`${API_BASE}/audit/reports/${planId}`);
  return handleResponse(response);
}
