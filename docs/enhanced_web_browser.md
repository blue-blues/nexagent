# Enhanced Web Browser

The Enhanced Web Browser is a powerful tool for web browsing, data extraction, and information gathering in Nexagent. It provides advanced capabilities for reliable web scraping, even on websites with anti-bot measures.

## Features

### 1. Stealth Mode Browser Configuration

The stealth mode browser configuration helps avoid detection by websites that implement anti-bot measures. It includes:

- WebDriver property manipulation
- User agent rotation
- Random delays to mimic human behavior
- WebGL fingerprinting protection
- Browser plugin emulation
- Language and platform spoofing

### 2. Structured Data Extraction

The Enhanced Web Browser provides robust capabilities for extracting structured data from websites:

- Extract data based on CSS selectors
- Support for various data types (text, links, tables, JSON)
- Schema-based extraction and validation
- Comprehensive extraction mode for maximum data retrieval

### 3. Multi-Source Validation

To ensure data accuracy, the Enhanced Web Browser can extract data from multiple sources and validate it:

- Extract from multiple URLs
- Compare and validate data across sources
- Different validation levels (basic, thorough, strict)
- Confidence scoring for validated data
- Consensus building for text and structured data

### 4. Exponential Backoff Retry Mechanism

For reliable operation, the Enhanced Web Browser implements sophisticated retry mechanisms:

- Exponential backoff for failed requests
- Configurable retry parameters
- Automatic fallback to alternative browser engines
- Detailed logging of retry attempts

## Usage

### Basic Usage

```python
from app.tool.enhanced_web_browser import EnhancedWebBrowser

async def example():
    browser = EnhancedWebBrowser()
    
    try:
        # Enable stealth mode
        await browser.execute(action="enable_stealth_mode")
        
        # Navigate to a URL
        result = await browser.execute(
            action="navigate",
            url="https://example.com"
        )
        
        # Extract data
        result = await browser.execute(
            action="extract_data",
            url="https://example.com",
            data_type="text"
        )
        
        print(result.output)
    
    finally:
        await browser.close()
```

### Structured Data Extraction

```python
# Define a schema for product data
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "price": {"type": "string"},
        "description": {"type": "string"}
    },
    "required": ["title", "price"]
}

# Extract structured data
result = await browser.execute(
    action="extract_structured_data",
    url="https://example.com/product",
    schema=schema
)
```

### Multi-Source Validation

```python
# Define multiple sources
urls = [
    "https://source1.com/data",
    "https://source2.com/data",
    "https://source3.com/data"
]

# Extract and validate data from multiple sources
result = await browser.execute(
    action="multi_source_extract",
    urls=urls,
    data_type="text",
    validation_level="thorough"
)
```

## Configuration

The Enhanced Web Browser can be configured in the `config.toml` file:

```toml
[browser]
# Enhanced web browser settings
stealth_mode = true  # Enable stealth mode to avoid detection
random_delay = true  # Enable random delays to appear more human-like
min_delay = 800  # Minimum delay in milliseconds for random delays
max_delay = 2500  # Maximum delay in milliseconds for random delays
user_agent_rotation = true  # Enable user agent rotation
base_delay = 1.0  # Base delay for exponential backoff retry mechanism
validation_level = "thorough"  # Default validation level for multi-source validation
```

## API Reference

### Actions

The Enhanced Web Browser supports the following actions:

| Action | Description |
|--------|-------------|
| `enable_stealth_mode` | Enable comprehensive stealth mode |
| `disable_stealth_mode` | Disable stealth mode |
| `navigate` | Navigate to a URL with retry mechanism |
| `extract_data` | Extract data from a URL |
| `extract_structured_data` | Extract structured data based on a schema |
| `multi_source_extract` | Extract and validate data from multiple sources |
| `validate_data` | Validate data against a schema |

### Parameters

Common parameters for the Enhanced Web Browser:

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | string | The action to perform |
| `url` | string | The URL to navigate to or extract data from |
| `urls` | array | Multiple URLs to extract and validate data from |
| `selector` | string | CSS selector to extract specific elements |
| `data_type` | string | Type of data to extract (text, links, tables, json, all) |
| `timeout` | integer | Timeout in milliseconds (default: 60000) |
| `max_retries` | integer | Maximum number of retry attempts (default: 3) |
| `validation_level` | string | Level of validation to perform (basic, thorough, strict) |
| `schema` | object | JSON schema for validating extracted data |
