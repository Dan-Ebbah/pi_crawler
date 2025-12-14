"""
HTML parsing for faculty list and profile pages.
"""
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Optional
from .models import PIProfile
from .config import UniversityConfig


def parse_faculty_list(html: str, config: UniversityConfig) -> List[PIProfile]:
    """
    Parse faculty list page and extract base profile information.

    Args:
        html: HTML content of faculty list page
        config: University configuration with CSS selectors

    Returns:
        List of PIProfile objects with basic information
    """
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(config.item_selector)
    profiles: List[PIProfile] = []

    for item in items:
        # Extract name (required)
        name_el = item.select_one(config.name_selector)
        if not name_el:
            continue
        full_name = name_el.get_text(strip=True)
        if not full_name:
            continue

        # Extract title (optional)
        title: Optional[str] = None
        if getattr(config, "title_selector", None):
            title_el = item.select_one(config.title_selector)
            if title_el:
                title = title_el.get_text(strip=True) or None

        # Extract email from mailto link (optional)
        email: Optional[str] = None
        if getattr(config, "email_selector", None):
            email_el = item.select_one(config.email_selector)
            if email_el and email_el.has_attr("href"):
                href = email_el["href"]
                if href.startswith("mailto:"):
                    email = href.replace("mailto:", "").strip()

        # Extract profile URL (defaults to list page if not found)
        profile_url = config.faculty_list_url
        if getattr(config, "profile_link_selector", None):
            link_el = item.select_one(config.profile_link_selector)
            if link_el and link_el.has_attr("href"):
                profile_url = urljoin(config.faculty_list_url, link_el["href"])

        # Extract personal website URL (optional)
        personal_website_url: Optional[str] = None
        if getattr(config, "personal_website_selector", None):
            pw_el = item.select_one(config.personal_website_selector)
            if pw_el and pw_el.has_attr("href"):
                personal_website_url = urljoin(config.faculty_list_url, pw_el["href"])

        # Extract raw research text (optional)
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


def parse_profile_detail(
    html: str,
    base_url: str,
    config: UniversityConfig
) -> tuple[Optional[str], Optional[str]]:
    """
    Parse profile detail page for additional information.

    Args:
        html: HTML content of profile page
        base_url: Base URL for resolving relative links
        config: University configuration

    Returns:
        Tuple of (personal_website_url, raw_research_text)
    """
    soup = BeautifulSoup(html, "html.parser")

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
