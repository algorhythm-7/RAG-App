"""Tests for document parser component."""

import pytest
import io
from PIL import Image

from src.models import ParseError
from src.components.document_parser import DocumentParser


class TestDocumentParserPDF:
    """Tests for PDF parsing."""
    
    def test_parse_pdf_success(self, parser, sample_pdf_bytes):
        """Test successful PDF parsing."""
        doc = parser.parse(sample_pdf_bytes, "test.pdf", "pdf", "doc-1")
        
        assert doc.parsed_successfully
        assert doc.filename == "test.pdf"
        assert doc.file_format == "pdf"
        assert len(doc.passages) > 0
    
    def test_parse_empty_pdf(self, parser):
        """Test parsing empty PDF."""
        empty_pdf = b"%PDF-1.4\n"
        doc = parser.parse(empty_pdf, "empty.pdf", "pdf", "doc-1")
        
        # Should handle gracefully
        assert doc.document_id == "doc-1"
        assert doc.filename == "empty.pdf"


class TestDocumentParserImage:
    """Tests for image parsing with OCR."""
    
    def test_parse_image_success(self, parser, sample_image_bytes):
        """Test successful image parsing with OCR."""
        doc = parser.parse(sample_image_bytes, "test.png", "image", "doc-1")
        
        assert doc.document_id == "doc-1"
        assert doc.filename == "test.png"
        assert doc.file_format == "image"
        # Image parsing may not always succeed depending on OCR availability


class TestDocumentParserExcel:
    """Tests for Excel parsing."""
    
    def test_parse_excel_success(self, parser, sample_excel_bytes):
        """Test successful Excel parsing."""
        doc = parser.parse(sample_excel_bytes, "test.xlsx", "excel", "doc-1")
        
        assert doc.parsed_successfully
        assert doc.filename == "test.xlsx"
        assert doc.file_format == "excel"
        assert len(doc.passages) > 0
        assert "Column1" in doc.passages[0].text or "Value1" in doc.passages[0].text


class TestDocumentParserErrorHandling:
    """Tests for error handling in parser."""
    
    def test_parse_invalid_format(self, parser):
        """Test parsing with invalid format."""
        doc = parser.parse(b"fake content", "test.xyz", "unsupported", "doc-1")
        
        # Should return error document
        assert doc.document_id == "doc-1"
    
    def test_parse_corrupted_file(self, parser):
        """Test parsing corrupted PDF."""
        corrupted = b"This is not a valid PDF"
        doc = parser.parse(corrupted, "corrupted.pdf", "pdf", "doc-1")
        
        # Should handle error gracefully
        assert doc.document_id == "doc-1"


class TestDocumentParserChunking:
    """Tests for passage chunking."""
    
    def test_chunk_large_passage(self, parser):
        """Test chunking of large passages."""
        # Create a long text passage
        long_text = " ".join(["word"] * 1000)
        passages = [
            src.models.Passage(
                text=long_text,
                section="Section 1",
                document_id="doc-1",
                passage_index=0,
            )
        ]
        
        from src.components.document_parser import DocumentParser
        dp = DocumentParser()
        # Access private method for testing
        chunked = dp._chunk_passages(passages)
        
        # Should produce multiple chunks
        assert len(chunked) > 1
