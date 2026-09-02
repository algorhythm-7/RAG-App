"""Tests for error handler component."""

import pytest
from src.components.error_handler import ErrorResponse, ErrorHandler
from src.utils.constants import ERROR_CODES


class TestErrorResponse:
    """Tests for ErrorResponse class."""
    
    def test_error_response_creation(self):
        """Test creating an error response."""
        error = ErrorResponse(
            error_code="FILE_TOO_LARGE",
            context="test.pdf"
        )
        
        assert error.status == "error"
        assert error.error_code == "FILE_TOO_LARGE"
        assert error.context == "test.pdf"
        assert error.message == ERROR_CODES["FILE_TOO_LARGE"]
    
    def test_error_response_custom_message(self):
        """Test error response with custom message."""
        error = ErrorResponse(
            error_code="PARSE_FAILED",
            message="Custom error message",
            context="file.pdf"
        )
        
        assert error.message == "Custom error message"
        assert error.error_code == "PARSE_FAILED"
    
    def test_error_response_to_dict(self):
        """Test converting error response to dict."""
        error = ErrorResponse("UNSUPPORTED_FORMAT")
        error_dict = error.to_dict()
        
        assert error_dict["status"] == "error"
        assert error_dict["error_code"] == "UNSUPPORTED_FORMAT"
        assert "message" in error_dict
    
    def test_error_response_unknown_code(self):
        """Test error response with unknown code."""
        error = ErrorResponse("UNKNOWN_CODE")
        
        # Should use default message
        assert error.message == "An error occurred."


class TestErrorHandlerExceptionHandling:
    """Tests for handling exceptions."""
    
    def test_handle_exception_generic(self):
        """Test handling generic exception."""
        error = Exception("Test error")
        response = ErrorHandler.handle_exception(error, "test_component")
        
        assert response.status == "error"
        assert response.error_code == "INTERNAL_ERROR"
        assert response.context == ""
    
    def test_handle_exception_with_context(self):
        """Test handling exception with context."""
        error = Exception("File too large")
        response = ErrorHandler.handle_exception(
            error,
            "upload_handler",
            context="test.pdf"
        )
        
        assert response.status == "error"
        assert response.context == "test.pdf"
    
    def test_handle_exception_format_error(self):
        """Test handling format-related exception."""
        error = Exception("Unsupported format: xyz")
        response = ErrorHandler.handle_exception(error, "parser")
        
        assert response.error_code == "UNSUPPORTED_FORMAT"
    
    def test_handle_exception_size_error(self):
        """Test handling size-related exception."""
        error = Exception("File size exceeds limit")
        response = ErrorHandler.handle_exception(error, "validator")
        
        assert response.error_code == "FILE_TOO_LARGE"
    
    def test_handle_exception_parse_error(self):
        """Test handling parse-related exception."""
        error = Exception("Failed to parse file")
        response = ErrorHandler.handle_exception(error, "parser")
        
        assert response.error_code == "PARSE_FAILED"
    
    def test_handle_exception_timeout_error(self):
        """Test handling timeout exception."""
        error = TimeoutError("Query timed out")
        response = ErrorHandler.handle_exception(error, "query_processor")
        
        assert response.error_code == "QUERY_TIMEOUT"


class TestErrorHandlerValidationError:
    """Tests for validation error handling."""
    
    def test_validation_error_file_too_large(self):
        """Test validation error for file size."""
        response = ErrorHandler.validation_error("FILE_TOO_LARGE")
        
        assert response.status == "error"
        assert response.error_code == "FILE_TOO_LARGE"
        assert response.message == ERROR_CODES["FILE_TOO_LARGE"]
    
    def test_validation_error_duplicate(self):
        """Test validation error for duplicate file."""
        response = ErrorHandler.validation_error(
            "DUPLICATE_FILE",
            context="manual.pdf"
        )
        
        assert response.error_code == "DUPLICATE_FILE"
        assert response.context == "manual.pdf"
    
    def test_validation_error_unsupported_format(self):
        """Test validation error for unsupported format."""
        response = ErrorHandler.validation_error("UNSUPPORTED_FORMAT")
        
        assert response.error_code == "UNSUPPORTED_FORMAT"


class TestErrorHandlerMessageSafety:
    """Tests that error messages don't expose internal details."""
    
    def test_error_no_stack_trace(self):
        """Test that error messages don't include stack traces."""
        error = Exception("Stack trace details")
        response = ErrorHandler.handle_exception(error, "component")
        
        # Message from ERROR_CODES, not raw exception
        assert "Traceback" not in response.message
    
    def test_error_no_api_keys(self):
        """Test that error messages don't expose API keys."""
        error = Exception("API_KEY=sk-123456789")
        response = ErrorHandler.handle_exception(error, "component")
        
        # Message should be generic
        assert "sk-" not in response.message
    
    def test_error_no_file_paths(self):
        """Test that error messages don't expose file paths."""
        error = Exception("/usr/home/secret/file.pdf")
        response = ErrorHandler.handle_exception(error, "component")
        
        # Message should be generic
        assert "/usr/home" not in response.message


class TestErrorCodeMapping:
    """Tests for error code mapping."""
    
    def test_all_error_codes_have_messages(self):
        """Test that all error codes have messages."""
        for code in ["FILE_TOO_LARGE", "UNSUPPORTED_FORMAT", "PARSE_FAILED", 
                     "DUPLICATE_FILE", "QUERY_TIMEOUT", "NO_RESULTS", 
                     "INTERNAL_ERROR", "OUT_OF_SCOPE", "NO_DOCUMENTS"]:
            assert code in ERROR_CODES
            assert len(ERROR_CODES[code]) > 0
