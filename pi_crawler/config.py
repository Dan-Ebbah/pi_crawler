import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any

CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"

class ConfigValidationError(Exception):
    """Raised when a configuration file has validation errors."""
    def __init__(self, errors: List[str], config_path: str):
        self.errors = errors
        self.config_path = config_path
        error_list = "\n  - ".join(errors)
        super().__init__(f"Configuration validation failed for '{config_path}':\n  - {error_list}")


@dataclass
class PaginationConfig:
    """Configuration for handling paginated faculty lists."""
    enabled: bool = False
    type: str = "page_param"  # "page_param", "offset_param", "next_link", "load_more"
    param_name: str = "page"  # URL parameter name for page/offset
    start_value: int = 1  # Starting page/offset value
    increment: int = 1  # How much to increment each iteration
    max_pages: int = 50  # Safety limit
    next_link_selector: Optional[str] = None  # CSS selector for "next" link
    load_more_selector: Optional[str] = None  # CSS selector for "load more" button
    stop_when_empty: bool = True  # Stop when no items found


@dataclass
class UniversityConfig:
    id: str
    name: str
    department: str
    faculty_list_url: str
    item_selector: str
    name_selector: str
    research_heading_keywords: List[str]
    request_delay_seconds: float
    # Optional selectors
    title_selector: Optional[str] = None
    email_selector: Optional[str] = None
    profile_link_selector: Optional[str] = None
    personal_website_selector: Optional[str] = None
    research_text_selector: Optional[str] = None
    image_selector: Optional[str] = None
    # Pagination support
    pagination: Optional[PaginationConfig] = None
    # Additional flexibility
    base_url: Optional[str] = None  # Base URL for relative links (defaults to faculty_list_url domain)
    custom_headers: Optional[Dict[str, str]] = None  # Additional HTTP headers
    # Alternative selectors for different page layouts
    alt_name_selectors: List[str] = field(default_factory=list)
    alt_email_selectors: List[str] = field(default_factory=list)
    alt_profile_link_selectors: List[str] = field(default_factory=list)
    # Enrichment settings
    enrichment_enabled: bool = True
    personal_website_keywords: List[str] = field(default_factory=lambda: ["website", "homepage", "personal", "home page"])
    research_section_tags: List[str] = field(default_factory=lambda: ["h1", "h2", "h3", "h4", "strong", "b"])

    @classmethod
    def from_json_file(cls, path: Path) -> "UniversityConfig":
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            raise ConfigValidationError(
                [f"Invalid JSON syntax: {e}"],
                str(path)
            )

        # Validate before creating
        errors = cls._validate_config_data(data, str(path))
        if errors:
            raise ConfigValidationError(errors, str(path))

        # Handle pagination config if present
        if "pagination" in data and data["pagination"]:
            data["pagination"] = PaginationConfig(**data["pagination"])

        # Filter to only known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}

        return cls(**filtered_data)

    @staticmethod
    def _validate_config_data(data: Dict[str, Any], path: str) -> List[str]:
        """Validate configuration data and return list of errors."""
        errors = []

        # Required fields
        required_fields = [
            ("id", str, "Unique identifier for this university config"),
            ("name", str, "University display name"),
            ("department", str, "Department name"),
            ("faculty_list_url", str, "URL of the faculty list page"),
            ("item_selector", str, "CSS selector for individual faculty items"),
            ("name_selector", str, "CSS selector for faculty names within each item"),
            ("research_heading_keywords", list, "List of keywords to identify research sections"),
            ("request_delay_seconds", (int, float), "Delay between requests in seconds"),
        ]

        for field_name, field_type, description in required_fields:
            if field_name not in data:
                errors.append(f"Missing required field '{field_name}': {description}")
            elif not isinstance(data[field_name], field_type):
                type_name = field_type.__name__ if isinstance(field_type, type) else str(field_type)
                errors.append(f"Field '{field_name}' must be {type_name}, got {type(data[field_name]).__name__}")

        # Validate URL format
        if "faculty_list_url" in data and isinstance(data["faculty_list_url"], str):
            url = data["faculty_list_url"]
            if not url.startswith(("http://", "https://")):
                errors.append(f"Field 'faculty_list_url' must be a valid HTTP/HTTPS URL, got: {url}")

        # Validate CSS selectors (basic check)
        selector_fields = [
            "item_selector", "name_selector", "title_selector",
            "email_selector", "profile_link_selector",
            "personal_website_selector", "research_text_selector", "image_selector"
        ]
        for field_name in selector_fields:
            if field_name in data and data[field_name]:
                selector = data[field_name]
                if not isinstance(selector, str):
                    errors.append(f"Field '{field_name}' must be a string CSS selector")
                elif len(selector.strip()) == 0:
                    errors.append(f"Field '{field_name}' cannot be empty")

        # Validate request_delay_seconds
        if "request_delay_seconds" in data:
            delay = data["request_delay_seconds"]
            if isinstance(delay, (int, float)):
                if delay < 0:
                    errors.append("Field 'request_delay_seconds' must be non-negative")
                elif delay < 0.5:
                    errors.append("Warning: 'request_delay_seconds' < 0.5 may cause rate limiting")

        # Validate research_heading_keywords
        if "research_heading_keywords" in data:
            keywords = data["research_heading_keywords"]
            if isinstance(keywords, list):
                if len(keywords) == 0:
                    errors.append("Field 'research_heading_keywords' should have at least one keyword")
                for i, kw in enumerate(keywords):
                    if not isinstance(kw, str):
                        errors.append(f"research_heading_keywords[{i}] must be a string")

        # Validate pagination config if present
        if "pagination" in data and data["pagination"]:
            pag = data["pagination"]
            if not isinstance(pag, dict):
                errors.append("Field 'pagination' must be an object")
            else:
                valid_types = ["page_param", "offset_param", "next_link", "load_more"]
                if "type" in pag and pag["type"] not in valid_types:
                    errors.append(f"pagination.type must be one of: {valid_types}")
                if pag.get("type") == "next_link" and not pag.get("next_link_selector"):
                    errors.append("pagination.next_link_selector is required when type is 'next_link'")
                if pag.get("type") == "load_more" and not pag.get("load_more_selector"):
                    errors.append("pagination.load_more_selector is required when type is 'load_more'")

        return errors

    def get_selector_with_fallbacks(self, field: str) -> List[str]:
        """Get primary selector plus any alternatives for a field."""
        primary = getattr(self, field, None)
        alt_field = f"alt_{field}s"
        alternatives = getattr(self, alt_field, [])

        selectors = []
        if primary:
            selectors.append(primary)
        selectors.extend(alternatives)
        return selectors


def load_university_config(univ_id: str) -> UniversityConfig:
    """Load a university configuration by ID.

    Args:
        univ_id: The university config ID (filename without .json extension)

    Returns:
        UniversityConfig object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ConfigValidationError: If config file has validation errors
    """
    path = CONFIG_DIR / f"{univ_id}.json"
    if not path.exists():
        available = list_available_configs()
        if available:
            available_list = ", ".join(available)
            raise FileNotFoundError(
                f"Configuration file for university '{univ_id}' not found.\n"
                f"Available configs: {available_list}\n"
                f"Expected path: {path}"
            )
        else:
            raise FileNotFoundError(
                f"Configuration file for university '{univ_id}' not found.\n"
                f"No configuration files found in {CONFIG_DIR}\n"
                f"Create a config file at: {path}"
            )
    return UniversityConfig.from_json_file(path)


def list_available_configs() -> List[str]:
    """List all available university configuration IDs."""
    if not CONFIG_DIR.exists():
        return []
    return [p.stem for p in CONFIG_DIR.glob("*.json")]


def validate_config_file(path: Path) -> List[str]:
    """Validate a config file and return list of errors (empty if valid)."""
    try:
        UniversityConfig.from_json_file(path)
        return []
    except ConfigValidationError as e:
        return e.errors
    except Exception as e:
        return [str(e)]