"""
Extractor system for flexible data extraction from HTML.

Supports multiple extraction strategies with fallback chains.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
import re
import logging

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for all extractors."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize extractor with configuration.
        
        Args:
            config: Dictionary containing extractor configuration
        """
        self.config = config
        self.strategy = config.get("strategy", "")
        
    @abstractmethod
    def extract(self, soup: BeautifulSoup, base_url: Optional[str] = None) -> Optional[str]:
        """
        Extract data from the parsed HTML.
        
        Args:
            soup: BeautifulSoup object or Tag to extract from
            base_url: Base URL for resolving relative URLs
            
        Returns:
            Extracted string value or None if extraction failed
        """
        pass


class CSSExtractor(BaseExtractor):
    """Extract data using CSS selectors."""
    
    def extract(self, soup: BeautifulSoup, base_url: Optional[str] = None) -> Optional[str]:
        """
        Extract using CSS selector.
        
        Config keys:
            - selector: CSS selector string
            - attribute: "text" for text content, or attribute name (e.g., "href")
        """
        selector = self.config.get("selector")
        attribute = self.config.get("attribute", "text")
        
        if not selector:
            logger.warning("CSSExtractor: No selector provided")
            return None
            
        element = soup.select_one(selector)
        if not element:
            return None
            
        if attribute == "text":
            text = element.get_text(strip=True)
            return text if text else None
        else:
            # Extract attribute value
            if element.has_attr(attribute):
                value = element[attribute]
                # Handle list attributes
                if isinstance(value, list):
                    value = " ".join(value)
                return value.strip() if value else None
        
        return None


class XPathExtractor(BaseExtractor):
    """Extract data using XPath expressions."""
    
    def extract(self, soup: BeautifulSoup, base_url: Optional[str] = None) -> Optional[str]:
        """
        Extract using XPath selector.
        
        Config keys:
            - selector: XPath expression
        
        Note: Requires lxml parser support
        """
        selector = self.config.get("selector")
        
        if not selector:
            logger.warning("XPathExtractor: No selector provided")
            return None
        
        try:
            # Try to use lxml if available
            from lxml import etree
            
            # Convert BeautifulSoup to lxml
            if isinstance(soup, Tag):
                html_str = str(soup)
            else:
                html_str = str(soup)
            
            tree = etree.HTML(html_str)
            results = tree.xpath(selector)
            
            if results:
                # Return first result
                result = results[0]
                if isinstance(result, str):
                    return result.strip() if result else None
                elif hasattr(result, 'text'):
                    text = result.text
                    return text.strip() if text else None
                else:
                    return str(result).strip() if result else None
        except ImportError:
            logger.warning("XPathExtractor: lxml not installed, XPath not supported")
        except Exception as e:
            logger.debug(f"XPathExtractor failed: {e}")
            
        return None


class HeadingSectionExtractor(BaseExtractor):
    """Extract content following specific headings (e.g., "Research Interests")."""
    
    def extract(self, soup: BeautifulSoup, base_url: Optional[str] = None) -> Optional[str]:
        """
        Extract content following a heading that matches keywords.
        
        Config keys:
            - keywords: List of keywords to search in headings
            - content_type: "ul" for list items, "p" for paragraph, "all" for both
        """
        keywords = self.config.get("keywords", [])
        content_type = self.config.get("content_type", "ul")
        
        if not keywords:
            logger.warning("HeadingSectionExtractor: No keywords provided")
            return None
        
        # Normalize keywords to lowercase
        keywords = [kw.lower() for kw in keywords]
        
        # Find heading that contains any of the keywords
        heading = soup.find(
            lambda tag: tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"] 
            and any(kw in tag.get_text(strip=True).lower() for kw in keywords)
        )
        
        if not heading:
            return None
        
        # Extract content based on type
        if content_type == "ul":
            ul = heading.find_next("ul")
            if ul:
                items = [li.get_text(strip=True) for li in ul.find_all("li")]
                items = [item for item in items if item]
                if items:
                    return " | ".join(items)
        
        elif content_type == "p":
            p = heading.find_next("p")
            if p:
                text = p.get_text(strip=True)
                return text if text else None
        
        elif content_type == "all":
            # Try ul first, then p
            ul = heading.find_next("ul")
            if ul:
                items = [li.get_text(strip=True) for li in ul.find_all("li")]
                items = [item for item in items if item]
                if items:
                    return " | ".join(items)
            
            p = heading.find_next("p")
            if p:
                text = p.get_text(strip=True)
                return text if text else None
        
        return None


class RegexExtractor(BaseExtractor):
    """Extract data using regular expressions."""
    
    def extract(self, soup: BeautifulSoup, base_url: Optional[str] = None) -> Optional[str]:
        """
        Extract using regex pattern.
        
        Config keys:
            - pattern: Regular expression pattern
            - group: Capture group index (default: 0 for full match)
        """
        pattern = self.config.get("pattern")
        group = self.config.get("group", 0)
        
        if not pattern:
            logger.warning("RegexExtractor: No pattern provided")
            return None
        
        # Get all text from soup
        text = soup.get_text(strip=True) if hasattr(soup, 'get_text') else str(soup)
        
        try:
            match = re.search(pattern, text)
            if match:
                return match.group(group)
        except Exception as e:
            logger.debug(f"RegexExtractor failed: {e}")
        
        return None


class ExtractorFactory:
    """Factory for creating extractors based on strategy."""
    
    _extractors = {
        "css": CSSExtractor,
        "xpath": XPathExtractor,
        "heading_section": HeadingSectionExtractor,
        "regex": RegexExtractor,
    }
    
    @classmethod
    def create(cls, config: Dict[str, Any]) -> Optional[BaseExtractor]:
        """
        Create an extractor instance based on config.
        
        Args:
            config: Extractor configuration dictionary
            
        Returns:
            Extractor instance or None if strategy not recognized
        """
        strategy = config.get("strategy", "").lower()
        extractor_class = cls._extractors.get(strategy)
        
        if extractor_class:
            return extractor_class(config)
        
        logger.warning(f"Unknown extraction strategy: {strategy}")
        return None
    
    @classmethod
    def register(cls, strategy: str, extractor_class: type):
        """Register a custom extractor class."""
        cls._extractors[strategy] = extractor_class


def extract_field(
    soup: BeautifulSoup,
    field_config: Dict[str, Any],
    base_url: Optional[str] = None,
) -> Optional[str]:
    """
    Extract a field value using fallback chain of extractors.
    
    Args:
        soup: BeautifulSoup object to extract from
        field_config: Field configuration with extractors list
        base_url: Base URL for resolving relative URLs
        
    Returns:
        Extracted value or None if all extractors failed
    """
    extractors = field_config.get("extractors", [])
    
    for i, extractor_config in enumerate(extractors):
        extractor = ExtractorFactory.create(extractor_config)
        if not extractor:
            continue
        
        try:
            value = extractor.extract(soup, base_url)
            if value:
                logger.debug(f"Extractor {i+1} ({extractor_config.get('strategy')}) succeeded")
                return value
        except Exception as e:
            logger.debug(f"Extractor {i+1} failed: {e}")
            continue
    
    logger.debug(f"All extractors failed for field")
    return None
