"""
Checkpoint functionality for saving and resuming crawl progress.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Set, Tuple, Optional
from .models import PIProfile

CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / "checkpoints"


def get_checkpoint_path(university_id: str) -> Path:
    """Get the checkpoint file path for a university."""
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    return CHECKPOINT_DIR / f"{university_id}_checkpoint.json"


def save_checkpoint(
    university_id: str,
    profiles: List[PIProfile],
    processed_names: Set[str],
    total_count: int,
) -> None:
    """
    Save current progress to checkpoint file.

    Args:
        university_id: University configuration ID
        profiles: List of extracted profiles so far
        processed_names: Set of names already processed
        total_count: Total number of faculty to process
    """
    checkpoint_path = get_checkpoint_path(university_id)

    data = {
        "timestamp": datetime.now().isoformat(),
        "university_id": university_id,
        "total_count": total_count,
        "processed_count": len(processed_names),
        "processed_names": list(processed_names),
        "profiles": [p.to_dict() for p in profiles],
    }

    with open(checkpoint_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"   [CHECKPOINT] Saved {len(profiles)} profiles")


def load_checkpoint(university_id: str) -> Tuple[List[PIProfile], Set[str]]:
    """
    Load progress from checkpoint file.

    Args:
        university_id: University configuration ID

    Returns:
        Tuple of (list of profiles, set of processed names)
    """
    checkpoint_path = get_checkpoint_path(university_id)
    profiles: List[PIProfile] = []
    processed_names: Set[str] = set()

    if not checkpoint_path.exists():
        return profiles, processed_names

    try:
        with open(checkpoint_path, "r") as f:
            data = json.load(f)

        # Verify it's for the same university
        if data.get("university_id") != university_id:
            print(f"[WARN] Checkpoint is for different university, ignoring")
            return profiles, processed_names

        # Load processed names
        processed_names = set(data.get("processed_names", []))

        # Load profiles
        for p_data in data.get("profiles", []):
            if p_data.get("full_name"):
                # Filter to only valid PIProfile fields
                valid_fields = {
                    "full_name", "title", "department", "university", "email",
                    "phone", "profile_url", "personal_website_url", "google_scholar_url",
                    "orcid_url", "qualifications", "about", "raw_research_text",
                    "expertise_keywords", "funding_sources", "country",
                    "source_university_id", "status", "quality_score",
                    "error_message", "extraction_timestamp"
                }
                filtered_data = {k: v for k, v in p_data.items() if k in valid_fields}
                profile = PIProfile(**filtered_data)
                profiles.append(profile)

        timestamp = data.get("timestamp", "unknown")
        print(f"[*] Loaded checkpoint from {timestamp}")
        print(f"    - {len(profiles)} profiles loaded")
        print(f"    - {len(processed_names)} names already processed")

    except Exception as e:
        print(f"[WARN] Could not load checkpoint: {e}")

    return profiles, processed_names


def clear_checkpoint(university_id: str) -> None:
    """Delete checkpoint file to start fresh."""
    checkpoint_path = get_checkpoint_path(university_id)

    if checkpoint_path.exists():
        os.remove(checkpoint_path)
        print(f"[*] Cleared checkpoint: {checkpoint_path.name}")
    else:
        print("[*] No checkpoint file to clear")


def has_checkpoint(university_id: str) -> bool:
    """Check if a checkpoint exists for the university."""
    return get_checkpoint_path(university_id).exists()


def get_checkpoint_info(university_id: str) -> Optional[dict]:
    """Get summary info about existing checkpoint."""
    checkpoint_path = get_checkpoint_path(university_id)

    if not checkpoint_path.exists():
        return None

    try:
        with open(checkpoint_path, "r") as f:
            data = json.load(f)

        return {
            "timestamp": data.get("timestamp"),
            "processed_count": data.get("processed_count", 0),
            "total_count": data.get("total_count", 0),
            "profile_count": len(data.get("profiles", [])),
        }
    except Exception:
        return None
