#!/usr/bin/env python3
"""
Generate test PO and Invoice CSV files for testing ReconcileAI
"""

import csv
import json
from datetime import datetime, timedelta
import random

def generate_po_csv(filename='test_po.csv'):
    """Generate a test Purchase Order CSV in the format the frontend expects"""
    
    line_items = [
        {'vendor': 'Acme Corporation', 'po_number': 'PO-2024-001', 'item_description': 'Widget A', 'quantity': 10, 'unit_price': 50.00, 'total_price': 500.00},
        {'vendor': 'Acme Corporation', 'po_number': 'PO-2024-001', 'item_description': 'Widget B', 'quantity': 5, 'unit_price': 100.00, 'total_price': 500.00},
        {'vendor': 'Acme Corporation', 'po_number': 'PO-2024-001', 'item_description': 'Widget C', 'quantity': 10, 'unit_price': 50.00, 'total_price': 500.00},
    ]
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header row
        writer.writerow(['VendorName', 'PONumber', 'ItemDescription', 'Quantity', 'UnitPrice', 'TotalPrice'])
        
        # Data rows
        for item in line_items:
            writer.writerow([
                item['vendor'],
                item['po_number'],
                item['item_description'],
                item['quantity'],
                item['unit_price'],
                item['total_price']
            ])
    
    print(f"✓ Generated PO CSV: {filename}")
    
    po_data = {
        'po_number': 'PO-2024-001',
        'vendor_name': 'Acme Corporation',
        'po_date': '2024-03-01',
        'total_amount': 1500.00
    }
    
    return po_data, line_items


def generate_matching_invoice_csv(po_data, line_items, filename='test_invoice_match.csv'):
    """Generate an invoice CSV that matches the PO exactly"""
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header row
        writer.writerow(['VendorName', 'InvoiceNumber', 'ItemDescription', 'Quantity', 'UnitPrice', 'TotalPrice'])
        
        # Data rows (same as PO)
        for item in line_items:
            writer.writerow([
                item['vendor'],
                'INV-2024-001',
                item['item_description'],
                item['quantity'],
                item['unit_price'],
                item['total_price']
            ])
    
    print(f"✓ Generated matching invoice CSV: {filename}")
    
    invoice_data = {
        'invoice_number': 'INV-2024-001',
        'vendor_name': po_data['vendor_name'],
        'invoice_date': '2024-03-10',
        'total_amount': po_data['total_amount']
    }
    
    return invoice_data


def generate_discrepancy_invoice_csv(po_data, line_items, filename='test_invoice_discrepancy.csv'):
    """Generate an invoice CSV with discrepancies"""
    
    # Modify quantities to create discrepancies
    modified_items = []
    total = 0
    for item in line_items:
        modified_quantity = item['quantity'] + 2  # Over-billed
        modified_total = modified_quantity * item['unit_price']
        modified_items.append({
            'vendor': item['vendor'],
            'item_description': item['item_description'],
            'quantity': modified_quantity,
            'unit_price': item['unit_price'],
            'total_price': modified_total
        })
        total += modified_total
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header row
        writer.writerow(['VendorName', 'InvoiceNumber', 'ItemDescription', 'Quantity', 'UnitPrice', 'TotalPrice'])
        
        # Data rows (modified quantities)
        for item in modified_items:
            writer.writerow([
                item['vendor'],
                'INV-2024-002',
                item['item_description'],
                item['quantity'],
                item['unit_price'],
                item['total_price']
            ])
    
    print(f"✓ Generated discrepancy invoice CSV: {filename}")
    
    invoice_data = {
        'invoice_number': 'INV-2024-002',
        'vendor_name': po_data['vendor_name'],
        'invoice_date': '2024-03-11',
        'total_amount': total
    }
    
    return invoice_data


def generate_json_format(po_data, line_items):
    """Generate JSON format for API upload"""
    
    po_json = {
        'vendorName': po_data['vendor_name'],
        'poNumber': po_data['po_number'],
        'lineItems': [
            {
                'itemDescription': item['item_description'],
                'quantity': item['quantity'],
                'unitPrice': item['unit_price']
            }
            for item in line_items
        ]
    }
    
    with open('test_po.json', 'w') as f:
        json.dump(po_json, f, indent=2)
    
    print(f"✓ Generated PO JSON: test_po.json")


if __name__ == '__main__':
    print("Generating test data files...\n")
    
    # Generate PO
    po_data, line_items = generate_po_csv('test_po.csv')
    
    # Generate matching invoice
    generate_matching_invoice_csv(po_data, line_items, 'test_invoice_match.csv')
    
    # Generate invoice with discrepancies
    generate_discrepancy_invoice_csv(po_data, line_items, 'test_invoice_discrepancy.csv')
    
    # Generate JSON format for API
    generate_json_format(po_data, line_items)
    
    print("\n✅ Test data generated successfully!")
    print("\nFiles created:")
    print("  - test_po.csv (Purchase Order)")
    print("  - test_invoice_match.csv (Invoice that matches PO)")
    print("  - test_invoice_discrepancy.csv (Invoice with quantity discrepancies)")
    print("  - test_po.json (PO in JSON format for API)")
    print("\nYou can now upload these files to test the platform.")
