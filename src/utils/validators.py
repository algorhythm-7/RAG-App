"""Input validation utilities."""

import hashlib
from src.utils.constants import SUPPORTED_FORMATS, MAX_FILE_SIZE_BYTES, ERROR_CODES


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_file_format(filename: str) -> str:
    """Validate file format is supported.
    
    Args:
        filename: Name of the file (e.g., "manual.pdf")
    
    Returns:
        File format type (e.g., "pdf", "image", "excel")
    
    Raises:
        ValidationError: If format is not supported.
    """
    ext = None
    for supported_ext in SUPPORTED_FORMATS.keys():
        if filename.lower().endswith(supported_ext):
            ext = supported_ext
            break
    
    if ext is None:
        raise ValidationError(ERROR_CODES["UNSUPPORTED_FORMAT"])
    
    return SUPPORTED_FORMATS[ext]


def validate_file_size(file_bytes: bytes) -> int:
    """Validate file size is within limit.
    
    Args:
        file_bytes: Raw file bytes
    
    Returns:
        File size in bytes
    
    Raises:
        ValidationError: If file is too large.
    """
    file_size = len(file_bytes)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(ERROR_CODES["FILE_TOO_LARGE"])
    return file_size


def validate_file(filename: str, file_bytes: bytes) -> dict:
    """Validate both format and size.
    
    Args:
        filename: Name of the file
        file_bytes: Raw file bytes
    
    Returns:
        Dictionary with filename, file_format, file_size, file_hash
    
    Raises:
        ValidationError: If validation fails.
    """
    file_format = validate_file_format(filename)
    file_size = validate_file_size(file_bytes)
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    return {
        "filename": filename,
        "file_format": file_format,
        "file_size": file_size,
        "file_hash": file_hash,
    }


def validate_query(query_text: str) -> str:
    """Validate query text is not empty.
    
    Args:
        query_text: User's query
    
    Returns:
        Cleaned query text
    
    Raises:
        ValidationError: If query is empty.
    """
    if not query_text or not query_text.strip():
        raise ValidationError("Query cannot be empty.")
    return query_text.strip()
