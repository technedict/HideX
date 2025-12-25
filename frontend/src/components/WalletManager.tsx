/**
 * Wallet Manager Component
 * 
 * Manage HD wallets with role-based separation.
 */

import { useState, useEffect } from 'react';
import { initializeWallet, listWallets, createWallet, retireWallet } from '../utils/api';
import type { Wallet, WalletRole } from '../types';

function WalletManager() {
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mnemonic, setMnemonic] = useState<string | null>(null);
  const [showMnemonic, setShowMnemonic] = useState(false);
  const [initialized, setInitialized] = useState(false);

  // New wallet form
  const [newWalletRole, setNewWalletRole] = useState<WalletRole>('transit');
  const [newWalletLabel, setNewWalletLabel] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadWallets();
  }, []);

  const loadWallets = async () => {
    try {
      setLoading(true);
      const data = await listWallets();
      setWallets(data.wallets);
      setInitialized(true);
    } catch (err) {
      // May not be initialized yet
      setInitialized(false);
    } finally {
      setLoading(false);
    }
  };

  const handleInitialize = async () => {
    try {
      setError(null);
      const result = await initializeWallet();
      setMnemonic(result.mnemonic);
      setShowMnemonic(true);
      setInitialized(true);
      await loadWallets();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize wallet');
    }
  };

  const handleCreateWallet = async () => {
    try {
      setError(null);
      setCreating(true);
      await createWallet(newWalletRole, newWalletLabel || undefined);
      setNewWalletLabel('');
      await loadWallets();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create wallet');
    } finally {
      setCreating(false);
    }
  };

  const handleRetireWallet = async (walletId: string) => {
    if (!confirm('Are you sure you want to retire this wallet?')) return;
    
    try {
      setError(null);
      await retireWallet(walletId);
      await loadWallets();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retire wallet');
    }
  };

  const truncateAddress = (address: string) => 
    `${address.slice(0, 6)}...${address.slice(-4)}`;

  const getStateBadge = (state: string) => {
    const badges: Record<string, string> = {
      active: 'badge-success',
      used: 'badge-warning',
      retired: 'badge-info',
      compromised: 'badge-danger',
    };
    return badges[state] || 'badge-info';
  };

  const getRoleBadge = (role: string) => {
    const badges: Record<string, string> = {
      funding: 'badge-warning',
      transit: 'badge-info',
      destination: 'badge-success',
    };
    return badges[role] || 'badge-info';
  };

  if (loading) {
    return <div className="card text-center">Loading wallets...</div>;
  }

  return (
    <div>
      <h1>Wallet Manager</h1>
      <p className="text-muted mb-4">
        Manage HD wallets with role-based separation for operational hygiene
      </p>

      {error && (
        <div className="alert alert-danger mb-3">{error}</div>
      )}

      {/* Mnemonic Display */}
      {showMnemonic && mnemonic && (
        <div className="alert alert-warning mb-4">
          <h3>⚠️ IMPORTANT: Save Your Mnemonic</h3>
          <p>Store this securely. You will need it to recover your wallets.</p>
          <div className="card mt-2" style={{ background: 'rgba(0,0,0,0.3)' }}>
            <code style={{ wordBreak: 'break-all' }}>{mnemonic}</code>
          </div>
          <button 
            className="btn-secondary mt-2"
            onClick={() => setShowMnemonic(false)}
          >
            I have saved my mnemonic
          </button>
        </div>
      )}

      {/* Initialize Section */}
      {!initialized && (
        <div className="card mb-4">
          <h3>Initialize Wallet System</h3>
          <p className="text-muted mb-3">
            Generate a new HD wallet or import an existing mnemonic.
          </p>
          <button className="btn-primary" onClick={handleInitialize}>
            Generate New Wallet
          </button>
        </div>
      )}

      {/* Create Wallet Form */}
      {initialized && (
        <div className="card mb-4">
          <h3>Create New Wallet</h3>
          <div className="grid grid-3">
            <div>
              <label>Role</label>
              <select
                value={newWalletRole}
                onChange={(e) => setNewWalletRole(e.target.value as WalletRole)}
              >
                <option value="funding">Funding (Source)</option>
                <option value="transit">Transit (Intermediate)</option>
                <option value="destination">Destination (Final)</option>
              </select>
            </div>
            <div>
              <label>Label (optional)</label>
              <input
                type="text"
                value={newWalletLabel}
                onChange={(e) => setNewWalletLabel(e.target.value)}
                placeholder="e.g., Main funding wallet"
              />
            </div>
            <div className="flex items-center">
              <button
                className="btn-success"
                onClick={handleCreateWallet}
                disabled={creating}
              >
                {creating ? 'Creating...' : 'Create Wallet'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Wallet List */}
      <div className="card">
        <div className="card-header">
          <h3>Your Wallets</h3>
          <span className="badge badge-info">{wallets.length} wallets</span>
        </div>

        {wallets.length === 0 ? (
          <p className="text-muted text-center">No wallets yet. Create one above.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Label</th>
                <th>Address</th>
                <th>Role</th>
                <th>State</th>
                <th>Transactions</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {wallets.map((wallet) => (
                <tr key={wallet.id}>
                  <td>{wallet.label || '-'}</td>
                  <td className="text-mono">{truncateAddress(wallet.address)}</td>
                  <td>
                    <span className={`badge ${getRoleBadge(wallet.role)}`}>
                      {wallet.role}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${getStateBadge(wallet.state)}`}>
                      {wallet.state}
                    </span>
                  </td>
                  <td>{wallet.transaction_count}</td>
                  <td>
                    {wallet.state === 'active' && (
                      <button
                        className="btn-secondary"
                        onClick={() => handleRetireWallet(wallet.id)}
                      >
                        Retire
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Role Explanation */}
      <div className="card mt-4">
        <h3>Wallet Roles Explained</h3>
        <div className="grid grid-3">
          <div>
            <h4>🏦 Funding Wallets</h4>
            <p className="text-muted">
              Source wallets that may have KYC or CEX history. 
              Use these as entry points but not for final destinations.
            </p>
          </div>
          <div>
            <h4>🔄 Transit Wallets</h4>
            <p className="text-muted">
              Intermediate wallets for breaking direct links. 
              Should be one-time use for best hygiene.
            </p>
          </div>
          <div>
            <h4>🎯 Destination Wallets</h4>
            <p className="text-muted">
              Final receiving wallets. 
              Keep these clean and separate from funding sources.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default WalletManager;
