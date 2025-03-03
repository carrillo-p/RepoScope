import pytest
from unittest.mock import MagicMock, patch
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from briefing_analyzer import ComplianceAnalyzer

import unittest.mock as mock

class TestComplianceAnalyzer:
    
    @patch('fitz.open')
    def test_extract_text_from_pdf_success(self, mock_open):
        # Setup mock PDF document with text
        mock_doc = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_page1.get_text.return_value = "Hello world"
        mock_page2.get_text.return_value = "This is a test"
        mock_doc.__iter__.return_value = [mock_page1, mock_page2]
        mock_open.return_value = mock_doc
        
        # Execute
        analyzer = ComplianceAnalyzer()
        result = analyzer.extract_text_from_pdf("dummy_path.pdf")
        
        # Verify
        assert result == "Hello world This is a test"
        mock_open.assert_called_once_with("dummy_path.pdf")
    
    @patch('fitz.open')
    def test_extract_text_from_pdf_exception(self, mock_open):
        # Setup mock to raise exception
        mock_open.side_effect = Exception("File not found")
        
        # Execute
        analyzer = ComplianceAnalyzer()
        result = analyzer.extract_text_from_pdf("nonexistent.pdf")
        
        # Verify
        assert result == ""
        mock_open.assert_called_once_with("nonexistent.pdf")
    
    @patch('fitz.open')
    def test_extract_text_from_pdf_logging_success(self, mock_open):
        # Setup mock PDF and logger
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = [MagicMock(get_text=lambda: "Test")]
        mock_open.return_value = mock_doc
        
        # Execute
        analyzer = ComplianceAnalyzer()
        analyzer.logger = MagicMock()
        analyzer.extract_text_from_pdf("test.pdf")
        
        # Verify logger was called correctly
        analyzer.logger.info.assert_called_once_with("Successfully extracted text from test.pdf")
        analyzer.logger.error.assert_not_called()
    
    @patch('fitz.open')
    def test_extract_text_from_pdf_logging_error(self, mock_open):
        # Setup exception and logger
        error_msg = "Access denied"
        mock_open.side_effect = Exception(error_msg)
        
        # Execute
        analyzer = ComplianceAnalyzer()
        analyzer.logger = MagicMock()
        analyzer.extract_text_from_pdf("restricted.pdf")
        
        # Verify error was logged
        analyzer.logger.error.assert_called_once()
        error_call_args = analyzer.logger.error.call_args[0][0]
        assert "Error extracting text from PDF" in error_call_args
        assert error_msg in error_call_args
    
    @patch('fitz.open')
    def test_extract_text_from_pdf_empty_document(self, mock_open):
        # Setup mock empty PDF
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = []
        mock_open.return_value = mock_doc
        
        # Execute
        analyzer = ComplianceAnalyzer()
        result = analyzer.extract_text_from_pdf("empty.pdf")
        
        # Verify
        assert result == ""