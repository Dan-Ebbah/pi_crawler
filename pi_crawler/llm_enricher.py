"""
Optional LLM-based enrichment for generating standardized expertise keywords.
Requires ANTHROPIC_API_KEY environment variable.

This module provides higher-quality expertise extraction than rule-based methods
but incurs API costs. Use sparingly or for profiles that need better keywords.
"""
import os
import re
import json
import time
from typing import List, Optional
from .models import PIProfile

# Optional import - only fails if actually used without the package
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


def get_anthropic_client():
    """Get Anthropic client if API key is available."""
    if not ANTHROPIC_AVAILABLE:
        raise ImportError("anthropic package not installed. Run: pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    return anthropic.Anthropic(api_key=api_key)


def build_expertise_prompt(profile: PIProfile) -> str:
    """Build prompt for extracting expertise keywords."""
    return f"""You are a research assistant extracting standardized expertise keywords.

## INPUT:
- Name: {profile.full_name}
- Title: {profile.title or 'Not specified'}
- Department: {profile.department}
- University: {profile.university}
- Raw Research Text: {profile.raw_research_text or 'Not available'}
- About/Bio: {profile.about or 'Not available'}

## TASK:
Generate 10-15 standardized expertise keyword phrases based on the information above.

## REQUIREMENTS:
- Each keyword should be a specific research area, skill, or methodology
- Keywords should be 2-5 words each
- Use standard academic terminology
- Be specific but not overly narrow
- Separate keywords with commas

## EXAMPLES OF GOOD KEYWORDS:
- Structural Health Monitoring
- Machine Learning
- Finite Element Analysis
- Sustainable Infrastructure
- Natural Language Processing
- Climate Resilience
- Data Analytics

## OUTPUT:
Return ONLY a comma-separated list of 10-15 expertise keywords. No other text.
"""


def extract_expertise_with_llm(
    profile: PIProfile,
    client=None,
    model: str = "claude-sonnet-4-20250514",
    max_retries: int = 3,
    rate_limit_wait: int = 60,
) -> Optional[str]:
    """
    Extract expertise keywords using Claude API.

    Args:
        profile: PIProfile to enrich
        client: Optional pre-initialized Anthropic client
        model: Model to use
        max_retries: Number of retry attempts
        rate_limit_wait: Seconds to wait on rate limit

    Returns:
        Comma-separated expertise keywords or None on failure
    """
    if client is None:
        client = get_anthropic_client()

    prompt = build_expertise_prompt(profile)

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract text response
            if response.content:
                text = response.content[0].text.strip()
                # Clean up the response
                text = re.sub(r'^["\']|["\']$', '', text)  # Remove quotes
                text = text.strip()
                if text:
                    return text

        except Exception as e:
            error_type = type(e).__name__
            if "RateLimitError" in error_type:
                wait_time = rate_limit_wait * (attempt + 1)
                print(f"   [!] Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"   [!] LLM error: {error_type}: {e}")
                time.sleep(5)

    return None


def enrich_profiles_with_llm(
    profiles: List[PIProfile],
    only_missing: bool = True,
    delay_seconds: float = 1.0,
    model: str = "claude-sonnet-4-20250514",
) -> List[PIProfile]:
    """
    Enrich profiles with LLM-generated expertise keywords.

    Args:
        profiles: List of profiles to enrich
        only_missing: Only enrich profiles without expertise keywords
        delay_seconds: Delay between API calls
        model: Claude model to use

    Returns:
        List of enriched profiles
    """
    client = get_anthropic_client()
    total = len(profiles)
    enriched_count = 0

    for idx, profile in enumerate(profiles, 1):
        # Skip if already has good keywords
        if only_missing and profile.get_expertise_count() >= 5:
            print(f"   [{idx}/{total}] Skipping {profile.full_name} (has {profile.get_expertise_count()} keywords)")
            continue

        print(f"   [{idx}/{total}] LLM enriching: {profile.full_name}")

        keywords = extract_expertise_with_llm(profile, client=client, model=model)
        if keywords:
            profile.expertise_keywords = keywords
            enriched_count += 1
            print(f"      Generated {profile.get_expertise_count()} keywords")
        else:
            print(f"      [!] Failed to generate keywords")

        # Rate limiting
        if idx < total:
            time.sleep(delay_seconds)

    print(f"[*] LLM enriched {enriched_count}/{total} profiles")
    return profiles


def build_full_extraction_prompt(name: str, department: str, university: str) -> str:
    """
    Build a comprehensive extraction prompt for web search.
    This is for use with Claude's web_search tool.
    """
    return f"""You are a research assistant extracting comprehensive faculty information.

## TARGET:
- **Name:** {name}
- **Institution:** {university}
- **Department:** {department if department else "Not specified"}

## TASK:
Search the web thoroughly and extract comprehensive information. Use web_search for each query.

## REQUIRED SEARCHES:
1. "{name} {university} professor biography"
2. "{name} Google Scholar"
3. "{name} research interests publications"

## OUTPUT FORMAT (JSON only):

{{
    "qualifications": "[Degrees: PhD, MS, BS, PE, etc. with institutions]",
    "title": "[Academic title: Professor, Associate Professor, etc.]",
    "about": "[Comprehensive biography describing research focus, approach, and impact - minimum 50 characters]",
    "expertise_keywords": "[EXACTLY 10-15 expertise keyword phrases, comma-separated]",
    "funding_sources": "[Funding agencies (NSF, NIH, DOE, DOT, etc.) and collaborating institutions]",
    "google_scholar_url": "[Google Scholar profile URL if found]",
    "orcid_url": "[ORCID profile URL if found]",
    "phone": "[Phone number with area code]"
}}

## CRITICAL REQUIREMENTS:

### EXPERTISE KEYWORDS (MOST IMPORTANT):
- Generate EXACTLY 10-15 expertise keyword phrases
- Each keyword should be a specific research area or skill
- Separate with commas
- Example: "Geotechnical Engineering, Soil Mechanics, Earthquake Engineering, Centrifuge Modeling"

Return ONLY JSON, no other text.
"""


def enrich_profile_with_web_search(
    profile: PIProfile,
    client=None,
    model: str = "claude-sonnet-4-20250514",
    max_retries: int = 3,
) -> PIProfile:
    """
    Fully enrich a profile using Claude with web search.
    This provides the highest quality extraction but is expensive.

    Args:
        profile: PIProfile to enrich
        client: Optional pre-initialized Anthropic client
        model: Model to use
        max_retries: Number of retry attempts

    Returns:
        Enriched profile
    """
    if client is None:
        client = get_anthropic_client()

    prompt = build_full_extraction_prompt(
        profile.full_name,
        profile.department,
        profile.university
    )

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract text from response
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text

            if response_text:
                # Parse JSON response
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    data = json.loads(json_match.group())

                    # Update profile with extracted data
                    if data.get("qualifications"):
                        profile.qualifications = data["qualifications"]
                    if data.get("title"):
                        profile.title = data["title"]
                    if data.get("about"):
                        profile.about = data["about"]
                    if data.get("expertise_keywords"):
                        profile.expertise_keywords = data["expertise_keywords"]
                    if data.get("funding_sources"):
                        profile.funding_sources = data["funding_sources"]
                    if data.get("google_scholar_url"):
                        profile.google_scholar_url = data["google_scholar_url"]
                    if data.get("orcid_url"):
                        profile.orcid_url = data["orcid_url"]
                    if data.get("phone"):
                        profile.phone = data["phone"]

                    return profile

        except Exception as e:
            error_type = type(e).__name__
            print(f"   [!] Error: {error_type}: {e}")
            if attempt < max_retries - 1:
                time.sleep(30 * (attempt + 1))

    profile.error_message = "LLM enrichment failed"
    return profile
