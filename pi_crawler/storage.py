import os
import psycopg2
from contextlib import contextmanager
from typing import List
from .models import PIProfile

DB_DSN = os.getenv("PI_CRAWLER_DB_DSN")


@contextmanager
def get_db_connection():
    conn = psycopg2.connect(DB_DSN)
    try:
        yield conn
    finally:
        conn.close()


def save_profiles(profiles: List[PIProfile]) -> None:
    """Save profiles to database or mock output if DB_DSN is not set."""
    if not profiles:
        return

    # Mock mode: if no DSN is configured, just print the profiles instead of saving
    if not DB_DSN:
        print(f"[MOCK] Would save {len(profiles)} profiles to database:")
        for i, p in enumerate(profiles[:6], 1):
            expertise_count = p.get_expertise_count()
            print(f"  {i}. {p.full_name}")
            print(f"      Title: {p.title or 'N/A'}")
            print(f"      Email: {p.email or 'N/A'}")
            print(f"      Expertise: {expertise_count} keywords")
            print(f"      Status: {p.status}")
        if len(profiles) > 6:
            print(f"  ... and {len(profiles) - 6} more")
        return

    # Real DB mode
    with get_db_connection() as conn:
        cur = conn.cursor()
        for p in profiles:
            cur.execute(
                """
                INSERT INTO pi_profiles (
                    full_name,
                    title,
                    department,
                    university,
                    email,
                    phone,
                    profile_url,
                    personal_website_url,
                    google_scholar_url,
                    orcid_url,
                    qualifications,
                    about,
                    raw_research_text,
                    expertise_keywords,
                    funding_sources,
                    country,
                    source_university_id,
                    status,
                    quality_score,
                    error_message,
                    extraction_timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (profile_url) DO UPDATE SET
                    title = EXCLUDED.title,
                    email = EXCLUDED.email,
                    phone = EXCLUDED.phone,
                    personal_website_url = EXCLUDED.personal_website_url,
                    google_scholar_url = EXCLUDED.google_scholar_url,
                    orcid_url = EXCLUDED.orcid_url,
                    qualifications = EXCLUDED.qualifications,
                    about = EXCLUDED.about,
                    raw_research_text = EXCLUDED.raw_research_text,
                    expertise_keywords = EXCLUDED.expertise_keywords,
                    funding_sources = EXCLUDED.funding_sources,
                    status = EXCLUDED.status,
                    quality_score = EXCLUDED.quality_score,
                    extraction_timestamp = EXCLUDED.extraction_timestamp;
                """,
                (
                    p.full_name,
                    p.title,
                    p.department,
                    p.university,
                    p.email,
                    p.phone,
                    p.profile_url,
                    p.personal_website_url,
                    p.google_scholar_url,
                    p.orcid_url,
                    p.qualifications,
                    p.about,
                    p.raw_research_text,
                    p.expertise_keywords,
                    p.funding_sources,
                    p.country,
                    p.source_university_id,
                    p.status,
                    p.quality_score,
                    p.error_message,
                    p.extraction_timestamp,
                ),
            )
        conn.commit()


# SQL for creating the updated table schema
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pi_profiles (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    department VARCHAR(255),
    university VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    profile_url TEXT NOT NULL UNIQUE,
    personal_website_url TEXT,
    google_scholar_url TEXT,
    orcid_url TEXT,
    qualifications TEXT,
    about TEXT,
    raw_research_text TEXT,
    expertise_keywords TEXT,
    funding_sources TEXT,
    country VARCHAR(100) DEFAULT 'USA',
    source_university_id VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'Active',
    quality_score DECIMAL(3,2) DEFAULT 0.0,
    error_message TEXT,
    extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pi_profiles_university ON pi_profiles(university);
CREATE INDEX IF NOT EXISTS idx_pi_profiles_department ON pi_profiles(department);
CREATE INDEX IF NOT EXISTS idx_pi_profiles_status ON pi_profiles(status);
"""
