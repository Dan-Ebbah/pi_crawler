# python
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Optional, Callable
from .models import PIProfile
from .config import UniversityConfig

def parse_faculty_list(html: str, config: UniversityConfig) -> List[PIProfile]:
    soup = BeautifulSoup(html, "html.parser")
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

def parse_profile_detail(html: str, base_url: str, config: UniversityConfig) -> tuple[Optional[str], Optional[str]]:
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
