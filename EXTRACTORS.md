# Enhanced Extractor System

The PI Crawler now supports an enhanced extractor system that provides:
- Multiple extraction strategies (CSS, XPath, Regex, Heading Sections)
- Fallback selector chains for robust data extraction
- Field-level validation with regex patterns
- Data transformations (strip_mailto, absolute_url, etc.)
- Template-based configuration inheritance
- Backward compatibility with old config format

## Quick Start

### Old Format (Still Supported)
```json
{
  "id": "example_cs",
  "name": "Example University",
  "department": "Computer Science",
  "faculty_list_url": "https://cs.example.edu/faculty",
  "item_selector": ".faculty-card",
  "name_selector": ".faculty-name",
  "email_selector": "a[href^='mailto:']",
  "research_heading_keywords": ["research", "interests"],
  "request_delay_seconds": 1.0
}
```

### New Format (Enhanced)
```json
{
  "id": "example_cs_new",
  "name": "Example University",
  "department": "Computer Science",
  "template": "standard_faculty_list",
  "faculty_list_url": "https://cs.example.edu/faculty",
  
  "list_item": {
    "selectors": [".faculty-card", ".profile-item"],
    "strategy": "css"
  },
  
  "fields": {
    "full_name": {
      "extractors": [
        {"strategy": "css", "selector": ".faculty-name", "attribute": "text"},
        {"strategy": "css", "selector": ".profile-name", "attribute": "text"}
      ],
      "required": true
    },
    "email": {
      "extractors": [
        {"strategy": "css", "selector": "a[href^='mailto:']", "attribute": "href", "transform": "strip_mailto"}
      ],
      "validation": "^[\\w.-]+@[\\w.-]+\\.\\w+$"
    }
  },
  
  "profile_page": {
    "enabled": true,
    "fields": {
      "raw_research_text": {
        "extractors": [
          {"strategy": "heading_section", "keywords": ["research", "interests"], "content_type": "ul"}
        ]
      }
    }
  }
}
```

## Extraction Strategies

### 1. CSS Extractor
Uses CSS selectors to extract data from HTML.

```json
{
  "strategy": "css",
  "selector": ".faculty-name",
  "attribute": "text"
}
```

**Attributes:**
- `text` - Extract text content
- `href` - Extract href attribute
- Any HTML attribute name

### 2. XPath Extractor
Uses XPath expressions (requires lxml).

```json
{
  "strategy": "xpath",
  "selector": ".//a[contains(text(), 'Profile')]/@href"
}
```

### 3. Heading Section Extractor
Extracts content following headings (e.g., "Research Interests").

```json
{
  "strategy": "heading_section",
  "keywords": ["research", "interests"],
  "content_type": "ul"
}
```

**Content Types:**
- `ul` - Extract list items
- `p` - Extract paragraph text
- `all` - Try ul first, then p

### 4. Regex Extractor
Extracts data using regular expressions.

```json
{
  "strategy": "regex",
  "pattern": "Email:\\s*([\\w.-]+@[\\w.-]+\\.\\w+)",
  "group": 1
}
```

## Fallback Chains

The extractor system tries each extractor in order until one succeeds:

```json
{
  "full_name": {
    "extractors": [
      {"strategy": "css", "selector": ".faculty-name", "attribute": "text"},
      {"strategy": "css", "selector": ".profile-name", "attribute": "text"},
      {"strategy": "css", "selector": "h3.name", "attribute": "text"}
    ]
  }
}
```

This makes the crawler more robust when universities have different HTML structures.

## Transformations

Apply transformations to extracted values:

### Available Transforms
- `strip_mailto` - Remove "mailto:" prefix from emails
- `absolute_url` - Convert relative URLs to absolute
- `strip_whitespace` - Remove leading/trailing whitespace
- `normalize_whitespace` - Convert multiple spaces to single space
- `lowercase` - Convert to lowercase
- `uppercase` - Convert to uppercase

### Usage

**Field-level transform:**
```json
{
  "profile_url": {
    "extractors": [...],
    "transform": "absolute_url"
  }
}
```

**Extractor-level transform:**
```json
{
  "email": {
    "extractors": [
      {"strategy": "css", "selector": "a[href^='mailto:']", "attribute": "href", "transform": "strip_mailto"}
    ]
  }
}
```

## Validation

Validate extracted data with regex patterns:

```json
{
  "email": {
    "extractors": [...],
    "required": false,
    "validation": "^[\\w.-]+@[\\w.-]+\\.\\w+$"
  }
}
```

**Validation Options:**
- `required: true/false` - Whether field must have a value
- `validation: "pattern"` - Regex pattern to validate against

Failed validations are logged as warnings.

## Template Inheritance

Create reusable configuration templates:

**Template:** `configs/templates/standard_faculty_list.json`
```json
{
  "list_item": {
    "selectors": [".faculty-card", ".profile-item"],
    "strategy": "css"
  },
  "fields": {
    "full_name": {
      "extractors": [
        {"strategy": "css", "selector": ".faculty-name", "attribute": "text"}
      ]
    }
  }
}
```

**University Config:**
```json
{
  "id": "mit_cs",
  "name": "MIT",
  "template": "standard_faculty_list",
  "faculty_list_url": "https://mit.edu/faculty",
  
  "fields": {
    "full_name": {
      "extractors": [
        {"strategy": "css", "selector": ".mit-faculty-name", "attribute": "text"}
      ]
    }
  }
}
```

Config values override template values via deep merge.

## Profile Page Extraction

Extract additional data from individual profile pages:

```json
{
  "profile_page": {
    "enabled": true,
    "fields": {
      "personal_website_url": {
        "extractors": [
          {"strategy": "css", "selector": "a:contains('website')", "attribute": "href"}
        ]
      },
      "raw_research_text": {
        "extractors": [
          {"strategy": "heading_section", "keywords": ["research"], "content_type": "ul"}
        ]
      }
    }
  }
}
```

## Logging and Debugging

The extractor system logs extraction attempts at DEBUG level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

You'll see messages like:
```
DEBUG:pi_crawler.extractors:Extractor 2 (css) succeeded
WARNING:pi_crawler.validators:Required field 'full_name' is missing or empty
WARNING:pi_crawler.validators:Field 'email' value 'invalid' does not match validation pattern
```

## Migration Guide

### Converting Old Configs to New Format

**Old:**
```json
{
  "item_selector": ".faculty-card",
  "name_selector": ".faculty-name",
  "email_selector": "a[href^='mailto:']"
}
```

**New:**
```json
{
  "list_item": {
    "selectors": [".faculty-card"]
  },
  "fields": {
    "full_name": {
      "extractors": [
        {"strategy": "css", "selector": ".faculty-name", "attribute": "text"}
      ],
      "required": true
    },
    "email": {
      "extractors": [
        {"strategy": "css", "selector": "a[href^='mailto:']", "attribute": "href", "transform": "strip_mailto"}
      ]
    }
  }
}
```

### Benefits of New Format

1. **Fallback chains** - Add multiple selectors as backups
2. **Validation** - Catch data quality issues early
3. **Transforms** - Cleaner data extraction
4. **Templates** - Reuse common patterns
5. **Better debugging** - See which extractors work/fail

## Examples

See example configs:
- `configs/univ_example.json` - Old format (still works)
- `configs/univ_example_new.json` - New format example
- `configs/univ_hampshire_new.json` - Real university with new format
- `configs/templates/standard_faculty_list.json` - Reusable template
