from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .models import PIProfile
from .config import UniversityConfig
from .fetcher import fetch_html

def enrich_profiles_with_profile_page(
        profiles: List[PIProfile],
        config: UniversityConfig,
        ) -> List[PIProfile]:
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
