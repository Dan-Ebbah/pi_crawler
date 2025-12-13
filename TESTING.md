# PICrawler Testing Guide
## Running the Crawler
The correct command syntax is:
```bash
python -m pi_crawler.cli <university_id>
```
**NOT** `python -m pi_crawler.cli crawl <university_id>` - there is no "crawl" subcommand.
## Available Configurations
- `univ_hampshire` - University of New Hampshire CS Department (real, working)
- `univ_example` - Example configuration (fake URL for testing)
## Examples
```bash
# Crawl UNH Computer Science faculty
python -m pi_crawler.cli univ_hampshire
# Try example config (will fail to fetch)
python -m pi_crawler.cli univ_example
```
## Mock Mode
The crawler runs in mock mode when `PI_CRAWLER_DB_DSN` environment variable is not set. In this mode:
- All fetching, parsing, and enrichment happens normally
- Instead of saving to PostgreSQL, it prints a summary of what would be saved
- Perfect for testing without database setup
## Database Mode
To use a real database, set the connection string:
```bash
export PI_CRAWLER_DB_DSN="postgresql://user:password@host:5432/database"
python -m pi_crawler.cli univ_hampshire
```
## Recent Fixes
1. **Parser fix**: Changed `item.select()` to `item.select_one()` for name selector to avoid calling `.get_text()` on a list
2. **Model fix**: Removed unused `phone` field and made `email` Optional to match actual parsing behavior
3. **Storage mock**: Added mock mode to allow testing without database connection
