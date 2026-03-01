// Invoice types for ReconcileAI
import { LineItem } from './po';

export enum InvoiceStatus {
  RECEIVED = 'Received',
  EXTRACTING = 'Extracting',
  MATCHING = 'Matching',
  DETECTING = 'Detecting',
  FLAGGED = 'Flagged',
  APPROVED = 'Approved',
  REJECTED = 'Rejected'
}

export enum DiscrepancyType {
  PRICE_MISMATCH = 'PRICE_MISMATCH',
  QUANTITY_MISMATCH = 'QUANTITY_MISMATCH',
  ITEM_NOT_FOUND = 'ITEM_NOT_FOUND',
  AMOUNT_EXCEEDED = 'AMOUNT_EXCEEDED'
}

export enum FraudFlagType {
  PRICE_SPIKE = 'PRICE_SPIKE',
  UNRECOGNIZED_VENDOR = 'UNRECOGNIZED_VENDOR',
  DUPLICATE_INVOICE = 'DUPLICATE_INVOICE',
  AMOUNT_EXCEEDED = 'AMOUNT_EXCEEDED'
}

export enum Severity {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH'
}

export interface Discrepancy {
  type: DiscrepancyType;
  invoiceLine: LineItem;
  poLine: LineItem;
  difference: number;
  description: string;
}

export interface FraudFlag {
  flagType: FraudFlagType;
  severity: Severity;
  description: string;
  evidence: Record<string, any>;
}

export interface Invoice {
  InvoiceId: string;
  VendorName: string;
  InvoiceNumber: string;
  InvoiceDate: string;
  LineItems: LineItem[];
  TotalAmount: number | string;
  Status: InvoiceStatus;
  MatchedPOIds: string[];
  Discrepancies: Discrepancy[];
  FraudFlags: FraudFlag[];
  AIReasoning: string;
  ReceivedDate: string;
  S3Key: string;
  StepFunctionArn?: string;
}

export interface InvoiceFilter {
  status?: InvoiceStatus;
  vendorName?: string;
  dateFrom?: string;
  dateTo?: string;
}

export interface AuditEntry {
  LogId: string;
  Timestamp: string;
  Actor: string;
  ActionType: string;
  EntityType: string;
  EntityId: string;
  Details: Record<string, any>;
  Reasoning?: string;
}

export interface InvoiceDetail {
  invoice: Invoice;
  matchedPOs: any[];
  auditTrail: AuditEntry[];
}
