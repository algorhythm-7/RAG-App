"""Error handling and logging utilities."""

from typing import Dict, Optional
from src.utils.logger import log_error
from src.utils.constants import ERROR_CODES


class ErrorResponse:
    """Formatted error response for users.
    
    Attributes:
        status: Always "error".
        error_code: Machine-readable error code.
        message: Human-readable error message.
        context: Optional context for debugging.
    """
    
    def __init__(
        self,
        error_code: str,
        message: Optional[str] = None,
        context: str = ""
    ):
        self.status = "error"
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "An error occurred.")
        self.context = context
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for Streamlit display."""
        return {
            "status": self.status,
            "error_code": self.error_code,
            "message": self.message,
        }


class ErrorHandler:
    """Handle errors across the application."""
    
    @staticmethod
    def handle_exception(
        error: Exception,
        component: str,
        context: str = ""
    ) -> ErrorResponse:
        """Handle an exception and return user-friendly error.
        
        Args:
            error: The exception that occurred.
            component: Name of the component (for logging).
            context: Additional context about what was happening.
        
        Returns:
            ErrorResponse formatted for display to user.
        """
        # Log the full error for debugging
        log_error(component, error, context)
        
        # Map specific exceptions to error codes
        error_code = "INTERNAL_ERROR"
        
        if "format" in str(error).lower():
            error_code = "UNSUPPORTED_FORMAT"
        elif "size" in str(error).lower():
            error_code = "FILE_TOO_LARGE"
        elif "duplicate" in str(error).lower():
            error_code = "DUPLICATE_FILE"
        elif "parse" in str(error).lower():
            error_code = "PARSE_FAILED"
        elif "timeout" in str(error).lower():
            error_code = "QUERY_TIMEOUT"
        
        return ErrorResponse(
            error_code=error_code,
            context=context
        )
    
    @staticmethod
    def validation_error(error_code: str, context: str = "") -> ErrorResponse:
        """Handle a validation error.
        
        Args:
            error_code: The error code (e.g., "FILE_TOO_LARGE").
            context: Optional additional context.
        
        Returns:
            ErrorResponse formatted for display to user.
        """
        return ErrorResponse(
            error_code=error_code,
            context=context
        )
