"""
Command-line interface for pi_crawler.

Features:
- Crawl faculty data from university websites
- Checkpoint/resume support for interrupted crawls
- CSV and JSON export
- Quality reporting
- Optional LLM enrichment
"""
import time
from datetime import datetime
from typing import Optional

import typer

from pi_crawler.config import load_university_config
from pi_crawler.enricher import enrich_profiles_with_profile_page
from pi_crawler.fetcher import fetch_html
from pi_crawler.parser import parse_faculty_list
from pi_crawler.storage import save_profiles
from pi_crawler.checkpoint import (
    save_checkpoint,
    load_checkpoint,
    clear_checkpoint,
    has_checkpoint,
    get_checkpoint_info,
)
from pi_crawler.export import (
    export_to_csv,
    export_to_json,
    print_quality_report,
)

app = typer.Typer(help="Faculty data crawler with checkpoint and export support")


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


@app.command()
def crawl(
    university_id: str = typer.Argument(..., help="University configuration ID (e.g., 'univ_hampshire')"),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume from checkpoint if available"),
    fresh: bool = typer.Option(False, "--fresh", "-f", help="Clear checkpoint and start fresh"),
    export_csv: bool = typer.Option(False, "--csv", help="Export results to CSV"),
    export_json: bool = typer.Option(False, "--json", help="Export results to JSON"),
    show_report: bool = typer.Option(True, "--report/--no-report", help="Show quality report"),
    use_llm: bool = typer.Option(False, "--llm", help="Use LLM for expertise extraction (requires ANTHROPIC_API_KEY)"),
):
    """
    Crawl faculty data from a university website.

    Examples:
        # Basic crawl
        python -m pi_crawler.cli crawl univ_hampshire

        # Resume interrupted crawl
        python -m pi_crawler.cli crawl univ_hampshire --resume

        # Fresh start with CSV export
        python -m pi_crawler.cli crawl univ_hampshire --fresh --csv
    """
    start_time = time.time()

    # Load configuration
    config = load_university_config(university_id)
    typer.echo(f"\n{'='*60}")
    typer.echo(f"PI CRAWLER: {config.name}")
    typer.echo(f"{'='*60}")
    typer.echo(f"[*] Department: {config.department}")
    typer.echo(f"[*] URL: {config.faculty_list_url}")

    # Handle checkpoint
    profiles = []
    processed_names = set()

    if fresh:
        clear_checkpoint(university_id)
    elif resume and has_checkpoint(university_id):
        info = get_checkpoint_info(university_id)
        typer.echo(f"\n[*] Found checkpoint from {info['timestamp']}")
        typer.echo(f"    Processed: {info['processed_count']}/{info['total_count']}")

        if typer.confirm("Resume from checkpoint?", default=True):
            profiles, processed_names = load_checkpoint(university_id)
        else:
            clear_checkpoint(university_id)

    # Fetch faculty list
    typer.echo(f"\n[*] Fetching faculty list...")
    list_html = fetch_html(config.faculty_list_url, delay_seconds=config.request_delay_seconds)
    if not list_html:
        typer.echo("[!] Failed to fetch faculty list page.")
        raise typer.Exit(code=1)

    # Parse faculty list
    all_profiles = parse_faculty_list(list_html, config)
    total_count = len(all_profiles)
    typer.echo(f"[*] Found {total_count} faculty members")

    # Filter out already processed
    profiles_to_process = [p for p in all_profiles if p.full_name not in processed_names]
    remaining = len(profiles_to_process)

    if remaining == 0:
        typer.echo("[*] All profiles already processed!")
    else:
        # Estimate time
        est_seconds = remaining * (config.request_delay_seconds + 2)  # +2s for processing
        typer.echo(f"\n[*] Remaining: {remaining} profiles")
        typer.echo(f"[*] Estimated time: ~{format_duration(est_seconds)}")
        typer.echo(f"{'='*60}\n")

        # Enrich profiles with progress tracking
        for idx, profile in enumerate(profiles_to_process, 1):
            progress_pct = (len(processed_names) + idx) / total_count * 100
            elapsed = time.time() - start_time
            eta = elapsed / idx * remaining if idx > 0 else 0

            typer.echo(f"[{len(processed_names) + idx}/{total_count}] ({progress_pct:.0f}%) {profile.full_name}")
            typer.echo(f"   ETA: {format_duration(eta)}")

            # Enrich single profile
            enriched = enrich_profiles_with_profile_page([profile], config)
            if enriched:
                profile = enriched[0]

            # Validate profile
            profile.validate()

            # Add to results
            profiles.append(profile)
            processed_names.add(profile.full_name)

            # Save checkpoint after each profile
            save_checkpoint(university_id, profiles, processed_names, total_count)

            # Show brief status
            typer.echo(f"   Email: {profile.email or 'Not found'}")
            typer.echo(f"   Expertise: {profile.get_expertise_count()} keywords")
            typer.echo(f"   Status: {profile.status}")
            typer.echo("")

    # Optional LLM enrichment
    if use_llm:
        typer.echo("\n[*] Running LLM enrichment for better expertise keywords...")
        try:
            from pi_crawler.llm_enricher import enrich_profiles_with_llm
            profiles = enrich_profiles_with_llm(profiles, only_missing=True)
            # Re-save checkpoint after LLM enrichment
            save_checkpoint(university_id, profiles, processed_names, total_count)
        except ImportError as e:
            typer.echo(f"[!] LLM enrichment unavailable: {e}")
        except ValueError as e:
            typer.echo(f"[!] LLM enrichment error: {e}")

    # Save to database
    save_profiles(profiles)
    typer.echo(f"\n[OK] Saved {len(profiles)} profiles")

    # Export options
    if export_csv:
        csv_path = export_to_csv(profiles, university_id=university_id)
        typer.echo(f"[OK] Exported to: {csv_path}")

    if export_json:
        json_path = export_to_json(profiles, university_id=university_id)
        typer.echo(f"[OK] Exported to: {json_path}")

    # Quality report
    if show_report:
        print_quality_report(profiles)

    # Final summary
    elapsed = time.time() - start_time
    typer.echo(f"\n{'='*60}")
    typer.echo(f"COMPLETED in {format_duration(elapsed)}")
    typer.echo(f"{'='*60}\n")


@app.command()
def export(
    university_id: str = typer.Argument(..., help="University configuration ID"),
    format: str = typer.Option("csv", "--format", "-f", help="Export format: csv or json"),
    filename: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
):
    """
    Export saved checkpoint data to CSV or JSON.

    Examples:
        python -m pi_crawler.cli export univ_hampshire --format csv
        python -m pi_crawler.cli export univ_hampshire -f json -o faculty_data.json
    """
    if not has_checkpoint(university_id):
        typer.echo(f"[!] No checkpoint found for {university_id}")
        raise typer.Exit(code=1)

    profiles, _ = load_checkpoint(university_id)
    if not profiles:
        typer.echo("[!] No profiles in checkpoint")
        raise typer.Exit(code=1)

    typer.echo(f"[*] Exporting {len(profiles)} profiles...")

    if format.lower() == "csv":
        path = export_to_csv(profiles, filename=filename, university_id=university_id)
    elif format.lower() == "json":
        path = export_to_json(profiles, filename=filename, university_id=university_id)
    else:
        typer.echo(f"[!] Unknown format: {format}")
        raise typer.Exit(code=1)

    typer.echo(f"[OK] Exported to: {path}")


@app.command()
def report(
    university_id: str = typer.Argument(..., help="University configuration ID"),
):
    """
    Generate quality report from checkpoint data.

    Examples:
        python -m pi_crawler.cli report univ_hampshire
    """
    if not has_checkpoint(university_id):
        typer.echo(f"[!] No checkpoint found for {university_id}")
        raise typer.Exit(code=1)

    profiles, _ = load_checkpoint(university_id)
    if not profiles:
        typer.echo("[!] No profiles in checkpoint")
        raise typer.Exit(code=1)

    # Validate all profiles
    for p in profiles:
        p.validate()

    print_quality_report(profiles)


@app.command()
def status(
    university_id: str = typer.Argument(..., help="University configuration ID"),
):
    """
    Show checkpoint status for a university.

    Examples:
        python -m pi_crawler.cli status univ_hampshire
    """
    info = get_checkpoint_info(university_id)
    if not info:
        typer.echo(f"[*] No checkpoint found for {university_id}")
        return

    typer.echo(f"\nCheckpoint Status: {university_id}")
    typer.echo(f"{'='*40}")
    typer.echo(f"Last updated: {info['timestamp']}")
    typer.echo(f"Progress: {info['processed_count']}/{info['total_count']}")
    typer.echo(f"Profiles saved: {info['profile_count']}")

    pct = info['processed_count'] / info['total_count'] * 100 if info['total_count'] > 0 else 0
    typer.echo(f"Completion: {pct:.0f}%")


@app.command()
def clear(
    university_id: str = typer.Argument(..., help="University configuration ID"),
):
    """
    Clear checkpoint for a university.

    Examples:
        python -m pi_crawler.cli clear univ_hampshire
    """
    if has_checkpoint(university_id):
        if typer.confirm(f"Clear checkpoint for {university_id}?"):
            clear_checkpoint(university_id)
            typer.echo("[OK] Checkpoint cleared")
    else:
        typer.echo("[*] No checkpoint to clear")


def run_crawl(university_id: str):
    """Programmatic interface for crawling."""
    crawl(university_id)


if __name__ == "__main__":
    app()
