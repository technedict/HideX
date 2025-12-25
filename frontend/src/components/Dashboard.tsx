/**
 * Dashboard Component
 * 
 * Overview of the HideX system status.
 */

import { useState, useEffect } from 'react';
import { checkHealth, listWallets, getCurrentAuditLog } from '../utils/api';
import type { Wallet, AuditLog } from '../types';

interface DashboardProps {
  onNavigate: (tab: 'wallets' | 'plans' | 'risk' | 'audit') => void;
}

function Dashboard({ onNavigate }: DashboardProps) {
  const [health, setHealth] = useState<{ status: string } | null>(null);
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLog | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [healthData, walletsData, auditData] = await Promise.all([
        checkHealth().catch(() => ({ status: 'unavailable' })),
        listWallets().catch(() => ({ wallets: [], total: 0 })),
        getCurrentAuditLog().catch(() => null),
      ]);

      setHealth(healthData);
      setWallets(walletsData.wallets);
      setAuditLog(auditData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const walletsByRole = {
    funding: wallets.filter(w => w.role === 'funding'),
    transit: wallets.filter(w => w.role === 'transit'),
    destination: wallets.filter(w => w.role === 'destination'),
  };

  if (loading) {
    return <div className="card text-center">Loading dashboard...</div>;
  }

  return (
    <div>
      <h1>Dashboard</h1>
      <p className="text-muted mb-4">
        Privacy-hygiene and transaction-risk management overview
      </p>

      {error && (
        <div className="alert alert-danger mb-3">
          {error}
        </div>
      )}

      {/* System Status */}
      <div className="grid grid-3 mb-4">
        <div className="card">
          <div className="card-header">
            <h3>System Status</h3>
            <span className={`badge ${health?.status === 'healthy' ? 'badge-success' : 'badge-danger'}`}>
              {health?.status || 'Unknown'}
            </span>
          </div>
          <p className="text-muted">
            Backend API status
          </p>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Wallets</h3>
            <span className="badge badge-info">{wallets.length}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-muted">
              F: {walletsByRole.funding.length} | 
              T: {walletsByRole.transit.length} | 
              D: {walletsByRole.destination.length}
            </span>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Audit Events</h3>
            <span className="badge badge-info">{auditLog?.total_entries || 0}</span>
          </div>
          <p className="text-muted">
            Session: {auditLog?.id?.slice(0, 8) || 'N/A'}...
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card mb-4">
        <h3 className="mb-3">Quick Actions</h3>
        <div className="flex gap-2">
          <button className="btn-primary" onClick={() => onNavigate('wallets')}>
            Manage Wallets
          </button>
          <button className="btn-primary" onClick={() => onNavigate('plans')}>
            Create Plan
          </button>
          <button className="btn-secondary" onClick={() => onNavigate('audit')}>
            View Audit Log
          </button>
          <button className="btn-secondary" onClick={loadDashboardData}>
            Refresh
          </button>
        </div>
      </div>

      {/* Key Principles */}
      <div className="card">
        <h3 className="mb-3">Key Principles</h3>
        <div className="grid grid-2">
          <div>
            <h4>✓ What HideX Does</h4>
            <ul className="text-muted">
              <li>• Simulates transaction paths before execution</li>
              <li>• Scores privacy/traceability risk</li>
              <li>• Enforces wallet hygiene and discipline</li>
              <li>• Plans safer transaction routes</li>
              <li>• Produces audit and compliance reports</li>
            </ul>
          </div>
          <div>
            <h4>✗ What HideX Does NOT Do</h4>
            <ul className="text-muted">
              <li>• Mix, tumble, or obfuscate transactions</li>
              <li>• Provide "untraceable" transfers</li>
              <li>• Bypass sanctions or KYC requirements</li>
              <li>• Execute without explicit confirmation</li>
              <li>• Send any data to external services</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
