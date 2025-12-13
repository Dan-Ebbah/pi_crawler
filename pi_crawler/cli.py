import time
import typer

from pi_crawler.config import load_university_config
from pi_crawler.enricher import enrich_profiles_with_profile_page
from pi_crawler.fetcher import fetch_html
from pi_crawler.parser import parse_faculty_list
from pi_crawler.storage import save_profiles

app = typer.Typer()

@app.command()
def crawl(university_id: str):
    config = load_university_config(university_id)
    typer.echo(f"[*] Crawling {config.name} ({config.id})...")

    list_html = fetch_html(config.faculty_list_url, delay_seconds=config.request_delay_seconds)
    if not list_html:
        typer.echo("[!] Failed to fetch faculty list page.")
        raise typer.Exit(code=1)

    base_profiles = parse_faculty_list(list_html, config)
    typer.echo(f"[*] Found {len(base_profiles)} base profiles.")

    enriched_profiles = enrich_profiles_with_profile_page(base_profiles, config)
    typer.echo(f"[*] Enriched {len(enriched_profiles)} profiles.")

    save_profiles(enriched_profiles)
    typer.echo(f"[✓] Saved profiles to database.")

def run_crawl(university_id: str):
    crawl(university_id)

if __name__ == "__main__":
    app()
