import React, { useState, useEffect } from 'react';
import { AuditService } from '../services/auditService';
import { AuditLog, AuditFilter, ActionType } from '../types/audit';
import './AuditTrailPage.css';

const AuditTrailPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
  
  // Filter state
  const [filter, setFilter] = useState<AuditFilter>({
    entityId: '',
    actor: '',
    actionType: '',
    dateFrom: '',
    dateTo: ''
  });

  useEffect(() => {
    loadAuditLogs();
  }, []);

  const loadAuditLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const auditLogs = await AuditService.getAuditLogs(filter);
      setLogs(auditLogs);
    } catch (err) {
      setError('Failed to load audit logs. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadAuditLogs();
  };

  const handleReset = () => {
    setFilter({
      entityId: '',
      actor: '',
      actionType: '',
      dateFrom: '',
      dateTo: ''
    });
  };

  const handleExport = async () => {
    try {
      const blob = await AuditService.exportAuditLogs(filter);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-logs-${new Date().toISOString()}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError('Failed to export audit logs. Please try again.');
      console.error(err);
    }
  };

  const toggleExpandLog = (logId: string) => {
    setExpandedLogId(expandedLogId === logId ? null : logId);
  };

  const getActionBadgeClass = (actionType: string): string => {
    const type = actionType.toLowerCase().replace(/([A-Z])/g, '-$1').toLowerCase();
    return `action-badge ${type}`;
  };

  const formatTimestamp = (timestamp: string): string => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="audit-trail-page">
      <h1>Audit Trail</h1>
      
      <div className="audit-search-form">
        <h2>Search Audit Logs</h2>
        <form onSubmit={handleSearch}>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="entityId">Entity ID</label>
              <input
                type="text"
                id="entityId"
                value={filter.entityId}
                onChange={(e) => setFilter({ ...filter, entityId: e.target.value })}
                placeholder="Enter entity ID"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="actor">Actor</label>
              <input
                type="text"
                id="actor"
                value={filter.actor}
                onChange={(e) => setFilter({ ...filter, actor: e.target.value })}
                placeholder="Enter actor name"
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="actionType">Action Type</label>
              <select
                id="actionType"
                value={filter.actionType}
                onChange={(e) => setFilter({ ...filter, actionType: e.target.value })}
              >
                <option value="">All Actions</option>
                {Object.values(ActionType).map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="dateFrom">Date From</label>
              <input
                type="date"
                id="dateFrom"
                value={filter.dateFrom}
                onChange={(e) => setFilter({ ...filter, dateFrom: e.target.value })}
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="dateTo">Date To</label>
              <input
                type="date"
                id="dateTo"
                value={filter.dateTo}
                onChange={(e) => setFilter({ ...filter, dateTo: e.target.value })}
              />
            </div>
          </div>
          
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">Search</button>
            <button type="button" className="btn btn-secondary" onClick={handleReset}>Reset</button>
            <button type="button" className="btn btn-success" onClick={handleExport}>Export to CSV</button>
          </div>
        </form>
      </div>

      <div className="audit-logs-container">
        <div className="audit-logs-header">
          <h2>Audit Logs ({logs.length})</h2>
        </div>
        
        {loading && <div className="loading-message">Loading audit logs...</div>}
        
        {error && <div className="error-message">{error}</div>}
        
        {!loading && !error && logs.length === 0 && (
          <div className="no-logs-message">No audit logs found matching your criteria.</div>
        )}
        
        {!loading && !error && logs.length > 0 && (
          <table className="audit-logs-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Entity Type</th>
                <th>Entity ID</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <React.Fragment key={log.LogId}>
                  <tr onClick={() => toggleExpandLog(log.LogId)}>
                    <td>{formatTimestamp(log.Timestamp)}</td>
                    <td>{log.Actor}</td>
                    <td>
                      <span className={getActionBadgeClass(log.ActionType)}>
                        {log.ActionType}
                      </span>
                    </td>
                    <td>{log.EntityType}</td>
                    <td>{log.EntityId}</td>
                  </tr>
                  {expandedLogId === log.LogId && (
                    <tr className="expandable-row">
                      <td colSpan={5}>
                        <div className="expandable-content">
                          <div className="details-section">
                            <h4>Details:</h4>
                            <div className="details-json">
                              {JSON.stringify(log.Details, null, 2)}
                            </div>
                          </div>
                          
                          {log.Reasoning && (
                            <div className="details-section">
                              <h4>AI Reasoning:</h4>
                              <div className="details-json">
                                {log.Reasoning}
                              </div>
                            </div>
                          )}
                          
                          {log.IPAddress && (
                            <div className="details-section">
                              <h4>IP Address:</h4>
                              <p>{log.IPAddress}</p>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default AuditTrailPage;
