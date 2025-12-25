/**
 * Risk Viewer Component
 * 
 * Detailed risk analysis and explanation.
 */

import { useState } from 'react';
import type { RiskFactor } from '../types';

function RiskViewer() {
  const [planId, setPlanId] = useState('');

  // Example risk factors for demonstration
  const exampleFactors: RiskFactor[] = [
    {
      name: 'Source Contamination',
      score: 40,
      explanation: 'Source is a funding wallet (may have KYC history)',
      remediation: 'Use transit wallets to break direct links from CEX',
    },
    {
      name: 'Timing Correlation',
      score: 30,
      explanation: 'Good timing separation with 600s minimum delay',
      remediation: null,
    },
    {
      name: 'Amount Similarity',
      score: 25,
      explanation: 'Amounts have moderate variance',
      remediation: null,
    },
    {
      name: 'Address Reuse',
      score: 0,
      explanation: 'No address reuse detected',
      remediation: null,
    },
    {
      name: 'Cross-Chain Heuristic',
      score: 0,
      explanation: 'Single-chain plan - no cross-chain risks',
      remediation: null,
    },
    {
      name: 'Same Block Activity',
      score: 0,
      explanation: 'No same-block activity detected',
      remediation: null,
    },
    {
      name: 'Round Amount',
      score: 15,
      explanation: 'Amounts appear sufficiently non-round',
      remediation: null,
    },
    {
      name: 'Gas Pattern',
      score: 10,
      explanation: 'Gas limits vary between transactions',
      remediation: null,
    },
  ];

  const getScoreClass = (score: number) => {
    if (score <= 33) return 'low';
    if (score <= 66) return 'medium';
    return 'high';
  };

  const getScoreBadge = (score: number) => {
    if (score <= 33) return 'badge-success';
    if (score <= 66) return 'badge-warning';
    return 'badge-danger';
  };

  return (
    <div>
      <h1>Risk Analysis</h1>
      <p className="text-muted mb-4">
        Understand and interpret risk scores for your transaction plans
      </p>

      {/* Risk Factors Explanation */}
      <div className="card mb-4">
        <h3 className="mb-3">Risk Factors</h3>
        <p className="text-muted mb-3">
          Each factor is scored 0-100 and weighted to produce an overall risk score.
          All scoring is deterministic and explainable - no black-box ML.
        </p>

        <table>
          <thead>
            <tr>
              <th>Factor</th>
              <th>Score</th>
              <th>Explanation</th>
              <th>Remediation</th>
            </tr>
          </thead>
          <tbody>
            {exampleFactors.map((factor) => (
              <tr key={factor.name}>
                <td><strong>{factor.name}</strong></td>
                <td>
                  <span className={`badge ${getScoreBadge(factor.score)}`}>
                    {factor.score}/100
                  </span>
                </td>
                <td className="text-muted">{factor.explanation}</td>
                <td className="text-muted">
                  {factor.remediation || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Risk Bands */}
      <div className="card mb-4">
        <h3 className="mb-3">Risk Bands</h3>
        <div className="grid grid-3">
          <div className="card" style={{ background: 'rgba(40, 167, 69, 0.1)' }}>
            <h4 className="risk-score low">LOW (0-33)</h4>
            <p className="text-muted">
              Plan appears well-structured with good operational hygiene.
              Consider proceeding with standard precautions.
            </p>
          </div>
          <div className="card" style={{ background: 'rgba(255, 193, 7, 0.1)' }}>
            <h4 className="risk-score medium">MEDIUM (34-66)</h4>
            <p className="text-muted">
              Some concerns identified. Review recommendations and
              consider adjustments before proceeding.
            </p>
          </div>
          <div className="card" style={{ background: 'rgba(220, 53, 69, 0.1)' }}>
            <h4 className="risk-score high">HIGH (67-100)</h4>
            <p className="text-muted">
              Significant issues detected. Strongly recommend addressing
              blockers before execution.
            </p>
          </div>
        </div>
      </div>

      {/* Factor Weights */}
      <div className="card mb-4">
        <h3 className="mb-3">Factor Weights</h3>
        <p className="text-muted mb-3">
          Factors are weighted based on their impact on transaction linkability:
        </p>
        <div className="grid grid-2">
          <div>
            <ul className="text-muted">
              <li>• <strong>Source Contamination:</strong> 25%</li>
              <li>• <strong>Timing Correlation:</strong> 20%</li>
              <li>• <strong>Amount Similarity:</strong> 20%</li>
              <li>• <strong>Address Reuse:</strong> 15%</li>
            </ul>
          </div>
          <div>
            <ul className="text-muted">
              <li>• <strong>Cross-Chain Heuristic:</strong> 10%</li>
              <li>• <strong>Same Block Activity:</strong> 5%</li>
              <li>• <strong>Round Amount:</strong> 3%</li>
              <li>• <strong>Gas Pattern:</strong> 2%</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Design Philosophy */}
      <div className="card">
        <h3 className="mb-3">Design Philosophy</h3>
        <div className="alert alert-info">
          <p><strong>Explainability First:</strong></p>
          <ul>
            <li>Every risk factor has a clear explanation</li>
            <li>Scores are deterministic (same inputs = same output)</li>
            <li>No hidden algorithms or black-box ML in MVP</li>
            <li>Users can understand and act on recommendations</li>
          </ul>
        </div>
        <div className="alert alert-warning mt-3">
          <p><strong>What This Is NOT:</strong></p>
          <ul>
            <li>This is NOT a guarantee of privacy or anonymity</li>
            <li>Low risk does NOT mean untraceable</li>
            <li>This tool reduces linkability through discipline, not secrecy</li>
            <li>On-chain transactions are always public and verifiable</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default RiskViewer;
