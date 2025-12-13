"""
Data validation utilities for extracted fields.
"""
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def validate_pattern(value: Optional[str], pattern: str) -> bool:
    """
    Validate value against a regex pattern.
    
    Args:
        value: Value to validate
        pattern: Regular expression pattern
        
    Returns:
        True if value matches pattern, False otherwise
    """
    if not value:
        return False
    
    try:
        return bool(re.match(pattern, value))
    except re.error as e:
        logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        return False


def validate_email(value: Optional[str]) -> bool:
    """Validate email address format."""
    if not value:
        return False
    
    # Basic email pattern
    pattern = r'^[\w.-]+@[\w.-]+\.\w+$'
    return validate_pattern(value, pattern)


def validate_url(value: Optional[str]) -> bool:
    """Validate URL format."""
    if not value:
        return False
    
    # Basic URL pattern
    pattern = r'^https?://.+'
    return validate_pattern(value, pattern)


def validate_required(value: Optional[str]) -> bool:
    """Validate that value is not None or empty."""
    return bool(value and value.strip())


def validate_field(
    field_name: str,
    value: Optional[str],
    field_config: dict,
    log_warnings: bool = True
) -> bool:
    """
    Validate a field value according to its configuration.
    
    Args:
        field_name: Name of the field
        value: Field value to validate
        field_config: Field configuration dictionary
        log_warnings: Whether to log validation warnings
        
    Returns:
        True if valid, False otherwise
    """
    # Check if field is required
    is_required = field_config.get("required", False)
    if is_required and not validate_required(value):
        if log_warnings:
            logger.warning(f"Required field '{field_name}' is missing or empty")
        return False
    
    # If value is None or empty and not required, it's valid
    if not value:
        return True
    
    # Check regex validation pattern if provided
    validation_pattern = field_config.get("validation")
    if validation_pattern:
        is_valid = validate_pattern(value, validation_pattern)
        if not is_valid and log_warnings:
            logger.warning(
                f"Field '{field_name}' value '{value}' does not match "
                f"validation pattern '{validation_pattern}'"
            )
        return is_valid
    
    return True
