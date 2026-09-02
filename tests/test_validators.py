"""Tests for validation utilities."""

import pytest
from src.utils.validators import (
    ValidationError,
    validate_file_format,
    validate_file_size,
    validate_file,
    validate_query,
)


class TestValidateFileFormat:
    """Tests for file format validation."""
    
    def test_validate_pdf_format(self):
        """Test validating PDF format."""
        result = validate_file_format("manual.pdf")
        assert result == "pdf"
    
    def test_validate_image_formats(self):
        """Test validating various image formats."""
        assert validate_file_format("photo.png") == "image"
        assert validate_file_format("photo.jpg") == "image"
        assert validate_file_format("photo.jpeg") == "image"
    
    def test_validate_excel_formats(self):
        """Test validating Excel formats."""
        assert validate_file_format("data.xls") == "excel"
        assert validate_file_format("data.xlsx") == "excel"
    
    def test_validate_unsupported_format(self):
        """Test that unsupported formats raise error."""
        with pytest.raises(ValidationError):
            validate_file_format("file.xyz")
    
    def test_validate_case_insensitive(self):
        """Test that validation is case-insensitive."""
        result = validate_file_format("MANUAL.PDF")
        assert result == "pdf"
    
    def test_validate_no_extension(self):
        """Test file with no extension."""
        with pytest.raises(ValidationError):
            validate_file_format("document")


class TestValidateFileSize:
    """Tests for file size validation."""
    
    def test_validate_small_file(self):
        """Test validating small file."""
        small_bytes = b"x" * 1000  # 1KB
        size = validate_file_size(small_bytes)
        assert size == 1000
    
    def test_validate_large_file(self):
        """Test validating large but acceptable file."""
        large_bytes = b"x" * (10 * 1024 * 1024)  # 10MB
        size = validate_file_size(large_bytes)
        assert size == 10 * 1024 * 1024
    
    def test_validate_oversized_file(self):
        """Test that oversized files raise error."""
        # Create file larger than 50MB limit
        oversized_bytes = b"x" * (51 * 1024 * 1024)
        with pytest.raises(ValidationError):
            validate_file_size(oversized_bytes)
    
    def test_validate_empty_file(self):
        """Test validating empty file."""
        empty_bytes = b""
        size = validate_file_size(empty_bytes)
        assert size == 0


class TestValidateFile:
    """Tests for comprehensive file validation."""
    
    def test_validate_file_success(self):
        """Test successful file validation."""
        file_bytes = b"PDF content here"
        result = validate_file("manual.pdf", file_bytes)
        
        assert result["filename"] == "manual.pdf"
        assert result["file_format"] == "pdf"
        assert result["file_size"] == len(file_bytes)
        assert "file_hash" in result
    
    def test_validate_file_hash(self):
        """Test that file hash is generated."""
        file_bytes = b"content"
        result = validate_file("test.pdf", file_bytes)
        
        # Hash should be SHA-256 hex string
        assert len(result["file_hash"]) == 64
        assert all(c in "0123456789abcdef" for c in result["file_hash"])
    
    def test_validate_file_same_content_same_hash(self):
        """Test that same content produces same hash."""
        file_bytes = b"identical content"
        result1 = validate_file("file1.pdf", file_bytes)
        result2 = validate_file("file2.pdf", file_bytes)
        
        assert result1["file_hash"] == result2["file_hash"]
    
    def test_validate_file_invalid_format(self):
        """Test validation fails with invalid format."""
        with pytest.raises(ValidationError):
            validate_file("bad.xyz", b"content")
    
    def test_validate_file_too_large(self):
        """Test validation fails with oversized file."""
        oversized = b"x" * (51 * 1024 * 1024)
        with pytest.raises(ValidationError):
            validate_file("large.pdf", oversized)


class TestValidateQuery:
    """Tests for query validation."""
    
    def test_validate_valid_query(self):
        """Test validating valid query."""
        query = "What is tire pressure?"
        result = validate_query(query)
        assert result == query
    
    def test_validate_query_stripped(self):
        """Test that query is stripped of whitespace."""
        query = "  test query  "
        result = validate_query(query)
        assert result == "test query"
    
    def test_validate_empty_query(self):
        """Test that empty query raises error."""
        with pytest.raises(ValidationError):
            validate_query("")
    
    def test_validate_whitespace_only_query(self):
        """Test that whitespace-only query raises error."""
        with pytest.raises(ValidationError):
            validate_query("   ")
    
    def test_validate_long_query(self):
        """Test validating long query."""
        long_query = "What is the recommended tire pressure for different speeds?"
        result = validate_query(long_query)
        assert result == long_query


class TestValidationErrorException:
    """Tests for ValidationError exception."""
    
    def test_validation_error_message(self):
        """Test that ValidationError includes message."""
        try:
            raise ValidationError("Test error message")
        except ValidationError as e:
            assert str(e) == "Test error message"
    
    def test_validation_error_inheritance(self):
        """Test that ValidationError is an Exception."""
        error = ValidationError("test")
        assert isinstance(error, Exception)
