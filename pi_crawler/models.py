from dataclasses import dataclass, field, asdict
from typing import Optional, List, Tuple
from datetime import datetime


@dataclass
class PIProfile:
    """
    Faculty profile with comprehensive fields matching research data requirements.
    """
    # Core identification
    full_name: str
    title: Optional[str] = None
    department: str = ""
    university: str = ""

    # Contact information
    email: Optional[str] = None
    phone: Optional[str] = None

    # URLs
    profile_url: str = ""
    personal_website_url: Optional[str] = None
    google_scholar_url: Optional[str] = None
    orcid_url: Optional[str] = None

    # Academic information
    qualifications: Optional[str] = None  # Degrees: PhD, MS, BS, PE, etc.
    about: Optional[str] = None  # Comprehensive biography
    raw_research_text: Optional[str] = None  # Raw research interests text
    expertise_keywords: Optional[str] = None  # Comma-separated standardized keywords
    funding_sources: Optional[str] = None  # NSF, NIH, DOE, etc.

    # Location
    country: str = "USA"

    # Metadata
    source_university_id: str = ""
    status: str = "Active"  # Active, Needs Review, Failed
    quality_score: float = 0.0
    error_message: Optional[str] = None
    extraction_timestamp: Optional[str] = None

    def __post_init__(self):
        if not self.extraction_timestamp:
            self.extraction_timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_output_dict(self) -> dict:
        """Convert to output dictionary with standardized column names."""
        return {
            "PI Name": self.full_name,
            "Qualifications and Certifications": self.qualifications or "",
            "Title": self.title or "",
            "About": self.about or "",
            "Expertise": self.expertise_keywords or "",
            "Department": self.department,
            "Previous Collaborations & Funding Sources": self.funding_sources or "",
            "Affiliation": self.university,
            "Public Profile Weblink": self._get_all_urls(),
            "Email": self.email or "",
            "Official Phone": self.phone or "",
            "Country of Residence": self.country,
            "Status": self.status,
        }

    def _get_all_urls(self) -> str:
        """Combine all profile URLs into a single string."""
        urls = []
        if self.profile_url:
            urls.append(self.profile_url)
        if self.personal_website_url:
            urls.append(self.personal_website_url)
        if self.google_scholar_url:
            urls.append(self.google_scholar_url)
        if self.orcid_url:
            urls.append(self.orcid_url)
        return ", ".join(urls)

    def validate(self, min_about_length: int = 50, min_expertise_keywords: int = 5) -> Tuple[bool, List[str]]:
        """
        Validate profile quality.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check about/bio length
        if not self.about or len(self.about) < min_about_length:
            issues.append(f"About too short (min {min_about_length} chars)")

        # Check expertise keywords count
        if self.expertise_keywords:
            keyword_count = len([k.strip() for k in self.expertise_keywords.split(',') if k.strip()])
            if keyword_count < min_expertise_keywords:
                issues.append(f"Need {min_expertise_keywords}+ expertise keywords (found {keyword_count})")
        else:
            issues.append(f"No expertise keywords (need {min_expertise_keywords}+)")

        # Check email
        if not self.email or '@' not in self.email:
            issues.append("Valid email required")

        # Check profile URL
        if not self.profile_url:
            issues.append("Profile URL required")

        # Calculate quality score
        self.quality_score = max(0.0, 1.0 - (len(issues) * 0.2))

        # Update status based on validation
        if len(issues) == 0:
            self.status = "Active"
        elif len(issues) <= 2:
            self.status = "Needs Review"
        else:
            self.status = "Incomplete"

        return len(issues) == 0, issues

    def get_expertise_count(self) -> int:
        """Get the number of expertise keywords."""
        if not self.expertise_keywords:
            return 0
        return len([k.strip() for k in self.expertise_keywords.split(',') if k.strip()])
