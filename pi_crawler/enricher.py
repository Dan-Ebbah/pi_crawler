from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
from .models import PIProfile
from .config import UniversityConfig
from .fetcher import fetch_html
from .extractors import extract_field
from .transforms import apply_transform

logger = logging.getLogger(__name__)

def enrich_profiles_with_profile_page(
        profiles: List[PIProfile],
        config: UniversityConfig,
        ) -> List[PIProfile]:
    # Check if using new format with profile_page config
    if config.is_new_format and config.raw_config:
        profile_page_config = config.raw_config.get("profile_page", {})
        if profile_page_config.get("enabled", False):
            return _enrich_profiles_new_format(profiles, config)
    
    # Fall back to old format
    return _enrich_profiles_old_format(profiles, config)


def _enrich_profiles_old_format(
        profiles: List[PIProfile],
        config: UniversityConfig,
        ) -> List[PIProfile]:
    """Enrich profiles using old format (backward compatibility)."""
    enriched: List[PIProfile] = []
    keywords = [k.lower() for k in config.research_heading_keywords]

    for profile in profiles:
        html = fetch_html(profile.profile_url, delay_seconds=config.request_delay_seconds)
        if not html:
            enriched.append(profile)
            continue
        soup = BeautifulSoup(html, "html.parser")

        personal_link = soup.find("a", string=lambda s: s and "website" in s.lower())
        personal_site_url = None
        if personal_link and personal_link.has_attr("href"):
            personal_site_url = urljoin(profile.profile_url, personal_link["href"])

        research_texts = None

        heading = soup.find(lambda tag: tag.name in ["h1", "h2", "h3"] and any(
            kw in tag.get_text(strip=True).lower() for kw in keywords))

        if heading:
            ul = heading.find_next("ul")
            if ul:
                items = [li.get_text(strip=True) for li in ul.find_all("li")]
                research_texts = " | ".join([i for i in items if i])
            else:
                p = heading.find_next("p")
                if p:
                    research_texts = p.get_text(strip=True)

        profile.personal_website_url = personal_site_url or profile.personal_website_url
        profile.raw_research_text = research_texts or profile.raw_research_text
        enriched.append(profile)

    return enriched


def _enrich_profiles_new_format(
        profiles: List[PIProfile],
        config: UniversityConfig,
        ) -> List[PIProfile]:
    """Enrich profiles using new extractor format."""
    enriched: List[PIProfile] = []
    profile_page_config = config.raw_config.get("profile_page", {})
    fields_config = profile_page_config.get("fields", {})

    for profile in profiles:
        html = fetch_html(profile.profile_url, delay_seconds=config.request_delay_seconds)
        if not html:
            enriched.append(profile)
            continue
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract personal_website_url if not already set
        if not profile.personal_website_url and "personal_website_url" in fields_config:
            personal_website_url = extract_field(soup, fields_config["personal_website_url"], profile.profile_url)
            if personal_website_url:
                # Apply transform
                field_config = fields_config["personal_website_url"]
                if "transform" in field_config:
                    transform = field_config["transform"]
                    personal_website_url = apply_transform(personal_website_url, transform, profile.profile_url)
                # Ensure absolute URL
                if personal_website_url and not personal_website_url.startswith("http"):
                    personal_website_url = urljoin(profile.profile_url, personal_website_url)
                profile.personal_website_url = personal_website_url
        
        # Extract raw_research_text if not already set
        if not profile.raw_research_text and "raw_research_text" in fields_config:
            raw_research_text = extract_field(soup, fields_config["raw_research_text"], profile.profile_url)
            if raw_research_text:
                profile.raw_research_text = raw_research_text
        
        enriched.append(profile)

    return enriched
