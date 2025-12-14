# PI Crawler - Faculty Data Extraction System

A cost-effective web scraping solution for extracting faculty information from university websites, with optional LLM enrichment for higher-quality expertise extraction.

## Features

- **Web Scraping**: Extract faculty data from university websites using BeautifulSoup
- **Checkpoint/Resume**: Save progress and resume interrupted crawls
- **CSV/JSON Export**: Export data in multiple formats matching your template
- **Quality Validation**: Automatic validation with quality scores
- **Progress Tracking**: Real-time progress display with ETA
- **LLM Enrichment** (optional): Use Claude API for better expertise keyword extraction

## Installation

```bash
pip install -r requirements.txt
```

For optional LLM enrichment:
```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-api-key"
```

## Quick Start

### Basic Crawl
```bash
python -m pi_crawler.cli crawl univ_hampshire
```

### With CSV Export
```bash
python -m pi_crawler.cli crawl univ_hampshire --csv
```

### Resume Interrupted Crawl
```bash
python -m pi_crawler.cli crawl univ_hampshire --resume
```

### Fresh Start (Clear Previous Data)
```bash
python -m pi_crawler.cli crawl univ_hampshire --fresh --csv
```

### With LLM Enrichment
```bash
python -m pi_crawler.cli crawl univ_hampshire --llm --csv
```

## CLI Commands

### `crawl` - Main Extraction Command
```bash
python -m pi_crawler.cli crawl <university_id> [OPTIONS]

Options:
  --resume, -r          Resume from checkpoint if available
  --fresh, -f           Clear checkpoint and start fresh
  --csv                 Export results to CSV
  --json                Export results to JSON
  --report/--no-report  Show quality report (default: show)
  --llm                 Use LLM for expertise extraction (requires ANTHROPIC_API_KEY)
```

### `export` - Export Saved Data
```bash
python -m pi_crawler.cli export <university_id> [OPTIONS]

Options:
  --format, -f TEXT   Export format: csv or json (default: csv)
  --output, -o TEXT   Output filename
```

### `report` - Generate Quality Report
```bash
python -m pi_crawler.cli report <university_id>
```

### `status` - Check Checkpoint Status
```bash
python -m pi_crawler.cli status <university_id>
```

### `clear` - Clear Checkpoint Data
```bash
python -m pi_crawler.cli clear <university_id>
```

## Available Configurations

- `univ_hampshire` - University of New Hampshire CS Department (working example)
- `univ_example` - Example configuration for testing

## Output Fields

The system extracts and exports the following fields:

| Field | Description |
|-------|-------------|
| PI Name | Faculty member's full name |
| Qualifications and Certifications | Degrees (PhD, MS, BS, PE, etc.) |
| Title | Academic title |
| About | Comprehensive biography |
| Expertise | Comma-separated keyword phrases |
| Department | Academic department |
| Previous Collaborations & Funding Sources | Grants and collaborations |
| Affiliation | Institution name |
| Public Profile Weblink | All profile URLs |
| Email | Official email |
| Official Phone | Phone number |
| Country of Residence | Country |
| Status | Active/Needs Review/Incomplete |

## Mock Mode

The crawler runs in **mock mode** when `PI_CRAWLER_DB_DSN` is not set:
- All fetching, parsing, and enrichment happens normally
- Instead of saving to PostgreSQL, prints a summary
- Perfect for testing without database setup

## Database Mode

To use PostgreSQL storage:
```bash
export PI_CRAWLER_DB_DSN="postgresql://user:password@host:5432/database"
python -m pi_crawler.cli crawl univ_hampshire
```

## Adding New Universities

1. Create a new JSON config file in `configs/`:
```json
{
  "id": "your_university_id",
  "name": "University Name",
  "department": "Department Name",
  "faculty_list_url": "https://university.edu/faculty",
  "item_selector": ".faculty-item",
  "name_selector": ".faculty-name",
  "title_selector": ".faculty-title",
  "email_selector": "a[href^='mailto:']",
  "profile_link_selector": "a[href*='/faculty/']",
  "research_heading_keywords": ["research", "interests"],
  "request_delay_seconds": 1.0
}
```

2. Run the crawler:
```bash
python -m pi_crawler.cli crawl your_university_id --csv
```

## Directory Structure

```
pi_crawler/
├── pi_crawler/
│   ├── cli.py           # Command-line interface
│   ├── config.py        # Configuration loading
│   ├── models.py        # PIProfile data model
│   ├── fetcher.py       # HTTP fetching with retry
│   ├── parser.py        # HTML parsing
│   ├── enricher.py      # Profile enrichment
│   ├── llm_enricher.py  # Optional LLM enrichment
│   ├── checkpoint.py    # Checkpoint save/load
│   ├── export.py        # CSV/JSON export
│   ├── storage.py       # Database storage
│   └── api.py           # FastAPI endpoint
├── configs/             # University configurations
├── checkpoints/         # Checkpoint files (auto-created)
├── output/              # Exported files (auto-created)
└── TESTING.md           # This file
```

## Cost Comparison

| Method | Cost | Quality |
|--------|------|---------|
| Web Scraping Only | Free | Good |
| Web Scraping + LLM Enrichment | ~$0.01-0.03/profile | Excellent |
| Full LLM with Web Search | ~$0.10-0.30/profile | Best |

The hybrid approach (web scraping + optional LLM enrichment) provides the best balance of cost and quality.
