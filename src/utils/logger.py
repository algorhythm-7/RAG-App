"""Logging configuration and utilities."""

import logging
import sys
import os
from datetime import datetime

try:
    import streamlit as st
    LOG_LEVEL = st.secrets.get("LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO")).upper()
except Exception:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()



def setup_logger(name: str) -> logging.Logger:
    """Set up logger with consistent formatting.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    return logger


def log_event(event_name: str, **kwargs):
    """Log a structured event with context.
    
    Args:
        event_name: Name of the event (e.g., "file_upload", "query_processed")
        **kwargs: Additional context (e.g., filename, status, duration)
    """
    logger = logging.getLogger(__name__)
    context = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"EVENT: {event_name} | {context}")


def log_error(component: str, error: Exception, context: str = ""):
    """Log an error with full details for debugging.
    
    Args:
        component: Component name (e.g., "document_parser")
        error: The exception
        context: Additional context about what was happening
    """
    logger = logging.getLogger(__name__)
    logger.exception(
        f"ERROR in {component} ({context}): {str(error)}",
        exc_info=True
    )
