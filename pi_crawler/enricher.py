from typing import List, Optional, Tuple
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin, urlparse
import re
from .models import PIProfile
from .config import UniversityConfig
from .fetcher import fetch_html


def enrich_profiles_with_profile_page(
        profiles: List[PIProfile],
        config: UniversityConfig,
) -> List[PIProfile]:
    """Enrich profiles by fetching individual profile pages for additional details."""
    # Skip enrichment if disabled
    if not getattr(config, 'enrichment_enabled', True):
        return profiles

    enriched: List[PIProfile] = []
    keywords = [k.lower() for k in config.research_heading_keywords]
    website_keywords = getattr(config, 'personal_website_keywords',
                               ["website", "homepage", "personal", "home page"])
    section_tags = getattr(config, 'research_section_tags',
                          ["h1", "h2", "h3", "h4", "strong", "b"])

    for profile in profiles:
        # Skip if profile URL is the same as list URL (no detail page)
        if profile.profile_url == config.faculty_list_url:
            enriched.append(profile)
            continue

        html = fetch_html(profile.profile_url, delay_seconds=config.request_delay_seconds)
        if not html:
            enriched.append(profile)
            continue

        soup = BeautifulSoup(html, "html.parser")

        # Extract personal website using multiple strategies
        personal_site_url = _extract_personal_website(
            soup, profile.profile_url, website_keywords, config
        )

        # Extract research text using multiple strategies
        research_texts = _extract_research_text(soup, keywords, section_tags)

        # Extract email if not already found
        if not profile.email:
            profile.email = _extract_email(soup)

        profile.personal_website_url = personal_site_url or profile.personal_website_url
        profile.raw_research_text = research_texts or profile.raw_research_text
        enriched.append(profile)

    return enriched


def _extract_personal_website(
    soup: BeautifulSoup,
    base_url: str,
    keywords: List[str],
    config: UniversityConfig
) -> Optional[str]:
    """Extract personal website URL using multiple strategies."""

    # Strategy 1: Use explicit selector from config
    if getattr(config, 'personal_website_selector', None):
        el = soup.select_one(config.personal_website_selector)
        if el and el.has_attr("href"):
            return urljoin(base_url, el["href"])

    # Strategy 2: Look for links with keyword text
    for keyword in keywords:
        link = soup.find("a", string=lambda s: s and keyword.lower() in s.lower())
        if link and link.has_attr("href"):
            href = link["href"]
            # Filter out internal links and email links
            if not href.startswith("mailto:") and _is_external_link(href, base_url):
                return urljoin(base_url, href)

    # Strategy 3: Look for links with keyword in title/aria-label
    for keyword in keywords:
        link = soup.find("a", attrs={
            "title": lambda t: t and keyword.lower() in t.lower()
        })
        if link and link.has_attr("href"):
            href = link["href"]
            if not href.startswith("mailto:") and _is_external_link(href, base_url):
                return urljoin(base_url, href)

        link = soup.find("a", attrs={
            "aria-label": lambda t: t and keyword.lower() in t.lower()
        })
        if link and link.has_attr("href"):
            href = link["href"]
            if not href.startswith("mailto:") and _is_external_link(href, base_url):
                return urljoin(base_url, href)

    # Strategy 4: Look for common external link patterns
    external_patterns = [
        r'https?://(?:www\.)?(?!(?:linkedin|facebook|twitter|instagram|youtube)\.com)[a-zA-Z0-9-]+\.[a-zA-Z]{2,}',
    ]
    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Skip social media and the university's own domain
        if _is_likely_personal_site(href, base_url):
            return href

    # Strategy 5: Look for links in a "links" or "contact" section
    link_sections = soup.find_all(["div", "section", "aside"], class_=lambda c: c and any(
        x in c.lower() for x in ["links", "contact", "connect", "external", "social"]
    ))
    for section in link_sections:
        for link in section.find_all("a", href=True):
            href = link["href"]
            if _is_likely_personal_site(href, base_url):
                return href

    return None


def _is_external_link(href: str, base_url: str) -> bool:
    """Check if a link points to an external site."""
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return False
    if href.startswith(("http://", "https://")):
        base_domain = urlparse(base_url).netloc.lower()
        href_domain = urlparse(href).netloc.lower()
        return base_domain != href_domain
    return False


def _is_likely_personal_site(href: str, base_url: str) -> bool:
    """Heuristically determine if a URL is likely a personal website."""
    if not href.startswith(("http://", "https://")):
        return False

    # Skip social media
    social_domains = [
        "linkedin.com", "facebook.com", "twitter.com", "instagram.com",
        "youtube.com", "github.com", "scholar.google.com", "researchgate.net",
        "orcid.org", "x.com"
    ]
    href_lower = href.lower()
    if any(domain in href_lower for domain in social_domains):
        return False

    # Skip the university's own domain
    base_domain = urlparse(base_url).netloc.lower()
    href_domain = urlparse(href).netloc.lower()
    if base_domain == href_domain:
        return False

    # Skip common non-personal URLs
    skip_patterns = ["/doi/", "/pdf", ".pdf", "/download", "/publication"]
    if any(pattern in href_lower for pattern in skip_patterns):
        return False

    return True


def _extract_research_text(
    soup: BeautifulSoup,
    keywords: List[str],
    section_tags: List[str]
) -> Optional[str]:
    """Extract research interests text using multiple strategies."""

    # Strategy 1: Look for heading followed by content
    heading = soup.find(lambda tag: tag.name in section_tags and any(
        kw in tag.get_text(strip=True).lower() for kw in keywords))

    if heading:
        result = _extract_content_after_heading(heading)
        if result:
            return result

    # Strategy 2: Look for elements with research-related class/id
    research_patterns = ["research", "interest", "expertise", "specialty", "focus"]
    for pattern in research_patterns:
        # By class
        el = soup.find(class_=lambda c: c and pattern in c.lower())
        if el:
            text = el.get_text(" ", strip=True)
            if text and len(text) > 10:
                return _clean_research_text(text)

        # By id
        el = soup.find(id=lambda i: i and pattern in i.lower())
        if el:
            text = el.get_text(" ", strip=True)
            if text and len(text) > 10:
                return _clean_research_text(text)

    # Strategy 3: Look for labeled content (label: value pattern)
    for kw in keywords:
        # Look for dt/dd pairs
        dt = soup.find("dt", string=lambda s: s and kw.lower() in s.lower())
        if dt:
            dd = dt.find_next("dd")
            if dd:
                return _clean_research_text(dd.get_text(" ", strip=True))

        # Look for th/td pairs in tables
        th = soup.find("th", string=lambda s: s and kw.lower() in s.lower())
        if th:
            td = th.find_next("td")
            if td:
                return _clean_research_text(td.get_text(" ", strip=True))

    # Strategy 4: Look for meta description or structured data
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        content = meta["content"]
        if any(kw in content.lower() for kw in keywords):
            return content

    return None


def _extract_content_after_heading(heading: Tag) -> Optional[str]:
    """Extract content that follows a heading element."""
    # Try to find list items
    ul = heading.find_next("ul")
    if ul:
        # Check it's reasonably close (not from another section)
        if _is_element_close(heading, ul):
            items = [li.get_text(strip=True) for li in ul.find_all("li", recursive=False)]
            if items:
                return " | ".join([i for i in items if i])

    ol = heading.find_next("ol")
    if ol:
        if _is_element_close(heading, ol):
            items = [li.get_text(strip=True) for li in ol.find_all("li", recursive=False)]
            if items:
                return " | ".join([i for i in items if i])

    # Try to find paragraph
    p = heading.find_next("p")
    if p:
        if _is_element_close(heading, p):
            text = p.get_text(strip=True)
            if text:
                return _clean_research_text(text)

    # Try to find a div with text content
    div = heading.find_next("div")
    if div:
        if _is_element_close(heading, div):
            text = div.get_text(" ", strip=True)
            if text and len(text) > 10:
                return _clean_research_text(text)

    return None


def _is_element_close(el1: Tag, el2: Tag, max_elements: int = 5) -> bool:
    """Check if two elements are close to each other in the document."""
    # Simple heuristic: count elements between them
    current = el1.find_next()
    count = 0
    while current and current != el2 and count < max_elements:
        current = current.find_next()
        count += 1
    return current == el2


def _clean_research_text(text: str) -> str:
    """Clean up research text."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Truncate if too long
    if len(text) > 1000:
        text = text[:1000] + "..."
    return text.strip()


def _extract_email(soup: BeautifulSoup) -> Optional[str]:
    """Extract email address from the page."""
    # Look for mailto links
    email_link = soup.find("a", href=lambda h: h and h.startswith("mailto:"))
    if email_link:
        href = email_link["href"]
        email = href.replace("mailto:", "").split("?")[0].strip()
        if "@" in email:
            return email

    # Look for email pattern in text
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    for text in soup.stripped_strings:
        match = re.search(email_pattern, text)
        if match:
            return match.group(0)

    return None
