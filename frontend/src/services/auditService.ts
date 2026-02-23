// Audit Service for API interactions
import { AuditLog, AuditFilter } from '../types/audit';

const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT || 'http://localhost:3001/api';

export class AuditService {
  /**
   * Get audit logs with optional filtering
   */
  static async getAuditLogs(filter: AuditFilter = {}): Promise<AuditLog[]> {
    try {
      const params = new URLSearchParams();
      if (filter.entityId) params.append('entityId', filter.entityId);
      if (filter.actor) params.append('actor', filter.actor);
      if (filter.actionType) params.append('actionType', filter.actionType);
      if (filter.dateFrom) params.append('dateFrom', filter.dateFrom);
      if (filter.dateTo) params.append('dateTo', filter.dateTo);

      const response = await fetch(`${API_ENDPOINT}/audit-logs?${params.toString()}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch audit logs');
      }

      const data = await response.json();
      return data.logs || [];
    } catch (error) {
      console.error('Error fetching audit logs:', error);
      throw error;
    }
  }

  /**
   * Export audit logs to CSV
   */
  static async exportAuditLogs(filter: AuditFilter = {}): Promise<Blob> {
    try {
      const logs = await this.getAuditLogs(filter);
      
      // Convert logs to CSV format
      const headers = ['Timestamp', 'Actor', 'Action Type', 'Entity Type', 'Entity ID', 'Details', 'Reasoning'];
      const csvRows = [headers.join(',')];
      
      logs.forEach(log => {
        const row = [
          log.Timestamp,
          log.Actor,
          log.ActionType,
          log.EntityType,
          log.EntityId,
          JSON.stringify(log.Details).replace(/,/g, ';'),
          log.Reasoning ? JSON.stringify(log.Reasoning).replace(/,/g, ';') : ''
        ];
        csvRows.push(row.join(','));
      });

      const csvContent = csvRows.join('\n');
      return new Blob([csvContent], { type: 'text/csv' });
    } catch (error) {
      console.error('Error exporting audit logs:', error);
      throw error;
    }
  }
}
