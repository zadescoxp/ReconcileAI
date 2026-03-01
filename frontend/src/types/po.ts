// Purchase Order types for ReconcileAI

export interface LineItem {
  LineNumber: number | string;
  ItemDescription: string;
  Quantity: number | string;
  UnitPrice: number | string;
  TotalPrice: number | string;
  MatchedQuantity?: number | string;
}

export enum POStatus {
  ACTIVE = 'Active',
  FULLY_MATCHED = 'FullyMatched',
  PARTIALLY_MATCHED = 'PartiallyMatched',
  EXPIRED = 'Expired'
}

export interface PO {
  POId: string;
  VendorName: string;
  PONumber: string;
  LineItems: LineItem[];
  TotalAmount: number;
  UploadDate: string;
  UploadedBy: string;
  Status: POStatus;
}

export interface POMetadata {
  vendorName: string;
  poNumber: string;
  totalAmount: number;
  lineItems: LineItem[];
}

export interface POSearchQuery {
  poNumber?: string;
  vendorName?: string;
  dateFrom?: string;
  dateTo?: string;
}

export interface POUploadResult {
  success: boolean;
  poId?: string;
  message: string;
  errors?: string[];
}
