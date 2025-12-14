"""
Profile enrichment from detail pages.
Extracts additional information like bio, qualifications, phone, etc.
"""
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .models import PIProfile
from .config import UniversityConfig
from .fetcher import fetch_html


def extract_phone_number(soup: BeautifulSoup) -> Optional[str]:
    """Extract phone number from page."""
    # Common patterns for phone numbers
    phone_patterns = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (603) 862-1234 or 603-862-1234
        r'\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # +1-603-862-1234
    ]

    # Look for phone in common locations
    phone_elements = soup.find_all(["a", "span", "p", "div"], string=re.compile(r'phone|tel', re.I))
    for el in phone_elements:
        text = el.get_text()
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group().strip()

    # Check tel: links
    tel_link = soup.find("a", href=re.compile(r'^tel:'))
    if tel_link:
        href = tel_link.get("href", "")
        return href.replace("tel:", "").strip()

    # Search entire page text
    page_text = soup.get_text()
    for pattern in phone_patterns:
        match = re.search(pattern, page_text)
        if match:
            return match.group().strip()

    return None


def extract_qualifications(soup: BeautifulSoup) -> Optional[str]:
    """Extract qualifications/degrees from page."""
    qualifications = []

    # Common degree patterns
    degree_patterns = [
        r'\bPh\.?D\.?\b',
        r'\bM\.?S\.?\b',
        r'\bM\.?A\.?\b',
        r'\bB\.?S\.?\b',
        r'\bB\.?A\.?\b',
        r'\bM\.?B\.?A\.?\b',
        r'\bP\.?E\.?\b',  # Professional Engineer
        r'\bM\.?D\.?\b',
    ]

    # Look for education section
    edu_heading = soup.find(lambda tag: tag.name in ["h1", "h2", "h3", "h4"] and
                            re.search(r'education|degree|credential|qualification', tag.get_text(), re.I))

    if edu_heading:
        # Get content after heading
        next_el = edu_heading.find_next(["ul", "p", "div"])
        if next_el:
            text = next_el.get_text(" ", strip=True)
            # Extract degree mentions
            for pattern in degree_patterns:
                if re.search(pattern, text, re.I):
                    # Try to get the full degree line
                    lines = text.split('\n')
                    for line in lines:
                        if re.search(pattern, line, re.I):
                            qualifications.append(line.strip())

    # Also check the page for degree mentions
    if not qualifications:
        page_text = soup.get_text()
        for pattern in degree_patterns:
            matches = re.findall(pattern, page_text, re.I)
            qualifications.extend(matches)

    if qualifications:
        # Deduplicate and format
        unique = list(dict.fromkeys(qualifications))
        return ", ".join(unique[:5])  # Limit to 5

    return None


def extract_about_bio(soup: BeautifulSoup) -> Optional[str]:
    """Extract biography/about text from page."""
    # Look for bio/about section
    bio_heading = soup.find(lambda tag: tag.name in ["h1", "h2", "h3", "h4"] and
                           re.search(r'about|bio|overview|profile|background', tag.get_text(), re.I))

    if bio_heading:
        # Get paragraphs after heading
        paragraphs = []
        for sibling in bio_heading.find_next_siblings():
            if sibling.name in ["p"]:
                text = sibling.get_text(strip=True)
                if len(text) > 30:  # Skip short paragraphs
                    paragraphs.append(text)
            elif sibling.name in ["h1", "h2", "h3"]:
                break  # Stop at next heading
            if len(paragraphs) >= 3:
                break
        if paragraphs:
            return " ".join(paragraphs)

    # Try to find the main content area bio
    main_content = soup.find(["main", "article", "div"], class_=re.compile(r'content|profile|bio', re.I))
    if main_content:
        paragraphs = main_content.find_all("p", limit=5)
        bio_text = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 50:  # Only substantial paragraphs
                bio_text.append(text)
        if bio_text:
            return " ".join(bio_text[:3])

    return None


def extract_google_scholar_url(soup: BeautifulSoup) -> Optional[str]:
    """Extract Google Scholar profile URL."""
    scholar_link = soup.find("a", href=re.compile(r'scholar\.google\.com', re.I))
    if scholar_link:
        return scholar_link.get("href")
    return None


def extract_orcid_url(soup: BeautifulSoup) -> Optional[str]:
    """Extract ORCID profile URL."""
    orcid_link = soup.find("a", href=re.compile(r'orcid\.org', re.I))
    if orcid_link:
        return orcid_link.get("href")
    return None


def generate_expertise_keywords(raw_research_text: Optional[str]) -> Optional[str]:
    """
    Generate standardized expertise keywords from raw research text.
    This is a simple extraction - for better results, use LLM enrichment.
    """
    if not raw_research_text:
        return None

    # Common research area patterns and keywords
    keywords = []

    # Split by common delimiters
    parts = re.split(r'[|;,\n]', raw_research_text)

    for part in parts:
        part = part.strip()
        # Skip very short or very long items
        if 3 <= len(part) <= 50:
            # Clean up
            part = re.sub(r'\s+', ' ', part)
            part = part.strip('.-')
            if part and not part.isdigit():
                keywords.append(part)

    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen:
            seen.add(kw_lower)
            unique_keywords.append(kw)

    if unique_keywords:
        return ", ".join(unique_keywords[:15])  # Limit to 15 keywords

    return None


def enrich_profiles_with_profile_page(
    profiles: List[PIProfile],
    config: UniversityConfig,
) -> List[PIProfile]:
    """
    Enrich profiles by fetching and parsing their detail pages.

    Extracts:
    - Personal website URL
    - Research interests/raw text
    - Phone number
    - Qualifications/degrees
    - About/bio
    - Google Scholar URL
    - ORCID URL
    - Expertise keywords (derived from research text)
    """
    enriched: List[PIProfile] = []
    keywords = [k.lower() for k in config.research_heading_keywords]
    total = len(profiles)

    for idx, profile in enumerate(profiles, 1):
        print(f"   [{idx}/{total}] Enriching: {profile.full_name}")

        html = fetch_html(profile.profile_url, delay_seconds=config.request_delay_seconds)
        if not html:
            enriched.append(profile)
            continue

        soup = BeautifulSoup(html, "html.parser")

        # Extract personal website
        personal_link = soup.find("a", string=lambda s: s and "website" in s.lower())
        if personal_link and personal_link.has_attr("href"):
            profile.personal_website_url = urljoin(profile.profile_url, personal_link["href"])

        # Extract research interests
        research_texts = None
        heading = soup.find(lambda tag: tag.name in ["h1", "h2", "h3", "h4"] and any(
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

        if research_texts:
            profile.raw_research_text = research_texts
            # Generate expertise keywords from raw text
            if not profile.expertise_keywords:
                profile.expertise_keywords = generate_expertise_keywords(research_texts)

        # Extract additional fields
        if not profile.phone:
            profile.phone = extract_phone_number(soup)

        if not profile.qualifications:
            profile.qualifications = extract_qualifications(soup)

        if not profile.about:
            profile.about = extract_about_bio(soup)

        if not profile.google_scholar_url:
            profile.google_scholar_url = extract_google_scholar_url(soup)

        if not profile.orcid_url:
            profile.orcid_url = extract_orcid_url(soup)

        enriched.append(profile)

    return enriched
