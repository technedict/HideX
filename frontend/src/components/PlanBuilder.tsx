/**
 * Plan Builder Component
 * 
 * Create and manage transaction plans.
 */

import { useState } from 'react';
import { createPlan, simulatePlan } from '../utils/api';
import type { TransactionPlan, PlanType } from '../types';

function PlanBuilder() {
  const [sourceAddress, setSourceAddress] = useState('');
  const [destinationAddress, setDestinationAddress] = useState('');
  const [amount, setAmount] = useState('');
  const [planType, setPlanType] = useState<PlanType>('multi_hop');
  const [numHops, setNumHops] = useState(2);
  const [numSplits, setNumSplits] = useState(3);
  const [minDelay, setMinDelay] = useState(300);
  const [maxDelay, setMaxDelay] = useState(3600);
  const [planName, setPlanName] = useState('');

  const [creating, setCreating] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<TransactionPlan | null>(null);

  const handleCreatePlan = async () => {
    try {
      setError(null);
      setCreating(true);

      // Convert ETH to wei
      const amountWei = (parseFloat(amount) * 1e18).toFixed(0);

      const newPlan = await createPlan({
        source_address: sourceAddress,
        destination_address: destinationAddress,
        amount_wei: amountWei,
        plan_type: planType,
        num_hops: numHops,
        num_splits: numSplits,
        min_delay_seconds: minDelay,
        max_delay_seconds: maxDelay,
        name: planName || undefined,
      });

      setPlan(newPlan);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create plan');
    } finally {
      setCreating(false);
    }
  };

  const handleSimulatePlan = async () => {
    if (!plan) return;

    try {
      setError(null);
      setSimulating(true);

      const simulatedPlan = await simulatePlan(plan.id);
      setPlan(simulatedPlan);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to simulate plan');
    } finally {
      setSimulating(false);
    }
  };

  const getRiskClass = (score: number | null) => {
    if (score === null) return '';
    if (score <= 33) return 'low';
    if (score <= 66) return 'medium';
    return 'high';
  };

  const truncateAddress = (address: string) =>
    `${address.slice(0, 10)}...${address.slice(-8)}`;

  return (
    <div>
      <h1>Plan Builder</h1>
      <p className="text-muted mb-4">
        Create and simulate transaction plans before execution
      </p>

      {error && (
        <div className="alert alert-danger mb-3">{error}</div>
      )}

      <div className="grid grid-2">
        {/* Plan Configuration */}
        <div className="card">
          <h3 className="mb-3">Configure Plan</h3>

          <label>Plan Name (optional)</label>
          <input
            type="text"
            value={planName}
            onChange={(e) => setPlanName(e.target.value)}
            placeholder="e.g., Monthly transfer"
          />

          <label>Source Address</label>
          <input
            type="text"
            value={sourceAddress}
            onChange={(e) => setSourceAddress(e.target.value)}
            placeholder="0x..."
          />

          <label>Destination Address</label>
          <input
            type="text"
            value={destinationAddress}
            onChange={(e) => setDestinationAddress(e.target.value)}
            placeholder="0x..."
          />

          <label>Amount (ETH)</label>
          <input
            type="number"
            step="0.001"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="1.0"
          />

          <label>Plan Type</label>
          <select
            value={planType}
            onChange={(e) => setPlanType(e.target.value as PlanType)}
          >
            <option value="simple">Simple (Direct Transfer)</option>
            <option value="multi_hop">Multi-Hop (Through Transit Wallets)</option>
            <option value="split">Split (Multiple Paths)</option>
          </select>

          {planType === 'multi_hop' && (
            <>
              <label>Number of Hops</label>
              <input
                type="number"
                min={1}
                max={10}
                value={numHops}
                onChange={(e) => setNumHops(parseInt(e.target.value))}
              />
            </>
          )}

          {planType === 'split' && (
            <>
              <label>Number of Splits</label>
              <input
                type="number"
                min={2}
                max={10}
                value={numSplits}
                onChange={(e) => setNumSplits(parseInt(e.target.value))}
              />
            </>
          )}

          {planType !== 'simple' && (
            <>
              <label>Min Delay (seconds)</label>
              <input
                type="number"
                min={0}
                value={minDelay}
                onChange={(e) => setMinDelay(parseInt(e.target.value))}
              />

              <label>Max Delay (seconds)</label>
              <input
                type="number"
                min={0}
                value={maxDelay}
                onChange={(e) => setMaxDelay(parseInt(e.target.value))}
              />
            </>
          )}

          <div className="flex gap-2 mt-3">
            <button
              className="btn-primary"
              onClick={handleCreatePlan}
              disabled={creating || !sourceAddress || !destinationAddress || !amount}
            >
              {creating ? 'Creating...' : 'Create Plan'}
            </button>
          </div>
        </div>

        {/* Plan Preview */}
        <div className="card">
          <h3 className="mb-3">Plan Preview</h3>

          {!plan ? (
            <p className="text-muted text-center">
              Configure and create a plan to see preview
            </p>
          ) : (
            <>
              {/* Plan Info */}
              <div className="mb-3">
                <p><strong>Name:</strong> {plan.name || 'Unnamed'}</p>
                <p><strong>Amount:</strong> {plan.total_amount_formatted}</p>
                <p><strong>Status:</strong> 
                  <span className={`badge ${plan.status === 'simulated' ? 'badge-success' : 'badge-info'}`}>
                    {plan.status}
                  </span>
                </p>
                <p><strong>Mode:</strong> 
                  <span className={`badge ${plan.is_dry_run ? 'badge-warning' : 'badge-danger'}`}>
                    {plan.is_dry_run ? 'SIMULATION' : 'LIVE'}
                  </span>
                </p>
              </div>

              {/* Risk Score */}
              {plan.risk_score !== null && (
                <div className="mb-3">
                  <p><strong>Risk Assessment:</strong></p>
                  <div className={`risk-score ${getRiskClass(plan.risk_score)}`}>
                    {plan.risk_score}/100 ({plan.risk_band})
                  </div>
                  <div className="progress-bar mt-2">
                    <div
                      className={`progress-bar-fill ${getRiskClass(plan.risk_score)}`}
                      style={{ width: `${plan.risk_score}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Policy Compliance */}
              {plan.policy_violations.length > 0 && (
                <div className="alert alert-danger mb-3">
                  <strong>Policy Violations:</strong>
                  <ul>
                    {plan.policy_violations.map((v, i) => (
                      <li key={i}>{v}</li>
                    ))}
                  </ul>
                </div>
              )}

              {plan.policy_warnings.length > 0 && (
                <div className="alert alert-warning mb-3">
                  <strong>Warnings:</strong>
                  <ul>
                    {plan.policy_warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Steps */}
              <div className="mb-3">
                <p><strong>Transaction Steps:</strong></p>
                <div className="steps">
                  {plan.steps.map((step) => (
                    <div className="step" key={step.id}>
                      <div className="step-number">{step.order + 1}</div>
                      <div className="step-content">
                        <div className="step-addresses">
                          {truncateAddress(step.from_address)} → {truncateAddress(step.to_address)}
                        </div>
                        <div className="text-muted">
                          {step.amount_formatted}
                          {step.delay_seconds > 0 && ` (delay: ${step.delay_seconds}s)`}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  className="btn-success"
                  onClick={handleSimulatePlan}
                  disabled={simulating || plan.status === 'simulated'}
                >
                  {simulating ? 'Simulating...' : 'Simulate Plan'}
                </button>
              </div>

              {/* Execution Warning */}
              <div className="alert alert-info mt-3">
                <strong>Note:</strong> Live execution is disabled in this demo.
                All plans run in simulation mode.
              </div>
            </>
          )}
        </div>
      </div>

      {/* Plan Type Explanation */}
      <div className="card mt-4">
        <h3>Plan Types Explained</h3>
        <div className="grid grid-3">
          <div>
            <h4>📦 Simple Transfer</h4>
            <p className="text-muted">
              Direct single-hop transfer. Not privacy-optimized.
              Use only when speed is more important than hygiene.
            </p>
          </div>
          <div>
            <h4>🔄 Multi-Hop</h4>
            <p className="text-muted">
              Routes through transit wallets with timing delays.
              Breaks direct source-to-destination links.
            </p>
          </div>
          <div>
            <h4>🔀 Split</h4>
            <p className="text-muted">
              Splits amount across multiple paths.
              Reduces amount correlation risk.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PlanBuilder;
