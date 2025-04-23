# Enhanced Web Browsing Features

This document describes the enhanced web browsing features implemented in Phase 2 of the Devika-inspired features for Nexagent.

## Overview

The enhanced web browsing features provide advanced capabilities for web scraping, data extraction, and anti-detection measures. These features are designed to make Nexagent more effective at gathering information from the web, even from websites with anti-scraping measures.

## Features

### 1. Enhanced Stealth Mode

The enhanced stealth mode provides comprehensive anti-detection measures to avoid being blocked by websites:

- **WebDriver Property Manipulation**: Removes or modifies properties that websites use to detect automation
- **Plugin and Mimetype Emulation**: Adds realistic browser plugins and mimetypes to mimic a real browser
- **WebGL Fingerprinting Protection**: Modifies WebGL parameters to prevent fingerprinting
- **Canvas Fingerprinting Protection**: Adds slight noise to canvas data to prevent fingerprinting
- **User Agent Rotation**: Automatically rotates user agents to appear as different browsers
- **Random Delays**: Adds random delays between actions to mimic human behavior

### 2. Structured Data Extraction

The structured data extractor can extract various types of structured data from web pages:

- **JSON-LD**: Extracts JSON-LD data from script tags
- **Microdata**: Extracts Microdata from HTML elements with itemscope attributes
- **RDFa**: Extracts RDFa data from HTML elements with RDFa attributes
- **Custom Extraction Patterns**: Extracts data using custom patterns for specific websites

### 3. Brave Search Integration

Brave Search is now integrated as an alternative search engine:

- **API-Based Search**: Uses the Brave Search API for more accurate and up-to-date results
- **Configurable Parameters**: Supports language, country, and safe search parameters
- **Automatic Retry**: Implements retry logic with exponential backoff
- **Fallback Mechanism**: Automatically falls back to other search engines if Brave Search fails

### 4. Anti-Scraping Measures Handling

The enhanced browser tool includes several features to handle anti-scraping measures:

- **Cloudflare Bypass**: Attempts to bypass Cloudflare protection
- **CAPTCHA Detection**: Detects and handles CAPTCHAs
- **Request Throttling**: Limits the rate of requests to avoid being blocked
- **User Agent Rotation**: Rotates user agents to appear as different browsers

## Usage

### Enhanced Stealth Mode

```python
from app.tools.browser.enhanced_browser_tool import EnhancedBrowserTool

async def example():
    browser = EnhancedBrowserTool()
    
    # Enable stealth mode
    await browser.execute(action="stealth_mode", enable=True)
    
    # Configure random delays
    await browser.execute(action="random_delay", min_delay=800, max_delay=2500)
    
    # Rotate user agent
    await browser.execute(action="rotate_user_agent")
    
    # Navigate to a URL
    await browser.execute(action="navigate", url="https://example.com")
```

### Structured Data Extraction

```python
from app.tools.browser.enhanced_browser_tool import EnhancedBrowserTool

async def extract_structured_data():
    browser = EnhancedBrowserTool()
    
    # Navigate to a URL
    await browser.execute(action="navigate", url="https://example.com")
    
    # Extract structured data
    result = await browser.execute(
        action="extract_structured_data",
        extraction_type="all"  # Can be "jsonld", "microdata", "rdfa", "custom", or "all"
    )
    
    print(result.output)
```

### Brave Search

```python
from app.tools.browser.web_search import WebSearch

async def search_example():
    web_search = WebSearch()
    
    # Perform a search (will use Brave Search if configured as default)
    results = await web_search.execute(
        query="your search query",
        num_results=10
    )
    
    for result in results:
        print(result)
```

## Configuration

### Brave Search Configuration

To use Brave Search, you need to obtain an API key from the [Brave Search API](https://brave.com/search/api/) website and configure it in your `config.toml` file:

```toml
[search]
engine = "brave"  # Set Brave as the default search engine (optional)
brave_api_key = "your_api_key_here"
```

### Enhanced Browser Configuration

You can configure the enhanced browser tool in your `config.toml` file:

```toml
[browser]
# Enhanced web browser settings
stealth_mode = true  # Enable stealth mode to avoid detection
random_delay = true  # Enable random delays to appear more human-like
min_delay = 800  # Minimum delay in milliseconds for random delays
max_delay = 2500  # Maximum delay in milliseconds for random delays
user_agent_rotation = true  # Enable user agent rotation
```

## Limitations

- Some websites may still detect and block automated browsing despite stealth mode
- Structured data extraction depends on the structure of the website and may not work for all websites
- Brave Search API has usage limits and requires an API key
- Anti-scraping measures are constantly evolving, and the effectiveness of these features may vary over time

## Future Enhancements

- Add support for more structured data formats
- Implement more advanced anti-detection measures
- Add support for more search engines
- Implement more advanced CAPTCHA solving capabilities
- Add support for more complex web interactions
