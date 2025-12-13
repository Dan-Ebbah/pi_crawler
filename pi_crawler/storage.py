import os
from contextlib import contextmanager
from typing import List
from .models import PIProfile

DB_DSN = os.getenv("PI_CRAWLER_DB_DSN")

@contextmanager
def get_db_connection():
    try:
        import psycopg2
    except ImportError:
        raise ImportError("psycopg2 is required for database storage. Install with: pip install psycopg2-binary")
    
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
        for i, p in enumerate(profiles[:6], 1):  # Show first 3 as sample
            print(f"  {i}. {p.full_name} ({p.title}) - {p.email} - {p.profile_url} - {p.personal_website_url} - {p.raw_research_text}")
        if len(profiles) > 3:
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
                    profile_url,
                    personal_website_url,
                    raw_research_text,
                    source_university_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (
                    p.full_name,
                    p.title,
                    p.department,
                    p.university,
                    p.email,
                    p.profile_url,
                    p.personal_website_url,
                    p.raw_research_text,
                    p.source_university_id
                ),
            )
        conn.commit()
