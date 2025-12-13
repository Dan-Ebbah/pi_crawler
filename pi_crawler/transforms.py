"""
Field transformations for extracted data.
"""
from typing import Optional
from urllib.parse import urljoin
import re


def strip_mailto(value: Optional[str]) -> Optional[str]:
    """Remove 'mailto:' prefix from email links."""
    if not value:
        return None
    if value.startswith("mailto:"):
        return value.replace("mailto:", "").strip()
    return value


def absolute_url(value: Optional[str], base_url: Optional[str] = None) -> Optional[str]:
    """Convert relative URLs to absolute URLs."""
    if not value or not base_url:
        return value
    return urljoin(base_url, value)


def strip_whitespace(value: Optional[str]) -> Optional[str]:
    """Strip leading and trailing whitespace."""
    if not value:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def normalize_whitespace(value: Optional[str]) -> Optional[str]:
    """Normalize internal whitespace to single spaces."""
    if not value:
        return None
    normalized = re.sub(r'\s+', ' ', value.strip())
    return normalized if normalized else None


def lowercase(value: Optional[str]) -> Optional[str]:
    """Convert to lowercase."""
    if not value:
        return None
    return value.lower()


def uppercase(value: Optional[str]) -> Optional[str]:
    """Convert to uppercase."""
    if not value:
        return None
    return value.upper()


# Registry of available transforms
TRANSFORMS = {
    "strip_mailto": strip_mailto,
    "absolute_url": absolute_url,
    "strip_whitespace": strip_whitespace,
    "normalize_whitespace": normalize_whitespace,
    "lowercase": lowercase,
    "uppercase": uppercase,
}


def apply_transform(
    value: Optional[str],
    transform_name: str,
    base_url: Optional[str] = None
) -> Optional[str]:
    """
    Apply a named transform to a value.
    
    Args:
        value: Value to transform
        transform_name: Name of the transform to apply
        base_url: Base URL for URL transformations
        
    Returns:
        Transformed value or original value if transform not found
    """
    if not value:
        return None
    
    transform_func = TRANSFORMS.get(transform_name)
    if not transform_func:
        return value
    
    # Special handling for transforms that need base_url
    if transform_name == "absolute_url":
        return transform_func(value, base_url)
    
    return transform_func(value)
