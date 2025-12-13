# PICrawler

A configurable web crawler for extracting faculty and Principal Investigator (PI) profiles from university department websites.

## Overview

PICrawler is a Python-based web scraping tool designed to systematically collect faculty information from university department websites. It extracts structured data about researchers, including their contact information, research interests, and profile URLs, making it easier to build academic databases or conduct research on faculty members across different institutions.

## Features

- **Configurable Crawling**: JSON-based configuration system allows easy addition of new universities
- **Two-Stage Parsing**: Efficiently extracts data from faculty list pages and individual profile pages
- **Enrichment Pipeline**: Automatically follows profile links to gather additional information
- **Polite Crawling**: Built-in rate limiting and retry logic with exponential backoff
- **Mock Mode**: Test configurations without a database connection
- **PostgreSQL Storage**: Save collected data to a PostgreSQL database
- **Robust Error Handling**: Gracefully handles missing fields, failed requests, and parsing errors

## Project Structure

```
pi_crawler/
├── pi_crawler/
│   ├── cli.py          # Command-line interface
│   ├── config.py       # Configuration loading and management
│   ├── fetcher.py      # HTTP fetching with retry logic
│   ├── parser.py       # HTML parsing for faculty lists
│   ├── enricher.py     # Profile enrichment from detail pages
│   ├── models.py       # Data models (PIProfile)
│   ├── storage.py      # Database storage (PostgreSQL)
│   └── api.py          # API utilities
├── configs/
│   ├── univ_hampshire.json   # UNH CS Department config
│   └── univ_example.json     # Example template
└── TESTING.md          # Testing guide
```

## Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL database (optional, for production use)

### Install Dependencies

```bash
pip install typer requests beautifulsoup4 psycopg2-binary
```

Or if using a requirements file:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

The crawler is invoked via the CLI with a university configuration ID:

```bash
python -m pi_crawler.cli <university_id>
```

### Examples

```bash
# Crawl University of New Hampshire CS Department
python -m pi_crawler.cli univ_hampshire

# Try the example configuration (will fail to fetch from fake URL)
python -m pi_crawler.cli univ_example
```

### Mock Mode (No Database)

By default, if no database connection string is configured, the crawler runs in mock mode:

```bash
python -m pi_crawler.cli univ_hampshire
```

This will:
- Fetch and parse all data normally
- Print a summary of collected profiles to stdout
- Skip database storage

Perfect for testing configurations or exploring data before committing to a database.

### Database Mode

To save data to PostgreSQL, set the `PI_CRAWLER_DB_DSN` environment variable:

```bash
export PI_CRAWLER_DB_DSN="postgresql://user:password@host:5432/database"
python -m pi_crawler.cli univ_hampshire
```

## Configuration

### Adding a New University

Create a JSON configuration file in the `configs/` directory:

```json
{
  "id": "your_univ_cs",
  "name": "Your University Name",
  "department": "Computer Science",
  "faculty_list_url": "https://cs.youruniv.edu/faculty",
  "item_selector": ".faculty-card",
  "name_selector": ".faculty-name",
  "title_selector": ".faculty-title",
  "email_selector": "a[href^='mailto:']",
  "profile_link_selector": "a[href*='/faculty/']",
  "research_heading_keywords": ["research", "interests"],
  "request_delay_seconds": 1.0
}
```

### Configuration Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the configuration |
| `name` | string | Full university name |
| `department` | string | Department name (e.g., "Computer Science") |
| `faculty_list_url` | string | URL of the faculty directory page |
| `item_selector` | string | CSS selector for individual faculty items |
| `name_selector` | string | CSS selector for faculty name within an item |
| `title_selector` | string (optional) | CSS selector for job title |
| `email_selector` | string (optional) | CSS selector for email links |
| `profile_link_selector` | string (optional) | CSS selector for profile page links |
| `research_heading_keywords` | array | Keywords to identify research sections (e.g., ["research", "interests"]) |
| `request_delay_seconds` | float | Delay between requests (for rate limiting) |

### CSS Selectors

The crawler uses CSS selectors to locate data on web pages. Common patterns:

- Class selectors: `.faculty-name`, `.person-list__person`
- Attribute selectors: `a[href^='mailto:']`, `a[href*='/faculty/']`
- Pseudo-classes: Use BeautifulSoup's `select_one()` for single elements

Tip: Use browser developer tools to inspect HTML and identify the right selectors.

## Architecture

### Crawling Workflow

1. **Load Configuration**: Read university config from JSON file
2. **Fetch List Page**: Download the faculty directory HTML
3. **Parse Base Profiles**: Extract basic info from list page (name, title, email, profile URL)
4. **Enrich Profiles**: Visit individual profile pages to collect:
   - Personal website URLs
   - Research interests/descriptions
5. **Save Data**: Store profiles in PostgreSQL or output to console (mock mode)

### Data Model

The `PIProfile` dataclass represents a faculty member:

```python
@dataclass
class PIProfile:
    full_name: str                      # Full name
    title: Optional[str]                # Job title (e.g., "Associate Professor")
    department: str                     # Department name
    university: str                     # University name
    email: Optional[str]                # Email address
    profile_url: str                    # URL to faculty profile page
    personal_website_url: Optional[str] # Personal/lab website URL
    raw_research_text: Optional[str]    # Research interests description
    source_university_id: str           # Configuration ID used for crawling
```

### Components

- **Fetcher** (`fetcher.py`): Handles HTTP requests with retry logic, rate limiting, and user-agent headers
- **Parser** (`parser.py`): Parses HTML using BeautifulSoup to extract structured data
- **Enricher** (`enricher.py`): Follows profile links to gather additional details
- **Storage** (`storage.py`): Manages database persistence with mock mode support
- **Config** (`config.py`): Loads and validates university configurations
- **CLI** (`cli.py`): Command-line interface built with Typer

## Database Schema

The PostgreSQL database should have a `pi_profiles` table:

```sql
CREATE TABLE pi_profiles (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    department VARCHAR(255) NOT NULL,
    university VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    profile_url TEXT NOT NULL,
    personal_website_url TEXT,
    raw_research_text TEXT,
    source_university_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_url, source_university_id)
);
```

The `ON CONFLICT DO NOTHING` clause prevents duplicate entries.

## Development

### Running Tests

See [TESTING.md](TESTING.md) for detailed testing instructions.

### Adding New Features

1. **New Data Fields**: Update the `PIProfile` model and database schema
2. **New Selectors**: Add optional fields to `UniversityConfig`
3. **Custom Parsing Logic**: Extend the `parser.py` or `enricher.py` modules

### Best Practices

- **Rate Limiting**: Always set appropriate `request_delay_seconds` (recommended: 1-2 seconds)
- **User Agent**: The fetcher includes a polite user-agent with contact info
- **Error Handling**: Missing fields are set to `None` rather than failing the entire crawl
- **Testing**: Use mock mode to verify configurations before running production crawls

## Dependencies

- **typer**: Modern CLI framework
- **requests**: HTTP library
- **beautifulsoup4**: HTML parsing
- **psycopg2-binary**: PostgreSQL adapter

## Known Issues & Limitations

- Currently focused on university CS department websites
- CSS selectors are site-specific and may break with website redesigns
- No JavaScript rendering (uses static HTML only)
- Research interest extraction relies on heading keywords and may miss non-standard layouts

## Contributing

To add a new university configuration:

1. Inspect the target website's HTML structure
2. Create a JSON config file with appropriate selectors
3. Test in mock mode: `python -m pi_crawler.cli your_config_id`
4. Submit a pull request with the config file

## License

Contact: danielebbah@yahoo.com

## Changelog

### Recent Fixes

- **Parser**: Fixed `.select()` → `.select_one()` for name selector to avoid list errors
- **Model**: Made `email` field optional to match actual parsing behavior
- **Storage**: Added mock mode for testing without database
