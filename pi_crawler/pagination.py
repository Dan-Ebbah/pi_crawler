"""Pagination support for faculty list pages."""
from typing import List, Optional, Iterator, Callable
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup

from .config import UniversityConfig, PaginationConfig
from .models import PIProfile


def generate_paginated_urls(config: UniversityConfig) -> Iterator[str]:
    """Generate URLs for paginated faculty lists.

    Yields URLs one at a time to allow for lazy fetching.
    """
    pagination = config.pagination

    if not pagination or not pagination.enabled:
        # No pagination - just yield the single URL
        yield config.faculty_list_url
        return

    if pagination.type == "page_param":
        yield from _generate_page_param_urls(config.faculty_list_url, pagination)
    elif pagination.type == "offset_param":
        yield from _generate_offset_param_urls(config.faculty_list_url, pagination)
    else:
        # For next_link and load_more types, just yield the first URL
        # The actual pagination is handled during fetching
        yield config.faculty_list_url


def _generate_page_param_urls(base_url: str, pagination: PaginationConfig) -> Iterator[str]:
    """Generate URLs for page parameter based pagination."""
    current_page = pagination.start_value

    for _ in range(pagination.max_pages):
        yield _add_url_param(base_url, pagination.param_name, str(current_page))
        current_page += pagination.increment


def _generate_offset_param_urls(base_url: str, pagination: PaginationConfig) -> Iterator[str]:
    """Generate URLs for offset parameter based pagination."""
    current_offset = pagination.start_value

    for _ in range(pagination.max_pages):
        yield _add_url_param(base_url, pagination.param_name, str(current_offset))
        current_offset += pagination.increment


def _add_url_param(url: str, param_name: str, param_value: str) -> str:
    """Add or replace a URL parameter."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params[param_name] = [param_value]
    new_query = urlencode(params, doseq=True)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))


def fetch_all_paginated_pages(
    config: UniversityConfig,
    fetch_html: Callable[[str], Optional[str]],
    parse_page: Callable[[str, UniversityConfig], List[PIProfile]]
) -> List[PIProfile]:
    """Fetch all pages of a paginated faculty list.

    Args:
        config: University configuration
        fetch_html: Function to fetch HTML from a URL
        parse_page: Function to parse profiles from HTML

    Returns:
        List of all profiles from all pages
    """
    all_profiles: List[PIProfile] = []
    pagination = config.pagination
    seen_names = set()  # Track names to detect duplicate pages

    if not pagination or not pagination.enabled:
        # No pagination - single page fetch
        html = fetch_html(config.faculty_list_url)
        if html:
            return parse_page(html, config)
        return []

    if pagination.type in ["page_param", "offset_param"]:
        # URL-based pagination
        for url in generate_paginated_urls(config):
            html = fetch_html(url)
            if not html:
                break

            profiles = parse_page(html, config)

            # Stop if no profiles found
            if pagination.stop_when_empty and not profiles:
                break

            # Check for duplicate page (same profiles as before)
            page_names = frozenset(p.full_name for p in profiles)
            if page_names and page_names.issubset(seen_names):
                # We've seen all these names before - likely reached end
                break

            seen_names.update(page_names)
            all_profiles.extend(profiles)

    elif pagination.type == "next_link":
        # Follow "next" links
        current_url = config.faculty_list_url
        pages_fetched = 0

        while current_url and pages_fetched < pagination.max_pages:
            html = fetch_html(current_url)
            if not html:
                break

            profiles = parse_page(html, config)

            if pagination.stop_when_empty and not profiles:
                break

            # Check for duplicates
            page_names = frozenset(p.full_name for p in profiles)
            if page_names and page_names.issubset(seen_names):
                break

            seen_names.update(page_names)
            all_profiles.extend(profiles)
            pages_fetched += 1

            # Find next link
            soup = BeautifulSoup(html, "html.parser")
            next_link = soup.select_one(pagination.next_link_selector)
            if next_link and next_link.has_attr("href"):
                current_url = urljoin(current_url, next_link["href"])
            else:
                break

    elif pagination.type == "load_more":
        # Note: load_more typically requires JavaScript execution
        # This is a placeholder for potential future Selenium/Playwright integration
        html = fetch_html(config.faculty_list_url)
        if html:
            all_profiles = parse_page(html, config)
            print("[WARN] load_more pagination requires JavaScript. Only first page fetched.")

    return all_profiles


def detect_pagination_type(html: str, base_url: str) -> Optional[dict]:
    """Attempt to auto-detect pagination type from page HTML.

    Returns suggested pagination config or None if no pagination detected.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Look for "next" links
    next_patterns = [
        'a[rel="next"]',
        'a.next',
        '.pagination a.next',
        '.pager .next a',
        'a[aria-label*="next" i]',
        'a[title*="next" i]',
    ]
    for pattern in next_patterns:
        el = soup.select_one(pattern)
        if el and el.has_attr("href"):
            return {
                "enabled": True,
                "type": "next_link",
                "next_link_selector": pattern,
                "max_pages": 50
            }

    # Look for page number links
    page_patterns = [
        '.pagination a',
        '.pager a',
        '[class*="pagination"] a',
        '[class*="pager"] a',
    ]
    for pattern in page_patterns:
        links = soup.select(pattern)
        if len(links) >= 2:
            # Check if any href contains page parameter
            for link in links:
                href = link.get("href", "")
                if "page=" in href or "p=" in href:
                    param = "page" if "page=" in href else "p"
                    return {
                        "enabled": True,
                        "type": "page_param",
                        "param_name": param,
                        "start_value": 1,
                        "increment": 1,
                        "max_pages": 50
                    }

    # Look for "load more" buttons
    load_more_patterns = [
        'button[class*="load-more"]',
        'a[class*="load-more"]',
        'button:contains("Load More")',
        '[class*="show-more"]',
    ]
    for pattern in load_more_patterns:
        try:
            el = soup.select_one(pattern)
            if el:
                return {
                    "enabled": True,
                    "type": "load_more",
                    "load_more_selector": pattern,
                    "max_pages": 50
                }
        except Exception:
            continue

    return None
