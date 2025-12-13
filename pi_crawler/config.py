import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"
TEMPLATE_DIR = CONFIG_DIR / "templates"


@dataclass
class UniversityConfig:
    id: str
    name: str
    department: str
    faculty_list_url: str
    item_selector: str
    name_selector: str
    title_selector: Optional[str]
    email_selector: Optional[str]
    profile_link_selector: Optional[str]
    research_heading_keywords: List[str]
    request_delay_seconds: float
    
    # New fields for enhanced config
    raw_config: Optional[Dict[str, Any]] = None  # Store raw config for new format
    is_new_format: bool = False

    @classmethod
    def from_json_file(cls, path: Path) -> "UniversityConfig":
        data = json.loads(path.read_text())
        
        # Check if this is new format (has "fields" or "list_item" keys)
        is_new_format = "fields" in data or "list_item" in data
        
        if is_new_format:
            return cls._from_new_format(data)
        else:
            return cls._from_old_format(data)
    
    @classmethod
    def _from_old_format(cls, data: Dict[str, Any]) -> "UniversityConfig":
        """Create config from old format (backward compatibility)."""
        return cls(**data)
    
    @classmethod
    def _from_new_format(cls, data: Dict[str, Any]) -> "UniversityConfig":
        """Create config from new enhanced format."""
        # Apply template inheritance if specified
        if "template" in data:
            data = _apply_template(data)
        
        # Map new format to old format fields for backward compatibility
        old_format = {
            "id": data.get("id"),
            "name": data.get("name"),
            "department": data.get("department"),
            "faculty_list_url": data.get("faculty_list_url"),
            "request_delay_seconds": data.get("request_delay_seconds", 1.0),
            "research_heading_keywords": data.get("research_heading_keywords", ["research", "interests"]),
        }
        
        # Extract selectors from list_item if present
        list_item = data.get("list_item", {})
        if isinstance(list_item, dict):
            selectors = list_item.get("selectors", [])
            if selectors:
                old_format["item_selector"] = selectors[0] if isinstance(selectors, list) else selectors
            else:
                old_format["item_selector"] = list_item.get("selector", ".item")
        else:
            old_format["item_selector"] = ".item"
        
        # Extract field selectors from fields config
        fields = data.get("fields", {})
        old_format["name_selector"] = _get_first_css_selector(fields.get("full_name", {}))
        old_format["title_selector"] = _get_first_css_selector(fields.get("title", {}))
        old_format["email_selector"] = _get_first_css_selector(fields.get("email", {}))
        old_format["profile_link_selector"] = _get_first_css_selector(fields.get("profile_url", {}))
        
        # Create instance with both formats
        instance = cls(**old_format)
        instance.raw_config = data
        instance.is_new_format = True
        
        return instance


def _get_first_css_selector(field_config: Dict[str, Any]) -> Optional[str]:
    """Extract the first CSS selector from a field config."""
    if not field_config:
        return None
    
    extractors = field_config.get("extractors", [])
    for extractor in extractors:
        if extractor.get("strategy") == "css":
            return extractor.get("selector")
    
    return None


def _apply_template(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply template inheritance to config."""
    template_name = config.get("template")
    if not template_name:
        return config
    
    template_path = TEMPLATE_DIR / f"{template_name}.json"
    if not template_path.exists():
        logger.warning(f"Template '{template_name}' not found at {template_path}")
        return config
    
    try:
        template_data = json.loads(template_path.read_text())
        # Merge template with config (config overrides template)
        merged = _deep_merge(template_data, config)
        # Remove template key from merged config
        merged.pop("template", None)
        return merged
    except Exception as e:
        logger.warning(f"Failed to load template '{template_name}': {e}")
        return config


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def load_university_config(univ_id: str) -> UniversityConfig:
    path = CONFIG_DIR / f"{univ_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Configuration file for university '{univ_id}' not found.")
    return UniversityConfig.from_json_file(path)