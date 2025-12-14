# PI Crawler

A universal, configuration-driven web scraper for extracting faculty/principal investigator information from university websites.

## Features

- **Universal Compatibility**: Works with any university website through JSON configuration
- **Configuration Validation**: Helpful error messages when configs are misconfigured
- **Pagination Support**: Handles multi-page faculty lists (page params, offsets, or "next" links)
- **Smart Enrichment**: Automatically extracts research interests and personal websites from profile pages
- **Test Mode**: Verify your configuration before running a full crawl
- **Auto-Detection**: The `init` command attempts to detect CSS selectors automatically

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a Configuration

Option A: Use the auto-detect feature:
```bash
python -m pi_crawler.cli init stanford_cs \
  --url "https://cs.stanford.edu/people/faculty" \
  --name "Stanford University" \
  --department "Computer Science"
```

Option B: Copy and edit the template:
```bash
cp configs/_template.json configs/your_university.json
# Edit the file with your CSS selectors
```

### 3. Test Your Configuration

```bash
python -m pi_crawler.cli test your_university
```

### 4. Run the Crawler

```bash
# Dry run (no database save)
python -m pi_crawler.cli crawl your_university --dry-run

# Full crawl
python -m pi_crawler.cli crawl your_university
```

## CLI Commands

```bash
# List all available commands
python -m pi_crawler.cli --help

# List configured universities
python -m pi_crawler.cli list

# Validate all configurations
python -m pi_crawler.cli validate

# Test a specific config
python -m pi_crawler.cli test univ_hampshire

# Crawl with options
python -m pi_crawler.cli crawl univ_hampshire --limit 10 --no-enrich --dry-run
```

## Configuration Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for this config |
| `name` | string | University display name |
| `department` | string | Department name |
| `faculty_list_url` | string | URL of the faculty list page |
| `item_selector` | string | CSS selector for individual faculty items |
| `name_selector` | string | CSS selector for faculty names within each item |
| `research_heading_keywords` | array | Keywords to identify research sections |
| `request_delay_seconds` | number | Delay between requests (use >= 1.0) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `title_selector` | string | CSS selector for faculty titles |
| `email_selector` | string | CSS selector for email links |
| `profile_link_selector` | string | CSS selector for profile page links |
| `personal_website_selector` | string | CSS selector for personal website links |
| `research_text_selector` | string | CSS selector for research text |
| `enrichment_enabled` | boolean | Enable/disable profile page fetching (default: true) |
| `pagination` | object | Pagination configuration (see below) |

### Pagination Configuration

For faculty lists that span multiple pages:

```json
{
  "pagination": {
    "enabled": true,
    "type": "page_param",
    "param_name": "page",
    "start_value": 1,
    "increment": 1,
    "max_pages": 50,
    "stop_when_empty": true
  }
}
```

Pagination types:
- `page_param`: URL parameter like `?page=1`, `?page=2`
- `offset_param`: URL parameter like `?offset=0`, `?offset=20`
- `next_link`: Follow "next" links using a CSS selector

## Finding CSS Selectors

1. Open the faculty list page in your browser
2. Right-click on a faculty member's name and select "Inspect"
3. Look for a container element that wraps each faculty member (this is your `item_selector`)
4. Within that container, find the name element (this is your `name_selector`)

### Common Selector Patterns

```json
{
  "item_selector": ".faculty-card",
  "name_selector": ".faculty-name",
  "title_selector": ".faculty-title",
  "email_selector": "a[href^='mailto:']",
  "profile_link_selector": "a.profile-link"
}
```

### Selector Tips

- Use class selectors (`.classname`) when possible
- Use attribute selectors for emails: `a[href^='mailto:']`
- For profile links: `a[href*='/faculty/']` matches links containing "/faculty/"
- Test selectors in browser DevTools: `document.querySelectorAll('.your-selector')`

## Database Setup (Optional)

To save profiles to PostgreSQL, set the environment variable:

```bash
export PI_CRAWLER_DB_DSN="postgresql://user:pass@localhost/dbname"
```

Without this, profiles are printed to the console (mock mode).

## Example Configuration

```json
{
  "id": "mit_eecs",
  "name": "Massachusetts Institute of Technology",
  "department": "Electrical Engineering and Computer Science",
  "faculty_list_url": "https://www.eecs.mit.edu/people/faculty-advisors",
  "item_selector": ".person-card",
  "name_selector": ".person-card__name",
  "title_selector": ".person-card__title",
  "email_selector": "a[href^='mailto:']",
  "profile_link_selector": ".person-card__name a",
  "research_heading_keywords": ["research", "interests", "areas"],
  "request_delay_seconds": 1.5
}
```

## Troubleshooting

### No profiles found

1. Run `python -m pi_crawler.cli test your_config` to see diagnostic info
2. Verify your `item_selector` matches elements on the page
3. Verify your `name_selector` finds names within those elements
4. Test selectors in browser DevTools

### Rate limiting / 403 errors

- Increase `request_delay_seconds` (try 2.0 or higher)
- Some sites may block automated requests entirely

### Profile enrichment not finding data

- Check `research_heading_keywords` match the page's section headers
- Try adding more keywords like "expertise", "specialization", "focus"
- Some profile pages may use non-standard layouts

## License

MIT
