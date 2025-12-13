import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"

@dataclass
class UniversityConfig:
    id: str
    name: str
    department: str
    faculty_list_url: str
    item_selector: str
    name_selector: str
    title_selector: Optional[str]
    email_selector: Optional[str]
    profile_link_selector: Optional[str]
    research_heading_keywords: List[str]
    request_delay_seconds: float

    @classmethod
    def from_json_file(cls, path: Path) -> "UniversityConfig":
        data = json.loads(path.read_text())
        return cls(**data)

def load_university_config(univ_id: str) -> UniversityConfig:
    path = CONFIG_DIR / f"{univ_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Configuration file for university '{univ_id}' not found.")
    return UniversityConfig.from_json_file(path)