from dataclasses import dataclass
from typing import Optional


@dataclass
class PIProfile:
    full_name: str
    title: Optional[str]
    department: str
    university: str
    email: Optional[str]
    profile_url: str
    personal_website_url: Optional[str]
    raw_research_text: Optional[str]
    source_university_id: str