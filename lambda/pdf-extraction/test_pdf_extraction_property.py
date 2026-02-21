"""
Property-Based Tests for PDF Extraction Lambda
Tests Property 9: Invoice Data Extraction Completeness
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch, MagicMock
import json
import os
from datetime import datetime
from typing import Dict, Any

# Set environment variables before importing index
os.environ['INVOICES_TABLE_NAME'] = 'test-invoices-table'
os.environ['AUDIT_LOGS_TABLE_NAME'] = 'test-audit-logs-table'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Mock boto3 before importing index
with patch('boto3.client'), patch('boto3.resource'):
    # Import the functions to test
    from index import (
        parse_invoice_data,
        validate_invoice_data,
        PermanentError
    )


# Custom strategies for generating invoice text
@st.composite
def invoice_text_strategy(draw):
    """Generate realistic invoice text with all required fields."""
    
    # Generate required fields
    invoice_number = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Nd'), min_codepoint=48, max_codepoint=90),
        min_size=5,
        max_size=15
    ))
    
    vendor_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122),
        min_size=4,
        max_size=50
    ).filter(lambda x: len(x.strip()) >= 4))
    
    # Generate date in MM/DD/YYYY format
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))
    year = draw(st.integers(min_value=2020, max_value=2024))
    invoice_date = f"{month:02d}/{day:02d}/{year}"
    
    # Generate line items (at least 1)
    num_items = draw(st.integers(min_value=1, max_value=10))
    line_items = []
    total_amount = 0.0
    
    for i in range(num_items):
        item_desc = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=48, max_codepoint=122),
            min_size=5,
            max_size=30
        ))
        quantity = draw(st.integers(min_value=1, max_value=100))
        unit_price = draw(st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False))
        unit_price = round(unit_price, 2)
        item_total = round(quantity * unit_price, 2)
        total_amount += item_total
        
        line_items.append({
            'description': item_desc,
            'quantity': quantity,
            'unit_price': unit_price,
            'total': item_total
        })
    
    total_amount = round(total_amount, 2)
    
    # Build invoice text
    invoice_text = f"""{vendor_name}
123 Business Street
City, State 12345

INVOICE

Invoice Number: {invoice_number}
Invoice Date: {invoice_date}

BILL TO:
Customer Name
Customer Address

ITEMS:
Description                    Qty    Unit Price    Total
{"=" * 60}
"""
    
    for item in line_items:
        invoice_text += f"{item['description']:<30} {item['quantity']:<6} ${item['unit_price']:<12.2f} ${item['total']:<10.2f}\n"
    
    invoice_text += f"""
{"=" * 60}
TOTAL: ${total_amount:.2f}

Thank you for your business!
"""
    
    return {
        'text': invoice_text,
        'expected': {
            'invoice_number': invoice_number,
            'vendor_name': vendor_name,
            'invoice_date': invoice_date,
            'total_amount': total_amount,
            'line_items_count': num_items
        }
    }


# Feature: reconcile-ai, Property 9: Invoice Data Extraction Completeness
@given(invoice_data=invoice_text_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_invoice_data_extraction_completeness(invoice_data):
    """
    Property 9: Invoice Data Extraction Completeness
    
    For any successfully extracted invoice, the stored data should contain:
    - invoice_number
    - vendor_name
    - invoice_date
    - line_items (at least 1)
    - total_amount
    
    Validates: Requirements 4.1, 4.2, 4.4
    """
    invoice_text = invoice_data['text']
    expected = invoice_data['expected']
    
    # Parse the invoice data
    parsed_data = parse_invoice_data(invoice_text)
    
    # Property: All required fields must be present
    assert parsed_data['invoice_number'] is not None, \
        "Invoice number must be extracted"
    
    assert parsed_data['vendor_name'] is not None, \
        "Vendor name must be extracted"
    
    assert parsed_data['invoice_date'] is not None, \
        "Invoice date must be extracted"
    
    assert parsed_data['total_amount'] is not None, \
        "Total amount must be extracted"
    
    assert parsed_data['line_items'] is not None, \
        "Line items must be present"
    
    assert len(parsed_data['line_items']) >= 1, \
        "At least one line item must be extracted"
    
    # Property: Validation should pass for complete data
    try:
        validate_invoice_data(parsed_data)
    except PermanentError as e:
        pytest.fail(f"Validation failed for complete invoice data: {str(e)}")
    
    # Property: Each line item must have required fields
    for line_item in parsed_data['line_items']:
        assert 'item_description' in line_item, \
            "Line item must have item_description"
        assert 'quantity' in line_item, \
            "Line item must have quantity"
        assert 'unit_price' in line_item, \
            "Line item must have unit_price"
        assert 'total_price' in line_item, \
            "Line item must have total_price"
        
        # Property: Quantities must be positive integers
        assert isinstance(line_item['quantity'], int), \
            "Quantity must be an integer"
        assert line_item['quantity'] > 0, \
            "Quantity must be positive"
        
        # Property: Prices must be positive numbers
        assert line_item['unit_price'] > 0, \
            "Unit price must be positive"
        assert line_item['total_price'] > 0, \
            "Total price must be positive"


@given(
    invoice_number=st.one_of(st.none(), st.just("")),
    vendor_name=st.text(min_size=1, max_size=50),
    invoice_date=st.text(min_size=1, max_size=20),
    total_amount=st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False),
    line_items=st.lists(st.fixed_dictionaries({
        'item_description': st.text(min_size=1, max_size=50),
        'quantity': st.integers(min_value=1, max_value=100),
        'unit_price': st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False),
        'total_price': st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False)
    }), min_size=1, max_size=10)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_validation_rejects_missing_invoice_number(
    invoice_number, vendor_name, invoice_date, total_amount, line_items
):
    """
    Property: Validation must reject invoices with missing invoice_number.
    
    Validates: Requirements 4.1, 4.2
    """
    invoice_data = {
        'invoice_number': invoice_number,
        'vendor_name': vendor_name,
        'invoice_date': invoice_date,
        'total_amount': total_amount,
        'line_items': line_items
    }
    
    # Property: Missing invoice_number should raise PermanentError
    with pytest.raises(PermanentError) as exc_info:
        validate_invoice_data(invoice_data)
    
    assert 'invoice_number' in str(exc_info.value).lower(), \
        "Error message should mention missing invoice_number"


@given(
    invoice_number=st.text(min_size=1, max_size=20),
    vendor_name=st.one_of(st.none(), st.just("")),
    invoice_date=st.text(min_size=1, max_size=20),
    total_amount=st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False),
    line_items=st.lists(st.fixed_dictionaries({
        'item_description': st.text(min_size=1, max_size=50),
        'quantity': st.integers(min_value=1, max_value=100),
        'unit_price': st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False),
        'total_price': st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False)
    }), min_size=1, max_size=10)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_validation_rejects_missing_vendor_name(
    invoice_number, vendor_name, invoice_date, total_amount, line_items
):
    """
    Property: Validation must reject invoices with missing vendor_name.
    
    Validates: Requirements 4.1, 4.2
    """
    invoice_data = {
        'invoice_number': invoice_number,
        'vendor_name': vendor_name,
        'invoice_date': invoice_date,
        'total_amount': total_amount,
        'line_items': line_items
    }
    
    # Property: Missing vendor_name should raise PermanentError
    with pytest.raises(PermanentError) as exc_info:
        validate_invoice_data(invoice_data)
    
    assert 'vendor_name' in str(exc_info.value).lower(), \
        "Error message should mention missing vendor_name"


@given(
    invoice_number=st.text(min_size=1, max_size=20),
    vendor_name=st.text(min_size=1, max_size=50),
    invoice_date=st.text(min_size=1, max_size=20),
    total_amount=st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False),
    line_items=st.one_of(st.none(), st.just([]))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_validation_rejects_missing_line_items(
    invoice_number, vendor_name, invoice_date, total_amount, line_items
):
    """
    Property: Validation must reject invoices with no line items.
    
    Validates: Requirements 4.2, 4.4
    """
    invoice_data = {
        'invoice_number': invoice_number,
        'vendor_name': vendor_name,
        'invoice_date': invoice_date,
        'total_amount': total_amount,
        'line_items': line_items
    }
    
    # Property: Missing or empty line_items should raise PermanentError
    with pytest.raises(PermanentError) as exc_info:
        validate_invoice_data(invoice_data)
    
    assert 'line items' in str(exc_info.value).lower(), \
        "Error message should mention missing line items"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property_test"])
