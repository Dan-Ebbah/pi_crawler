import json
import sys
from pathlib import Path
from typing import Optional

import typer

from pi_crawler.config import (
    load_university_config,
    list_available_configs,
    validate_config_file,
    CONFIG_DIR,
    ConfigValidationError,
)
from pi_crawler.enricher import enrich_profiles_with_profile_page
from pi_crawler.fetcher import fetch_html
from pi_crawler.parser import parse_faculty_list
from pi_crawler.pagination import fetch_all_paginated_pages, detect_pagination_type
from pi_crawler.storage import save_profiles

app = typer.Typer(help="PI Crawler - Universal faculty/PI information scraper")


@app.command()
def crawl(
    university_id: str = typer.Argument(..., help="University config ID (filename without .json)"),
    no_enrich: bool = typer.Option(False, "--no-enrich", help="Skip profile page enrichment"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Limit number of profiles to process"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse but don't save to database"),
):
    """Crawl faculty information for a university."""
    try:
        config = load_university_config(university_id)
    except FileNotFoundError as e:
        typer.echo(f"[!] {e}", err=True)
        raise typer.Exit(code=1)
    except ConfigValidationError as e:
        typer.echo(f"[!] {e}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"[*] Crawling {config.name} ({config.id})...")
    typer.echo(f"[*] URL: {config.faculty_list_url}")

    # Fetch with pagination support
    def fetch_with_delay(url: str) -> Optional[str]:
        return fetch_html(url, delay_seconds=config.request_delay_seconds)

    if config.pagination and config.pagination.enabled:
        typer.echo(f"[*] Pagination enabled (type: {config.pagination.type})")
        base_profiles = fetch_all_paginated_pages(config, fetch_with_delay, parse_faculty_list)
    else:
        list_html = fetch_html(config.faculty_list_url, delay_seconds=config.request_delay_seconds)
        if not list_html:
            typer.echo("[!] Failed to fetch faculty list page.")
            raise typer.Exit(code=1)
        base_profiles = parse_faculty_list(list_html, config)

    typer.echo(f"[*] Found {len(base_profiles)} base profiles.")

    if limit:
        base_profiles = base_profiles[:limit]
        typer.echo(f"[*] Limited to {len(base_profiles)} profiles.")

    if no_enrich:
        enriched_profiles = base_profiles
        typer.echo("[*] Skipping enrichment.")
    else:
        enriched_profiles = enrich_profiles_with_profile_page(base_profiles, config)
        typer.echo(f"[*] Enriched {len(enriched_profiles)} profiles.")

    if dry_run:
        typer.echo("[*] Dry run - not saving to database.")
        for i, p in enumerate(enriched_profiles[:5], 1):
            typer.echo(f"  {i}. {p.full_name} ({p.title}) - {p.email}")
        if len(enriched_profiles) > 5:
            typer.echo(f"  ... and {len(enriched_profiles) - 5} more")
    else:
        save_profiles(enriched_profiles)
        typer.echo(f"[OK] Saved {len(enriched_profiles)} profiles.")


@app.command()
def test(
    university_id: str = typer.Argument(..., help="University config ID to test"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """Test a university configuration without saving data.

    This command validates the config, fetches the page, and shows sample results.
    """
    typer.echo(f"[*] Testing configuration: {university_id}")
    typer.echo("=" * 50)

    # Step 1: Load and validate config
    typer.echo("\n[1/4] Validating configuration...")
    try:
        config = load_university_config(university_id)
        typer.echo(f"  [OK] Config loaded successfully")
        typer.echo(f"  - University: {config.name}")
        typer.echo(f"  - Department: {config.department}")
        typer.echo(f"  - URL: {config.faculty_list_url}")
    except FileNotFoundError as e:
        typer.echo(f"  [FAIL] {e}", err=True)
        raise typer.Exit(code=1)
    except ConfigValidationError as e:
        typer.echo(f"  [FAIL] Configuration errors:", err=True)
        for error in e.errors:
            typer.echo(f"    - {error}", err=True)
        raise typer.Exit(code=1)

    # Step 2: Fetch the page
    typer.echo("\n[2/4] Fetching faculty list page...")
    html = fetch_html(config.faculty_list_url, delay_seconds=0.5)
    if not html:
        typer.echo("  [FAIL] Could not fetch the page", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"  [OK] Fetched {len(html)} bytes")

    # Step 3: Parse the page
    typer.echo("\n[3/4] Parsing faculty list...")
    profiles = parse_faculty_list(html, config)

    if not profiles:
        typer.echo("  [WARN] No profiles found!", err=True)
        typer.echo("  Check your CSS selectors:")
        typer.echo(f"    - item_selector: {config.item_selector}")
        typer.echo(f"    - name_selector: {config.name_selector}")

        # Try to help diagnose
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select(config.item_selector)
        typer.echo(f"  Elements matching item_selector: {len(items)}")
        if items:
            first_item = items[0]
            names = first_item.select(config.name_selector)
            typer.echo(f"  Elements matching name_selector in first item: {len(names)}")
        raise typer.Exit(code=1)

    typer.echo(f"  [OK] Found {len(profiles)} profiles")

    # Step 4: Show sample results
    typer.echo("\n[4/4] Sample results:")
    typer.echo("-" * 50)

    sample_count = 5 if not verbose else len(profiles)
    for i, p in enumerate(profiles[:sample_count], 1):
        typer.echo(f"\n  [{i}] {p.full_name}")
        if p.title:
            typer.echo(f"      Title: {p.title}")
        if p.email:
            typer.echo(f"      Email: {p.email}")
        if p.profile_url and p.profile_url != config.faculty_list_url:
            typer.echo(f"      Profile: {p.profile_url}")

    if len(profiles) > sample_count:
        typer.echo(f"\n  ... and {len(profiles) - sample_count} more profiles")

    # Check pagination
    typer.echo("\n" + "=" * 50)
    typer.echo("[*] Pagination detection:")
    pagination_hint = detect_pagination_type(html, config.faculty_list_url)
    if pagination_hint:
        typer.echo(f"  Detected pagination type: {pagination_hint['type']}")
        typer.echo("  Suggested config:")
        typer.echo(f"    {json.dumps(pagination_hint, indent=4)}")
    else:
        typer.echo("  No pagination detected (single page)")

    typer.echo("\n" + "=" * 50)
    typer.echo("[OK] Test completed successfully!")


@app.command("list")
def list_configs():
    """List all available university configurations."""
    configs = list_available_configs()

    if not configs:
        typer.echo("No configurations found.")
        typer.echo(f"Add config files to: {CONFIG_DIR}")
        return

    typer.echo(f"Available configurations ({len(configs)}):\n")

    for config_id in sorted(configs):
        try:
            config = load_university_config(config_id)
            typer.echo(f"  {config_id}")
            typer.echo(f"    {config.name} - {config.department}")
        except Exception as e:
            typer.echo(f"  {config_id} [ERROR: {e}]")


@app.command()
def validate(
    config_path: Optional[str] = typer.Argument(
        None, help="Path to config file (or 'all' to validate all)"
    ),
):
    """Validate a configuration file."""
    if config_path == "all" or config_path is None:
        # Validate all configs
        configs = list(CONFIG_DIR.glob("*.json"))
        if not configs:
            typer.echo("No configuration files found.")
            return

        typer.echo(f"Validating {len(configs)} configuration files...\n")
        errors_found = False

        for path in sorted(configs):
            errors = validate_config_file(path)
            if errors:
                errors_found = True
                typer.echo(f"[FAIL] {path.name}")
                for error in errors:
                    typer.echo(f"  - {error}")
            else:
                typer.echo(f"[OK] {path.name}")

        if errors_found:
            raise typer.Exit(code=1)
    else:
        # Validate single config
        path = Path(config_path)
        if not path.exists():
            # Try as config ID
            path = CONFIG_DIR / f"{config_path}.json"

        if not path.exists():
            typer.echo(f"Config file not found: {config_path}", err=True)
            raise typer.Exit(code=1)

        errors = validate_config_file(path)
        if errors:
            typer.echo(f"[FAIL] Validation errors in {path.name}:")
            for error in errors:
                typer.echo(f"  - {error}")
            raise typer.Exit(code=1)
        else:
            typer.echo(f"[OK] {path.name} is valid")


@app.command()
def init(
    university_id: str = typer.Argument(..., help="ID for the new config (e.g., 'stanford_cs')"),
    url: str = typer.Option(..., "--url", "-u", help="Faculty list page URL"),
    name: str = typer.Option(..., "--name", "-n", help="University name"),
    department: str = typer.Option(..., "--department", "-d", help="Department name"),
):
    """Initialize a new university configuration with suggested selectors.

    This command fetches the page and attempts to detect common patterns.
    """
    output_path = CONFIG_DIR / f"{university_id}.json"
    if output_path.exists():
        typer.echo(f"[!] Config already exists: {output_path}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"[*] Creating config for: {name} - {department}")
    typer.echo(f"[*] Fetching: {url}")

    html = fetch_html(url, delay_seconds=0.5)
    if not html:
        typer.echo("[!] Could not fetch the page", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"[*] Analyzing page structure...")

    # Analyze the page
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Common faculty list patterns
    item_selectors = [
        ".faculty-card", ".faculty-member", ".faculty-item",
        ".person-card", ".person-item", ".person",
        ".profile-card", ".profile-item", ".profile",
        ".staff-member", ".staff-card",
        ".directory-item", ".directory-entry",
        "[class*='faculty']", "[class*='person']", "[class*='profile']",
        ".views-row", ".node--type-person",
        "article", ".card",
    ]

    name_selectors = [
        ".name", ".faculty-name", ".person-name", ".profile-name",
        "h2", "h3", "h4",
        ".title a", ".name a",
        "[class*='name']",
    ]

    detected_item = None
    detected_name = None

    for item_sel in item_selectors:
        items = soup.select(item_sel)
        if len(items) >= 3:  # At least 3 items suggests it's a list
            for name_sel in name_selectors:
                names_found = sum(1 for item in items if item.select_one(name_sel))
                if names_found >= len(items) * 0.5:  # At least 50% have names
                    detected_item = item_sel
                    detected_name = name_sel
                    break
            if detected_item:
                break

    # Build config
    config = {
        "id": university_id,
        "name": name,
        "department": department,
        "faculty_list_url": url,
        "item_selector": detected_item or "REPLACE_WITH_SELECTOR",
        "name_selector": detected_name or "REPLACE_WITH_SELECTOR",
        "title_selector": None,
        "email_selector": "a[href^='mailto:']",
        "profile_link_selector": None,
        "research_heading_keywords": ["research", "interests", "expertise", "specialization"],
        "request_delay_seconds": 1.0
    }

    # Detect pagination
    pagination_hint = detect_pagination_type(html, url)
    if pagination_hint:
        config["pagination"] = pagination_hint

    # Write config
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)

    typer.echo(f"\n[OK] Created config: {output_path}")

    if detected_item:
        typer.echo(f"[*] Detected item selector: {detected_item}")
        typer.echo(f"[*] Detected name selector: {detected_name}")
        items = soup.select(detected_item)
        typer.echo(f"[*] Found {len(items)} potential faculty items")
    else:
        typer.echo("[!] Could not auto-detect selectors. Please edit the config manually.")

    typer.echo("\nNext steps:")
    typer.echo(f"  1. Edit {output_path} to refine selectors")
    typer.echo(f"  2. Run: python -m pi_crawler.cli test {university_id}")
    typer.echo(f"  3. When ready: python -m pi_crawler.cli crawl {university_id}")


def run_crawl(university_id: str):
    """Run crawl programmatically (for API use)."""
    crawl(university_id)


if __name__ == "__main__":
    app()
