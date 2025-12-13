# python
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Optional, Callable
import logging
from .models import PIProfile
from .config import UniversityConfig
from .extractors import extract_field
from .transforms import apply_transform
from .validators import validate_field

logger = logging.getLogger(__name__)

def parse_faculty_list(html: str, config: UniversityConfig) -> List[PIProfile]:
    soup = BeautifulSoup(html, "html.parser")
    
    # Check if using new format
    if config.is_new_format and config.raw_config:
        return _parse_faculty_list_new_format(soup, config)
    else:
        return _parse_faculty_list_old_format(soup, config)


def _parse_faculty_list_old_format(soup: BeautifulSoup, config: UniversityConfig) -> List[PIProfile]:
    """Parse using old format (backward compatibility)."""
    items = soup.select(config.item_selector)
    profiles: List[PIProfile] = []

    for item in items:
        name_el = item.select_one(config.name_selector)
        if not name_el:
            continue
        full_name = name_el.get_text(strip=True)
        if not full_name:
            continue

        title: Optional[str] = None
        if getattr(config, "title_selector", None):
            title_el = item.select_one(config.title_selector)
            if title_el:
                title = title_el.get_text(strip=True) or None

        email: Optional[str] = None
        if getattr(config, "email_selector", None):
            email_el = item.select_one(config.email_selector)
            if email_el and email_el.has_attr("href"):
                href = email_el["href"]
                if href.startswith("mailto:"):
                    email = href.replace("mailto:", "").strip()

        profile_url = config.faculty_list_url
        if getattr(config, "profile_link_selector", None):
            link_el = item.select_one(config.profile_link_selector)
            if link_el and link_el.has_attr("href"):
                profile_url = urljoin(config.faculty_list_url, link_el["href"])

        personal_website_url: Optional[str] = None
        if getattr(config, "personal_website_selector", None):
            pw_el = item.select_one(config.personal_website_selector)
            if pw_el and pw_el.has_attr("href"):
                personal_website_url = urljoin(config.faculty_list_url, pw_el["href"])

        raw_research_text: Optional[str] = None
        if getattr(config, "research_text_selector", None):
            rt_el = item.select_one(config.research_text_selector)
            if rt_el:
                text = rt_el.get_text(" ", strip=True)
                raw_research_text = text or None

        profiles.append(
            PIProfile(
                full_name=full_name,
                title=title,
                department=config.department,
                university=config.name,
                email=email,
                profile_url=profile_url,
                personal_website_url=personal_website_url,
                raw_research_text=raw_research_text,
                source_university_id=config.id,
            )
        )
    return profiles


def _parse_faculty_list_new_format(soup: BeautifulSoup, config: UniversityConfig) -> List[PIProfile]:
    """Parse using new extractor format."""
    raw_config = config.raw_config
    
    # Get list item selectors
    list_item_config = raw_config.get("list_item", {})
    selectors = list_item_config.get("selectors", [config.item_selector])
    if not isinstance(selectors, list):
        selectors = [selectors]
    
    # Try each selector until we find items
    items = []
    for selector in selectors:
        items = soup.select(selector)
        if items:
            logger.debug(f"Found {len(items)} items using selector: {selector}")
            break
    
    if not items:
        logger.warning(f"No items found with any selector: {selectors}")
        return []
    
    profiles: List[PIProfile] = []
    fields_config = raw_config.get("fields", {})
    
    for idx, item in enumerate(items):
        # Extract fields using new extractor system
        extracted_data = {}
        
        for field_name, field_config in fields_config.items():
            value = extract_field(item, field_config, config.faculty_list_url)
            
            # Apply field-level transformations if specified
            if value and "transform" in field_config:
                transform = field_config["transform"]
                if isinstance(transform, str):
                    value = apply_transform(value, transform, config.faculty_list_url)
                elif isinstance(transform, list):
                    for t in transform:
                        value = apply_transform(value, t, config.faculty_list_url)
            
            # Validate field
            validate_field(field_name, value, field_config, log_warnings=True)
            
            extracted_data[field_name] = value
        
        # full_name is required
        full_name = extracted_data.get("full_name")
        if not full_name:
            logger.debug(f"Skipping item {idx}: no full_name found")
            continue
        
        # Map extracted fields to PIProfile
        profile_url = extracted_data.get("profile_url", config.faculty_list_url)
        
        # Ensure profile_url is absolute
        if profile_url and not profile_url.startswith("http"):
            profile_url = urljoin(config.faculty_list_url, profile_url)
        
        profiles.append(
            PIProfile(
                full_name=full_name,
                title=extracted_data.get("title"),
                department=config.department,
                university=config.name,
                email=extracted_data.get("email"),
                profile_url=profile_url,
                personal_website_url=extracted_data.get("personal_website_url"),
                raw_research_text=extracted_data.get("raw_research_text"),
                source_university_id=config.id,
            )
        )
    
    logger.info(f"Extracted {len(profiles)} profiles from {len(items)} items")
    return profiles

def parse_profile_detail(html: str, base_url: str, config: UniversityConfig) -> tuple[Optional[str], Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")
    
    # Check if using new format with profile_page config
    if config.is_new_format and config.raw_config:
        profile_page_config = config.raw_config.get("profile_page", {})
        if profile_page_config.get("enabled", False):
            return _parse_profile_detail_new_format(soup, base_url, config)
    
    # Fall back to old format
    personal_website_url: Optional[str] = None
    if getattr(config, "personal_website_selector", None):
        pw_el = soup.select_one(config.personal_website_selector)
        if pw_el and pw_el.has_attr("href"):
            personal_website_url = urljoin(base_url, pw_el["href"])

    raw_research_text: Optional[str] = None
    if getattr(config, "research_text_selector", None):
        rt_el = soup.select_one(config.research_text_selector)
        if rt_el:
            text = rt_el.get_text(" ", strip=True)
            raw_research_text = text or None

    return personal_website_url, raw_research_text


def _parse_profile_detail_new_format(soup: BeautifulSoup, base_url: str, config: UniversityConfig) -> tuple[Optional[str], Optional[str]]:
    """Parse profile detail page using new format."""
    profile_page_config = config.raw_config.get("profile_page", {})
    fields_config = profile_page_config.get("fields", {})
    
    personal_website_url = None
    raw_research_text = None
    
    # Extract personal_website_url
    if "personal_website_url" in fields_config:
        personal_website_url = extract_field(soup, fields_config["personal_website_url"], base_url)
        if personal_website_url:
            # Apply transform
            field_config = fields_config["personal_website_url"]
            if "transform" in field_config:
                transform = field_config["transform"]
                personal_website_url = apply_transform(personal_website_url, transform, base_url)
            # Ensure absolute URL
            if personal_website_url and not personal_website_url.startswith("http"):
                personal_website_url = urljoin(base_url, personal_website_url)
    
    # Extract raw_research_text
    if "raw_research_text" in fields_config:
        raw_research_text = extract_field(soup, fields_config["raw_research_text"], base_url)
    
    return personal_website_url, raw_research_text

def parse_faculty_list_then_details(
        list_html: str,
        config: UniversityConfig,
        fetch_html: Callable[[str], str],
) -> List[PIProfile]:
    profiles = parse_faculty_list(list_html, config)

    for p in profiles:
        # Only fetch detail page if we have a distinct profile URL and missing fields
        should_fetch = (
                p.profile_url
                and p.profile_url != config.faculty_list_url
                and (p.personal_website_url is None or p.raw_research_text is None)
        )
        if not should_fetch:
            continue

        try:
            detail_html = fetch_html(p.profile_url)
        except Exception:
            continue  # skip on fetch errors

        pw_url, research_text = parse_profile_detail(detail_html, p.profile_url, config)

        # Only overwrite if the detail page actually provided values
        if p.personal_website_url is None and pw_url:
            p.personal_website_url = pw_url
        if p.raw_research_text is None and research_text:
            p.raw_research_text = research_text

    return profiles
