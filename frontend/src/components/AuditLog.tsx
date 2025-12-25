/**
 * Audit Log Component
 * 
 * View and review audit logs for compliance and learning.
 */

import { useState, useEffect } from 'react';
import { getCurrentAuditLog, listAuditSessions } from '../utils/api';
import type { AuditLog as AuditLogType, AuditEntry } from '../types';

function AuditLog() {
  const [auditLog, setAuditLog] = useState<AuditLogType | null>(null);
  const [sessions, setSessions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAuditData();
  }, []);

  const loadAuditData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [logData, sessionsData] = await Promise.all([
        getCurrentAuditLog().catch(() => null),
        listAuditSessions().catch(() => ({ sessions: [], total: 0 })),
      ]);

      setAuditLog(logData);
      setSessions(sessionsData.sessions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit data');
    } finally {
      setLoading(false);
    }
  };

  const getEventTypeBadge = (eventType: string) => {
    if (eventType.includes('FAIL') || eventType.includes('VIOLATION')) {
      return 'badge-danger';
    }
    if (eventType.includes('WARNING') || eventType.includes('OVERRIDE')) {
      return 'badge-warning';
    }
    if (eventType.includes('EXECUTED') || eventType.includes('CONFIRMED')) {
      return 'badge-success';
    }
    return 'badge-info';
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  if (loading) {
    return <div className="card text-center">Loading audit log...</div>;
  }

  return (
    <div>
      <h1>Audit Log</h1>
      <p className="text-muted mb-4">
        Immutable record of all actions for compliance and forensic review
      </p>

      {error && (
        <div className="alert alert-danger mb-3">{error}</div>
      )}

      {/* Session Info */}
      <div className="card mb-4">
        <div className="card-header">
          <h3>Current Session</h3>
          <button className="btn-secondary" onClick={loadAuditData}>
            Refresh
          </button>
        </div>
        <div className="grid grid-3">
          <div>
            <p className="text-muted">Session ID</p>
            <p className="text-mono">{auditLog?.id?.slice(0, 16) || 'N/A'}...</p>
          </div>
          <div>
            <p className="text-muted">Started</p>
            <p>{auditLog?.started_at ? formatTimestamp(auditLog.started_at) : 'N/A'}</p>
          </div>
          <div>
            <p className="text-muted">Total Events</p>
            <p><span className="badge badge-info">{auditLog?.total_entries || 0}</span></p>
          </div>
        </div>
      </div>

      {/* Audit Entries */}
      <div className="card mb-4">
        <div className="card-header">
          <h3>Event Log</h3>
          <span className="badge badge-info">{auditLog?.entries?.length || 0} entries</span>
        </div>

        {!auditLog?.entries?.length ? (
          <p className="text-muted text-center">No events logged yet</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Event Type</th>
                <th>Summary</th>
                <th>Plan ID</th>
                <th>TX Hash</th>
              </tr>
            </thead>
            <tbody>
              {auditLog.entries.map((entry) => (
                <tr key={entry.id}>
                  <td className="text-muted">
                    {formatTimestamp(entry.timestamp)}
                  </td>
                  <td>
                    <span className={`badge ${getEventTypeBadge(entry.event_type)}`}>
                      {entry.event_type}
                    </span>
                  </td>
                  <td>{entry.summary}</td>
                  <td className="text-mono">
                    {entry.plan_id ? `${entry.plan_id.slice(0, 8)}...` : '-'}
                  </td>
                  <td className="text-mono">
                    {entry.tx_hash ? `${entry.tx_hash.slice(0, 10)}...` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Past Sessions */}
      {sessions.length > 0 && (
        <div className="card mb-4">
          <h3 className="mb-3">Past Sessions</h3>
          <p className="text-muted mb-3">
            Previous audit sessions are stored locally for review.
          </p>
          <ul>
            {sessions.slice(0, 10).map((sessionId) => (
              <li key={sessionId} className="text-mono text-muted">
                {sessionId}
              </li>
            ))}
          </ul>
          {sessions.length > 10 && (
            <p className="text-muted">...and {sessions.length - 10} more</p>
          )}
        </div>
      )}

      {/* Audit Log Purpose */}
      <div className="card">
        <h3 className="mb-3">About Audit Logs</h3>
        <div className="grid grid-2">
          <div>
            <h4>What is Logged</h4>
            <ul className="text-muted">
              <li>• Wallet creation and usage</li>
              <li>• Plan creation and simulation</li>
              <li>• Risk assessments</li>
              <li>• Policy validations</li>
              <li>• Transaction execution attempts</li>
              <li>• System events</li>
            </ul>
          </div>
          <div>
            <h4>Design Principles</h4>
            <ul className="text-muted">
              <li>• Append-only (immutable)</li>
              <li>• Hash chain integrity</li>
              <li>• Local storage only</li>
              <li>• No external transmission</li>
              <li>• Designed for forensic review</li>
              <li>• Supports compliance reporting</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AuditLog;
