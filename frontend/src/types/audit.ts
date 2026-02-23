// Audit types for ReconcileAI

export enum ActionType {
  PO_UPLOADED = 'POUploaded',
  INVOICE_RECEIVED = 'InvoiceReceived',
  INVOICE_EXTRACTED = 'InvoiceExtracted',
  INVOICE_MATCHED = 'InvoiceMatched',
  FRAUD_DETECTED = 'FraudDetected',
  INVOICE_APPROVED = 'InvoiceApproved',
  INVOICE_REJECTED = 'InvoiceRejected',
  EMAIL_CONFIGURED = 'EmailConfigured'
}

export enum EntityType {
  PO = 'PO',
  INVOICE = 'Invoice',
  USER = 'User',
  EMAIL_CONFIG = 'EmailConfig'
}

export interface AuditLog {
  LogId: string;
  Timestamp: string;
  Actor: string;
  ActionType: ActionType;
  EntityType: EntityType;
  EntityId: string;
  Details: Record<string, any>;
  Reasoning?: string;
  IPAddress?: string;
  UserAgent?: string;
}

export interface AuditFilter {
  entityId?: string;
  actor?: string;
  actionType?: string;
  dateFrom?: string;
  dateTo?: string;
}
