"""
Export functionality for faculty profiles.
Supports CSV, JSON export and quality reporting.
"""
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from .models import PIProfile

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def ensure_output_dir() -> Path:
    """Ensure output directory exists."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR


def export_to_csv(
    profiles: List[PIProfile],
    filename: Optional[str] = None,
    university_id: Optional[str] = None,
) -> Path:
    """
    Export profiles to CSV file with standardized columns.

    Args:
        profiles: List of PIProfile objects
        filename: Optional custom filename
        university_id: Optional university ID for default filename

    Returns:
        Path to the exported CSV file
    """
    ensure_output_dir()

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = university_id or "faculty"
        filename = f"{prefix}_data_{timestamp}.csv"

    output_path = OUTPUT_DIR / filename

    # Define column order matching the original template
    columns = [
        "PI Name",
        "Qualifications and Certifications",
        "Title",
        "About",
        "Expertise",
        "Department",
        "Previous Collaborations & Funding Sources",
        "Affiliation",
        "Public Profile Weblink",
        "Email",
        "Official Phone",
        "Country of Residence",
        "Status",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for profile in profiles:
            row = profile.to_output_dict()
            writer.writerow(row)

    print(f"[*] Exported {len(profiles)} profiles to: {output_path}")
    return output_path


def export_to_json(
    profiles: List[PIProfile],
    filename: Optional[str] = None,
    university_id: Optional[str] = None,
) -> Path:
    """
    Export profiles to JSON file with all fields.

    Args:
        profiles: List of PIProfile objects
        filename: Optional custom filename
        university_id: Optional university ID for default filename

    Returns:
        Path to the exported JSON file
    """
    ensure_output_dir()

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = university_id or "faculty"
        filename = f"{prefix}_data_{timestamp}.json"

    output_path = OUTPUT_DIR / filename

    data = {
        "export_timestamp": datetime.now().isoformat(),
        "university_id": university_id,
        "total_profiles": len(profiles),
        "profiles": [p.to_dict() for p in profiles],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"[*] Exported {len(profiles)} profiles to: {output_path}")
    return output_path


def generate_quality_report(
    profiles: List[PIProfile],
    min_about_length: int = 50,
    min_expertise_keywords: int = 5,
) -> dict:
    """
    Generate a quality report for extracted profiles.

    Args:
        profiles: List of PIProfile objects
        min_about_length: Minimum required about/bio length
        min_expertise_keywords: Minimum required expertise keywords

    Returns:
        Dictionary containing quality metrics
    """
    if not profiles:
        return {"error": "No profiles to analyze"}

    # Validate all profiles
    for p in profiles:
        p.validate(min_about_length, min_expertise_keywords)

    # Count by status
    status_counts = {
        "Active": 0,
        "Needs Review": 0,
        "Incomplete": 0,
        "Failed": 0,
    }
    for p in profiles:
        status_counts[p.status] = status_counts.get(p.status, 0) + 1

    # Calculate field coverage
    total = len(profiles)
    field_coverage = {
        "email": sum(1 for p in profiles if p.email and "@" in p.email) / total * 100,
        "phone": sum(1 for p in profiles if p.phone) / total * 100,
        "about": sum(1 for p in profiles if p.about and len(p.about) >= min_about_length) / total * 100,
        "expertise": sum(1 for p in profiles if p.get_expertise_count() >= min_expertise_keywords) / total * 100,
        "qualifications": sum(1 for p in profiles if p.qualifications) / total * 100,
        "profile_url": sum(1 for p in profiles if p.profile_url) / total * 100,
        "personal_website": sum(1 for p in profiles if p.personal_website_url) / total * 100,
    }

    # Expertise keyword statistics
    expertise_counts = [p.get_expertise_count() for p in profiles]
    avg_expertise = sum(expertise_counts) / total if total > 0 else 0

    # Quality scores
    quality_scores = [p.quality_score for p in profiles]
    avg_quality = sum(quality_scores) / total if total > 0 else 0

    return {
        "total_profiles": total,
        "status_breakdown": status_counts,
        "field_coverage_percent": field_coverage,
        "expertise_stats": {
            "average_keywords": round(avg_expertise, 1),
            "min_keywords": min(expertise_counts) if expertise_counts else 0,
            "max_keywords": max(expertise_counts) if expertise_counts else 0,
            "profiles_meeting_minimum": sum(1 for c in expertise_counts if c >= min_expertise_keywords),
        },
        "average_quality_score": round(avg_quality, 2),
    }


def print_quality_report(profiles: List[PIProfile], min_expertise_keywords: int = 5) -> None:
    """Print a formatted quality report to console."""
    report = generate_quality_report(profiles, min_expertise_keywords=min_expertise_keywords)

    if "error" in report:
        print(f"[!] {report['error']}")
        return

    print("\n" + "=" * 60)
    print("QUALITY REPORT")
    print("=" * 60)

    print(f"\nTotal Profiles: {report['total_profiles']}")

    print("\nStatus Breakdown:")
    for status, count in report["status_breakdown"].items():
        pct = count / report["total_profiles"] * 100 if report["total_profiles"] > 0 else 0
        icon = {"Active": "[OK]", "Needs Review": "[!]", "Incomplete": "[?]", "Failed": "[X]"}.get(status, "")
        print(f"  {icon} {status}: {count} ({pct:.0f}%)")

    print("\nField Coverage:")
    for field, pct in report["field_coverage_percent"].items():
        bar = "[" + "#" * int(pct / 10) + "." * (10 - int(pct / 10)) + "]"
        print(f"  {field:20s}: {bar} {pct:.0f}%")

    print("\nExpertise Keywords:")
    stats = report["expertise_stats"]
    print(f"  Average per profile: {stats['average_keywords']}")
    print(f"  Range: {stats['min_keywords']} - {stats['max_keywords']}")
    print(f"  Meeting minimum ({min_expertise_keywords}+): {stats['profiles_meeting_minimum']}/{report['total_profiles']}")

    print(f"\nAverage Quality Score: {report['average_quality_score']:.2f}")

    print("\nPer-Faculty Expertise Count:")
    print("-" * 40)
    for p in profiles:
        count = p.get_expertise_count()
        icon = "[OK]" if count >= min_expertise_keywords else "[!]"
        print(f"  {icon} {p.full_name}: {count} keywords")

    print("=" * 60 + "\n")
