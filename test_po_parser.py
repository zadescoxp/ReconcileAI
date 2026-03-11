#!/usr/bin/env python3
"""
Test the PO PDF parser directly
"""

import os
os.environ['POS_TABLE_NAME'] = 'test'
os.environ['AUDIT_LOGS_TABLE_NAME'] = 'test'
os.environ['PDF_EXTRACTION_LAMBDA_NAME'] = 'test'
os.environ['INVOICE_BUCKET_NAME'] = 'test'

import sys
sys.path.insert(0, 'lambda/po-management')

from index import parse_po_from_text

# Sample PO text
test_text = """Purchase Order
PO Number: PO-2024-001
Vendor: Acme Corporation
Date: 2024-03-01

Item Description    Quantity    Unit Price    Total Price
Widget A           10          $50.00        $500.00
Widget B           5           $100.00       $500.00
Widget C           10          $50.00        $500.00

Total Amount: $1500.00
"""

print("Testing PO parser...")
print("=" * 60)
print("Input text:")
print(test_text)
print("=" * 60)

result = parse_po_from_text(test_text)

print("\nParsed result:")
print(f"Vendor: {result['vendorName']}")
print(f"PO Number: {result['poNumber']}")
print(f"Total Amount: ${result['totalAmount']}")
print(f"Line Items: {len(result['lineItems'])}")

for item in result['lineItems']:
    print(f"  - {item['ItemDescription']}: {item['Quantity']} x ${item['UnitPrice']} = ${item['TotalPrice']}")

print("\n" + "=" * 60)
if result['vendorName'] and result['poNumber'] and result['lineItems']:
    print("✓ Parser working!")
else:
    print("✗ Parser failed!")
    print(f"Missing: ", end="")
    if not result['vendorName']:
        print("vendor ", end="")
    if not result['poNumber']:
        print("PO number ", end="")
    if not result['lineItems']:
        print("line items", end="")
    print()
