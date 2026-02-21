"""
Unit Tests for PDF Extraction Edge Cases
Tests malformed PDFs, PDFs with no text, and PDFs with missing fields.
Validates: Requirements 4.3
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import json
import os
import io
from botocore.exceptions import ClientError

# Set environment variables before importing index
os.environ['INVOICES_TABLE_NAME'] = 'test-invoices-table'
os.environ['AUDIT_LOGS_TABLE_NAME'] = 'test-audit-logs-table'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def mock_aws_services():
    """Mock AWS services for testing."""
    with patch('boto3.client') as mock_client, \
         patch('boto3.resource') as mock_resource:
        
        # Mock S3 client
        s3_mock = MagicMock()
        mock_client.return_value = s3_mock
        
        # Mock DynamoDB resource
        dynamodb_mock = MagicMock()
        mock_resource.return_value = dynamodb_mock
        
        # Mock tables
        invoices_table_mock = MagicMock()
        audit_logs_table_mock = MagicMock()
        dynamodb_mock.Table.side_effect = lambda name: \
            invoices_table_mock if 'invoices' in name.lower() else audit_logs_table_mock
        
        yield {
            's3': s3_mock,
            'dynamodb': dynamodb_mock,
            'invoices_table': invoices_table_mock,
            'audit_logs_table': audit_logs_table_mock
        }


# Import after mocking
from index import (
    lambda_handler,
    extract_text_from_pdf,
    parse_invoice_data,
    validate_invoice_data,
    PermanentError,
    RetryableError
)


class TestMalformedPDFs:
    """Test handling of malformed PDF files."""
    
    def test_corrupted_pdf_bytes(self, mock_aws_services):
        """Test extraction fails gracefully with corrupted PDF bytes."""
        corrupted_pdf = b'%PDF-1.4\nThis is not a valid PDF structure\n%%EOF'
        
        with pytest.raises(PermanentError) as exc_info:
            extract_text_from_pdf(corrupted_pdf)
        
        assert 'Failed to extract text from PDF' in str(exc_info.value)
    
    def test_non_pdf_file(self, mock_aws_services):
        """Test extraction fails with non-PDF file content."""
        non_pdf_content = b'This is just plain text, not a PDF file at all.'
        
        with pytest.raises(PermanentError) as exc_info:
            extract_text_from_pdf(non_pdf_content)
        
        assert 'Failed to extract text from PDF' in str(exc_info.value)
    
    def test_truncated_pdf(self, mock_aws_services):
        """Test extraction fails with truncated PDF (missing EOF marker)."""
        truncated_pdf = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n'
        
        with pytest.raises(PermanentError) as exc_info:
            extract_text_from_pdf(truncated_pdf)
        
        assert 'Failed to extract text from PDF' in str(exc_info.value)
    
    @patch('index.s3_client')
    @patch('index.invoices_table')
    @patch('index.audit_logs_table')
    def test_lambda_handler_with_malformed_pdf(
        self, mock_audit_table, mock_invoices_table, mock_s3, mock_aws_services
    ):
        """Test lambda handler returns flagged status for malformed PDF."""
        # Mock S3 to return corrupted PDF
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'corrupted pdf content')
        }
        
        event = {
            's3_bucket': 'test-bucket',
            's3_key': 'invoices/2024/01/corrupted.pdf'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['status'] == 'FLAGGED'
        assert 'error' in result
        assert result['flagged_for_manual_review'] is True


class TestPDFsWithNoText:
    """Test handling of PDFs with no extractable text."""
    
    @patch('pdfplumber.open')
    def test_pdf_with_empty_pages(self, mock_pdfplumber, mock_aws_services):
        """Test extraction fails when PDF pages contain no text."""
        # Mock PDF with pages but no text
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None
        mock_pdf.pages = [mock_page, mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)
        mock_pdfplumber.return_value = mock_pdf
        
        pdf_content = b'%PDF-1.4\nsome content\n%%EOF'
        
        extracted_text = extract_text_from_pdf(pdf_content)
        
        # Should return empty string
        assert extracted_text == ""
    
    @patch('pdfplumber.open')
    def test_pdf_with_only_whitespace(self, mock_pdfplumber, mock_aws_services):
        """Test extraction fails when PDF contains only whitespace."""
        # Mock PDF with whitespace only
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "   \n\n   \t\t   \n"
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)
        mock_pdfplumber.return_value = mock_pdf
        
        pdf_content = b'%PDF-1.4\nsome content\n%%EOF'
        
        extracted_text = extract_text_from_pdf(pdf_content)
        
        # Should return empty string after stripping
        assert extracted_text == ""
    
    @patch('pdfplumber.open')
    def test_pdf_with_very_short_text(self, mock_pdfplumber, mock_aws_services):
        """Test extraction fails when PDF has text shorter than minimum."""
        # Mock PDF with very short text
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "ABC"
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)
        mock_pdfplumber.return_value = mock_pdf
        
        pdf_content = b'%PDF-1.4\nsome content\n%%EOF'
        
        extracted_text = extract_text_from_pdf(pdf_content)
        
        # Should return the short text
        assert extracted_text == "ABC"
    
    @patch('index.s3_client')
    @patch('index.extract_text_from_pdf')
    @patch('index.audit_logs_table')
    def test_lambda_handler_with_no_text_pdf(
        self, mock_audit_table, mock_extract, mock_s3, mock_aws_services
    ):
        """Test lambda handler flags PDF with no extractable text."""
        # Mock S3 to return valid PDF bytes
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'valid pdf bytes')
        }
        
        # Mock extraction to return empty text
        mock_extract.return_value = ""
        
        event = {
            's3_bucket': 'test-bucket',
            's3_key': 'invoices/2024/01/empty.pdf'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['status'] == 'FLAGGED'
        assert 'no extractable text' in result['error'].lower()
        assert result['flagged_for_manual_review'] is True
    
    @patch('pdfplumber.open')
    def test_pdf_with_no_pages(self, mock_pdfplumber, mock_aws_services):
        """Test extraction fails when PDF has zero pages."""
        # Mock PDF with no pages
        mock_pdf = MagicMock()
        mock_pdf.pages = []
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)
        mock_pdfplumber.return_value = mock_pdf
        
        pdf_content = b'%PDF-1.4\nsome content\n%%EOF'
        
        with pytest.raises(PermanentError) as exc_info:
            extract_text_from_pdf(pdf_content)
        
        assert 'no pages' in str(exc_info.value).lower()


class TestPDFsWithMissingFields:
    """Test handling of PDFs with missing required invoice fields."""
    
    def test_missing_invoice_number(self, mock_aws_services):
        """Test validation fails when invoice number is missing."""
        invoice_text = """
        Acme Corporation
        123 Business St
        
        Date: 01/15/2024
        
        Item Description    Qty    Price    Total
        Widget A            5      10.00    50.00
        
        Total: $50.00
        """
        
        parsed_data = parse_invoice_data(invoice_text)
        
        with pytest.raises(PermanentError) as exc_info:
            validate_invoice_data(parsed_data)
        
        assert 'invoice_number' in str(exc_info.value).lower()
    
    def test_missing_vendor_name(self, mock_aws_services):
        """Test validation fails when vendor name is missing."""
        invoice_text = """
        Invoice #: INV-12345
        Date: 01/15/2024
        
        Item Description    Qty    Price    Total
        Widget A            5      10.00    50.00
        
        Total: $50.00
        """
        
        parsed_data = parse_invoice_data(invoice_text)
        
        with pytest.raises(PermanentError) as exc_info:
            validate_invoice_data(parsed_data)
        
        assert 'vendor_name' in str(exc_info.value).lower()
    
    def test_missing_invoice_date(self, mock_aws_services):
        """Test validation fails when invoice date is missing."""
        invoice_text = """
        Acme Corporation
        
        Invoice #: INV-12345
        
        Item Description    Qty    Price    Total
        Widget A            5      10.00    50.00
        
        Total: $50.00
        """
        
        parsed_data = parse_invoice_data(invoice_text)
        
        with pytest.raises(PermanentError) as exc_info:
            validate_invoice_data(parsed_data)
        
        assert 'invoice_date' in str(exc_info.value).lower()
    
    def test_missing_total_amount(self, mock_aws_services):
        """Test validation fails when total amount is missing."""
        invoice_text = """
        Acme Corporation
        
        Invoice #: INV-12345
        Date: 01/15/2024
        
        Item Description    Qty    Price    Total
        Widget A            5      10.00    50.00
        """
        
        parsed_data = parse_invoice_data(invoice_text)
        
        with pytest.raises(PermanentError) as exc_info:
            validate_invoice_data(parsed_data)
        
        assert 'total_amount' in str(exc_info.value).lower()
    
    def test_missing_line_items(self, mock_aws_services):
        """Test validation fails when no line items are found."""
        invoice_text = """Acme Corporation
123 Business Street

Invoice #: INV-12345
Date: 01/15/2024

No items listed here.

Total: $50.00
"""
        
        parsed_data = parse_invoice_data(invoice_text)
        
        with pytest.raises(PermanentError) as exc_info:
            validate_invoice_data(parsed_data)
        
        assert 'line items' in str(exc_info.value).lower()
    
    def test_multiple_missing_fields(self, mock_aws_services):
        """Test validation reports all missing fields."""
        invoice_text = """
        Some random text that doesn't match any patterns.
        This is not a proper invoice.
        """
        
        parsed_data = parse_invoice_data(invoice_text)
        
        with pytest.raises(PermanentError) as exc_info:
            validate_invoice_data(parsed_data)
        
        error_message = str(exc_info.value).lower()
        # Should mention missing fields
        assert 'missing' in error_message or 'required' in error_message
    
    @patch('index.s3_client')
    @patch('index.extract_text_from_pdf')
    @patch('index.audit_logs_table')
    def test_lambda_handler_with_missing_fields(
        self, mock_audit_table, mock_extract, mock_s3, mock_aws_services
    ):
        """Test lambda handler flags invoice with missing required fields."""
        # Mock S3 to return valid PDF bytes
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'valid pdf bytes')
        }
        
        # Mock extraction to return text with missing fields
        mock_extract.return_value = """
        Some Company
        Invoice Date: 01/15/2024
        Total: $100.00
        """
        
        event = {
            's3_bucket': 'test-bucket',
            's3_key': 'invoices/2024/01/incomplete.pdf'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['status'] == 'FLAGGED'
        assert 'missing' in result['error'].lower() or 'required' in result['error'].lower()
        assert result['flagged_for_manual_review'] is True
    
    def test_invoice_with_invalid_amount_format(self, mock_aws_services):
        """Test parsing handles invalid amount formats gracefully."""
        invoice_text = """
        Acme Corporation
        
        Invoice #: INV-12345
        Date: 01/15/2024
        
        Item Description    Qty    Price    Total
        Widget A            5      10.00    50.00
        
        Total: INVALID_AMOUNT
        """
        
        parsed_data = parse_invoice_data(invoice_text)
        
        # Should not parse the invalid amount
        assert parsed_data['total_amount'] is None
        
        # Validation should fail
        with pytest.raises(PermanentError) as exc_info:
            validate_invoice_data(parsed_data)
        
        assert 'total_amount' in str(exc_info.value).lower()


class TestEdgeCaseIntegration:
    """Integration tests for edge cases through the full lambda handler."""
    
    @patch('index.s3_client')
    @patch('index.audit_logs_table')
    def test_missing_s3_bucket_parameter(self, mock_audit_table, mock_s3, mock_aws_services):
        """Test lambda handler fails gracefully when s3_bucket is missing."""
        event = {
            's3_key': 'invoices/2024/01/test.pdf'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['status'] == 'FLAGGED'
        assert 'missing required fields' in result['error'].lower()
        assert result['flagged_for_manual_review'] is True
    
    @patch('index.s3_client')
    @patch('index.audit_logs_table')
    def test_missing_s3_key_parameter(self, mock_audit_table, mock_s3, mock_aws_services):
        """Test lambda handler fails gracefully when s3_key is missing."""
        event = {
            's3_bucket': 'test-bucket'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['status'] == 'FLAGGED'
        assert 'missing required fields' in result['error'].lower()
        assert result['flagged_for_manual_review'] is True
    
    @patch('index.s3_client')
    @patch('index.audit_logs_table')
    def test_s3_file_not_found(self, mock_audit_table, mock_s3, mock_aws_services):
        """Test lambda handler handles S3 NoSuchKey error."""
        # Mock S3 to raise NoSuchKey error
        error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
        mock_s3.get_object.side_effect = ClientError(error_response, 'GetObject')
        
        event = {
            's3_bucket': 'test-bucket',
            's3_key': 'invoices/2024/01/nonexistent.pdf'
        }
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['status'] == 'FLAGGED'
        assert 'not found' in result['error'].lower()
        assert result['flagged_for_manual_review'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
