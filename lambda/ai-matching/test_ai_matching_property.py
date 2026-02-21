"""
Property-Based Tests for AI Matching Lambda
Tests Property 12: Perfect Match Classification
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch, MagicMock
import json
import os
from typing import Dict, Any, List

# Set environment variables before importing index
os.environ['POS_TABLE_NAME'] = 'test-pos-table'
os.environ['INVOICES_TABLE_NAME'] = 'test-invoices-table'
os.environ['AUDIT_LOGS_TABLE_NAME'] = 'test-audit-logs-table'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Mock boto3 before importing index
with patch('boto3.client'), patch('boto3.resource'):
    # Import the functions to test
    from index import (
        classify_perfect_match,
        PRICE_TOLERANCE,
        PRICE_TOLERANCE_EPSILON
    )


# Custom strategies for generating line items
@st.composite
def line_item_strategy(draw):
    """Generate a realistic line item."""
    item_description = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'), min_codepoint=32, max_codepoint=122),
        min_size=5,
        max_size=50
    ).filter(lambda x: len(x.strip()) >= 5))
    
    quantity = draw(st.integers(min_value=1, max_value=100))
    unit_price = draw(st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False))
    unit_price = round(unit_price, 2)
    total_price = round(quantity * unit_price, 2)
    
    return {
        'item_description': item_description,
        'quantity': quantity,
        'unit_price': unit_price,
        'total_price': total_price
    }


@st.composite
def po_line_item_strategy(draw, invoice_item=None):
    """Generate a PO line item, optionally matching an invoice item."""
    if invoice_item:
        # Generate matching PO item with exact quantity and within price tolerance
        item_description = invoice_item['item_description']
        quantity = invoice_item['quantity']
        
        # Price within ±5% tolerance
        # Important: The tolerance check uses PO price as denominator: |inv_price - po_price| / po_price <= 0.05
        # To ensure we stay within tolerance after rounding, we need to be more conservative
        # We want: |base_price - po_price| / po_price <= 0.05
        # This means: po_price >= base_price / 1.05 AND po_price <= base_price / 0.95
        base_price = invoice_item['unit_price']
        
        # Use a slightly tighter range to account for rounding errors
        # Instead of exactly 5%, use 4.5% to leave margin for rounding
        safe_tolerance = 0.045
        min_po_price = base_price / (1 + safe_tolerance)
        max_po_price = base_price / (1 - safe_tolerance)
        
        unit_price = draw(st.floats(min_value=min_po_price, max_value=max_po_price, allow_nan=False, allow_infinity=False))
        unit_price = round(unit_price, 2)
        
        return {
            'ItemDescription': item_description,
            'Quantity': quantity,
            'UnitPrice': unit_price,
            'TotalPrice': round(quantity * unit_price, 2)
        }
    else:
        # Generate random PO item
        item_description = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'), min_codepoint=32, max_codepoint=122),
            min_size=5,
            max_size=50
        ).filter(lambda x: len(x.strip()) >= 5))
        
        quantity = draw(st.integers(min_value=1, max_value=100))
        unit_price = draw(st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False))
        unit_price = round(unit_price, 2)
        
        return {
            'ItemDescription': item_description,
            'Quantity': quantity,
            'UnitPrice': unit_price,
            'TotalPrice': round(quantity * unit_price, 2)
        }


@st.composite
def perfect_match_invoice_and_pos_strategy(draw):
    """
    Generate an invoice and matching POs where all line items match within tolerances.
    This should result in a perfect match classification.
    """
    vendor_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122),
        min_size=4,
        max_size=50
    ).filter(lambda x: len(x.strip()) >= 4))
    
    # Generate invoice line items
    num_items = draw(st.integers(min_value=1, max_value=5))
    invoice_items = [draw(line_item_strategy()) for _ in range(num_items)]
    
    invoice_total = sum(item['total_price'] for item in invoice_items)
    
    invoice = {
        'InvoiceId': 'test-invoice-id',
        'VendorName': vendor_name,
        'InvoiceNumber': 'INV-' + draw(st.text(alphabet='0123456789', min_size=5, max_size=10)),
        'InvoiceDate': '2024-01-15',
        'LineItems': invoice_items,
        'TotalAmount': invoice_total
    }
    
    # Generate matching PO with all items matching within tolerance
    po_items = [draw(po_line_item_strategy(inv_item)) for inv_item in invoice_items]
    po_total = sum(item['TotalPrice'] for item in po_items)
    
    po_id = 'PO-' + draw(st.text(alphabet='0123456789ABCDEF', min_size=8, max_size=12))
    
    po = {
        'POId': po_id,
        'VendorName': vendor_name,
        'PONumber': 'PO-' + draw(st.text(alphabet='0123456789', min_size=5, max_size=10)),
        'LineItems': po_items,
        'TotalAmount': po_total
    }
    
    return {
        'invoice': invoice,
        'pos': [po],
        'matched_po_ids': [po_id],
        'discrepancies': []
    }


@st.composite
def imperfect_match_invoice_and_pos_strategy(draw):
    """
    Generate an invoice and POs with discrepancies (price mismatch, quantity mismatch, or missing items).
    This should NOT result in a perfect match classification.
    """
    vendor_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122),
        min_size=4,
        max_size=50
    ).filter(lambda x: len(x.strip()) >= 4))
    
    # Generate invoice line items
    num_items = draw(st.integers(min_value=1, max_value=5))
    invoice_items = [draw(line_item_strategy()) for _ in range(num_items)]
    
    invoice_total = sum(item['total_price'] for item in invoice_items)
    
    invoice = {
        'InvoiceId': 'test-invoice-id',
        'VendorName': vendor_name,
        'InvoiceNumber': 'INV-' + draw(st.text(alphabet='0123456789', min_size=5, max_size=10)),
        'InvoiceDate': '2024-01-15',
        'LineItems': invoice_items,
        'TotalAmount': invoice_total
    }
    
    # Generate PO with intentional discrepancies
    po_items = []
    discrepancy_type = draw(st.sampled_from(['price_mismatch', 'quantity_mismatch', 'missing_item']))
    
    for idx, inv_item in enumerate(invoice_items):
        if idx == 0:  # Introduce discrepancy in first item
            if discrepancy_type == 'price_mismatch':
                # Price difference > 5%
                base_price = inv_item['unit_price']
                unit_price = round(base_price * 1.15, 2)  # 15% higher
                po_items.append({
                    'ItemDescription': inv_item['item_description'],
                    'Quantity': inv_item['quantity'],
                    'UnitPrice': unit_price,
                    'TotalPrice': round(inv_item['quantity'] * unit_price, 2)
                })
            elif discrepancy_type == 'quantity_mismatch':
                # Different quantity
                different_qty = inv_item['quantity'] + draw(st.integers(min_value=1, max_value=10))
                po_items.append({
                    'ItemDescription': inv_item['item_description'],
                    'Quantity': different_qty,
                    'UnitPrice': inv_item['unit_price'],
                    'TotalPrice': round(different_qty * inv_item['unit_price'], 2)
                })
            else:  # missing_item - skip this item in PO
                pass
        else:
            # Other items match perfectly
            po_items.append(draw(po_line_item_strategy(inv_item)))
    
    po_total = sum(item['TotalPrice'] for item in po_items)
    po_id = 'PO-' + draw(st.text(alphabet='0123456789ABCDEF', min_size=8, max_size=12))
    
    po = {
        'POId': po_id,
        'VendorName': vendor_name,
        'PONumber': 'PO-' + draw(st.text(alphabet='0123456789', min_size=5, max_size=10)),
        'LineItems': po_items,
        'TotalAmount': po_total
    }
    
    # Create discrepancy record
    discrepancies = [{
        'type': discrepancy_type.upper(),
        'invoice_line': 0,
        'po_line': 0,
        'description': f'{discrepancy_type} detected'
    }]
    
    return {
        'invoice': invoice,
        'pos': [po],
        'matched_po_ids': [po_id],
        'discrepancies': discrepancies
    }


# Feature: reconcile-ai, Property 12: Perfect Match Classification
@given(data=perfect_match_invoice_and_pos_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_perfect_match_classification_for_matching_invoices(data):
    """
    Property 12: Perfect Match Classification
    
    For any invoice where all line items match PO line items within acceptable tolerances
    (±5% price, exact quantity, matching description), the system should classify it as
    a perfect match.
    
    Validates: Requirements 5.3
    """
    invoice = data['invoice']
    pos = data['pos']
    matched_po_ids = data['matched_po_ids']
    discrepancies = data['discrepancies']
    
    # Call the classification function
    is_perfect_match = classify_perfect_match(invoice, pos, matched_po_ids, discrepancies)
    
    # Property: Should be classified as perfect match
    assert is_perfect_match is True, \
        f"Invoice with all matching line items should be classified as perfect match. " \
        f"Invoice items: {len(invoice['LineItems'])}, PO items: {len(pos[0]['LineItems'])}"


@given(data=imperfect_match_invoice_and_pos_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_perfect_match_classification_rejects_discrepancies(data):
    """
    Property 12: Perfect Match Classification (Negative Case)
    
    For any invoice with discrepancies (price mismatch >5%, quantity mismatch, or missing items),
    the system should NOT classify it as a perfect match.
    
    Validates: Requirements 5.3
    """
    invoice = data['invoice']
    pos = data['pos']
    matched_po_ids = data['matched_po_ids']
    discrepancies = data['discrepancies']
    
    # Call the classification function
    is_perfect_match = classify_perfect_match(invoice, pos, matched_po_ids, discrepancies)
    
    # Property: Should NOT be classified as perfect match
    assert is_perfect_match is False, \
        f"Invoice with discrepancies should NOT be classified as perfect match. " \
        f"Discrepancies: {discrepancies}"


@given(
    invoice=st.fixed_dictionaries({
        'InvoiceId': st.text(min_size=5, max_size=20),
        'VendorName': st.text(min_size=4, max_size=50),
        'InvoiceNumber': st.text(min_size=5, max_size=20),
        'InvoiceDate': st.just('2024-01-15'),
        'LineItems': st.lists(line_item_strategy(), min_size=1, max_size=5),
        'TotalAmount': st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False)
    }),
    pos=st.lists(st.fixed_dictionaries({
        'POId': st.text(min_size=5, max_size=20),
        'VendorName': st.text(min_size=4, max_size=50),
        'PONumber': st.text(min_size=5, max_size=20),
        'LineItems': st.lists(po_line_item_strategy(), min_size=1, max_size=5),
        'TotalAmount': st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False)
    }), min_size=1, max_size=3)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_perfect_match_requires_no_discrepancies(invoice, pos):
    """
    Property: Perfect match classification requires zero discrepancies.
    
    If AI identified any discrepancies, the invoice cannot be a perfect match.
    
    Validates: Requirements 5.3
    """
    # Create non-empty discrepancies list
    discrepancies = [{
        'type': 'PRICE_MISMATCH',
        'invoice_line': 0,
        'po_line': 0,
        'difference': 10.50,
        'description': 'Price difference detected'
    }]
    
    matched_po_ids = [po['POId'] for po in pos]
    
    # Call the classification function
    is_perfect_match = classify_perfect_match(invoice, pos, matched_po_ids, discrepancies)
    
    # Property: Must NOT be perfect match if discrepancies exist
    assert is_perfect_match is False, \
        "Invoice with discrepancies cannot be classified as perfect match"


@given(
    invoice=st.fixed_dictionaries({
        'InvoiceId': st.text(min_size=5, max_size=20),
        'VendorName': st.text(min_size=4, max_size=50),
        'InvoiceNumber': st.text(min_size=5, max_size=20),
        'InvoiceDate': st.just('2024-01-15'),
        'LineItems': st.lists(line_item_strategy(), min_size=1, max_size=5),
        'TotalAmount': st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False)
    }),
    pos=st.lists(st.fixed_dictionaries({
        'POId': st.text(min_size=5, max_size=20),
        'VendorName': st.text(min_size=4, max_size=50),
        'PONumber': st.text(min_size=5, max_size=20),
        'LineItems': st.lists(po_line_item_strategy(), min_size=1, max_size=5),
        'TotalAmount': st.floats(min_value=1.0, max_value=100000.0, allow_nan=False, allow_infinity=False)
    }), min_size=1, max_size=3)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_perfect_match_requires_matched_pos(invoice, pos):
    """
    Property: Perfect match classification requires at least one matched PO.
    
    If no POs were matched, the invoice cannot be a perfect match.
    
    Validates: Requirements 5.3
    """
    # Empty matched_po_ids list
    matched_po_ids = []
    discrepancies = []
    
    # Call the classification function
    is_perfect_match = classify_perfect_match(invoice, pos, matched_po_ids, discrepancies)
    
    # Property: Must NOT be perfect match if no POs matched
    assert is_perfect_match is False, \
        "Invoice with no matched POs cannot be classified as perfect match"


@st.composite
def invoice_with_discrepancy_strategy(draw):
    """
    Generate an invoice and PO with a specific type of discrepancy.
    Returns invoice, PO, and the expected discrepancy type.
    """
    vendor_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122),
        min_size=4,
        max_size=50
    ).filter(lambda x: len(x.strip()) >= 4))
    
    # Generate a single invoice line item with reasonable price range
    invoice_item = draw(line_item_strategy())
    # Ensure price is at least $1 to avoid rounding issues with small values
    assume(invoice_item['unit_price'] >= 1.0)
    
    invoice = {
        'InvoiceId': 'test-invoice-id',
        'VendorName': vendor_name,
        'InvoiceNumber': 'INV-' + draw(st.text(alphabet='0123456789', min_size=5, max_size=10)),
        'InvoiceDate': '2024-01-15',
        'LineItems': [invoice_item],
        'TotalAmount': invoice_item['total_price']
    }
    
    # Choose discrepancy type
    discrepancy_type = draw(st.sampled_from(['PRICE_MISMATCH', 'QUANTITY_MISMATCH', 'ITEM_NOT_FOUND']))
    
    if discrepancy_type == 'PRICE_MISMATCH':
        # Create PO with price difference > 5%
        # Use a multiplier that ensures we're outside the tolerance even after rounding
        base_price = invoice_item['unit_price']
        # Use 15% difference to be well outside the 5% tolerance
        price_multiplier = draw(st.floats(min_value=1.15, max_value=2.0))
        po_unit_price = round(base_price * price_multiplier, 2)
        
        # Verify the price difference is actually > 5% after rounding
        price_diff_pct = abs(invoice_item['unit_price'] - po_unit_price) / po_unit_price
        assume(price_diff_pct > PRICE_TOLERANCE + PRICE_TOLERANCE_EPSILON)
        
        po_item = {
            'ItemDescription': invoice_item['item_description'],
            'Quantity': invoice_item['quantity'],
            'UnitPrice': po_unit_price,
            'TotalPrice': round(invoice_item['quantity'] * po_unit_price, 2)
        }
        
        po = {
            'POId': 'PO-' + draw(st.text(alphabet='0123456789ABCDEF', min_size=8, max_size=12)),
            'VendorName': vendor_name,
            'PONumber': 'PO-' + draw(st.text(alphabet='0123456789', min_size=5, max_size=10)),
            'LineItems': [po_item],
            'TotalAmount': po_item['TotalPrice']
        }
        
    elif discrepancy_type == 'QUANTITY_MISMATCH':
        # Create PO with different quantity
        different_qty = invoice_item['quantity'] + draw(st.integers(min_value=1, max_value=10))
        
        po_item = {
            'ItemDescription': invoice_item['item_description'],
            'Quantity': different_qty,
            'UnitPrice': invoice_item['unit_price'],
            'TotalPrice': round(different_qty * invoice_item['unit_price'], 2)
        }
        
        po = {
            'POId': 'PO-' + draw(st.text(alphabet='0123456789ABCDEF', min_size=8, max_size=12)),
            'VendorName': vendor_name,
            'PONumber': 'PO-' + draw(st.text(alphabet='0123456789', min_size=5, max_size=10)),
            'LineItems': [po_item],
            'TotalAmount': po_item['TotalPrice']
        }
        
    else:  # ITEM_NOT_FOUND
        # Create PO with completely different item
        different_item = draw(line_item_strategy())
        # Ensure description is sufficiently different (< 70% similarity)
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, 
                                    invoice_item['item_description'].lower(), 
                                    different_item['item_description'].lower()).ratio()
        assume(similarity < 0.7)
        
        po_item = {
            'ItemDescription': different_item['item_description'],
            'Quantity': different_item['quantity'],
            'UnitPrice': different_item['unit_price'],
            'TotalPrice': different_item['total_price']
        }
        
        po = {
            'POId': 'PO-' + draw(st.text(alphabet='0123456789ABCDEF', min_size=8, max_size=12)),
            'VendorName': vendor_name,
            'PONumber': 'PO-' + draw(st.text(alphabet='0123456789', min_size=5, max_size=10)),
            'LineItems': [po_item],
            'TotalAmount': po_item['TotalPrice']
        }
    
    return {
        'invoice': invoice,
        'po': po,
        'expected_discrepancy_type': discrepancy_type
    }


# Feature: reconcile-ai, Property 13: Discrepancy Detection Completeness
@given(data=invoice_with_discrepancy_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_discrepancy_detection_completeness(data):
    """
    Property 13: Discrepancy Detection Completeness
    
    For any invoice line item that differs from PO line items by more than acceptable
    tolerances, the system should identify and record a specific discrepancy with type,
    difference amount, and description.
    
    This test verifies that when there are actual discrepancies (price >5%, quantity
    mismatch, or missing items), the classify_perfect_match function correctly identifies
    them and returns False (not a perfect match).
    
    Validates: Requirements 5.4
    """
    invoice = data['invoice']
    po = data['po']
    expected_discrepancy_type = data['expected_discrepancy_type']
    
    # Simulate AI having identified the discrepancy
    # In real system, Bedrock would identify these discrepancies
    discrepancies = [{
        'type': expected_discrepancy_type,
        'invoice_line': 0,
        'po_line': 0,
        'description': f'{expected_discrepancy_type} detected'
    }]
    
    matched_po_ids = [po['POId']]
    
    # Call the classification function
    is_perfect_match = classify_perfect_match(invoice, [po], matched_po_ids, discrepancies)
    
    # Property: Invoice with discrepancies should NOT be classified as perfect match
    assert is_perfect_match is False, \
        f"Invoice with {expected_discrepancy_type} should NOT be classified as perfect match. " \
        f"Invoice item: {invoice['LineItems'][0]}, PO item: {po['LineItems'][0]}"


@given(data=invoice_with_discrepancy_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_discrepancy_detection_without_ai_identification(data):
    """
    Property 13: Discrepancy Detection Completeness (Verification Test)
    
    This test verifies that even if AI doesn't identify discrepancies, the
    classify_perfect_match function will still detect them through its own validation
    logic (price tolerance check, quantity check, description matching).
    
    For any invoice line item that differs from PO line items by more than acceptable
    tolerances, the classification should fail even without explicit discrepancy records.
    
    Validates: Requirements 5.4
    """
    invoice = data['invoice']
    po = data['po']
    expected_discrepancy_type = data['expected_discrepancy_type']
    
    # Test without AI-identified discrepancies (empty list)
    # The classify_perfect_match function should still detect the mismatch
    discrepancies = []
    matched_po_ids = [po['POId']]
    
    # Call the classification function
    is_perfect_match = classify_perfect_match(invoice, [po], matched_po_ids, discrepancies)
    
    # Property: Invoice with actual discrepancies should NOT be classified as perfect match
    # even if AI didn't explicitly identify them
    assert is_perfect_match is False, \
        f"Invoice with {expected_discrepancy_type} should NOT be classified as perfect match " \
        f"even without explicit discrepancy records. " \
        f"Invoice item: {invoice['LineItems'][0]}, PO item: {po['LineItems'][0]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property_test"])
