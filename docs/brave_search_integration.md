# Brave Search Integration

This document describes the integration of Brave Search into the Nexagent project.

## Overview

Brave Search is a privacy-focused search engine that provides a powerful API for programmatic access to search results. This integration allows Nexagent to use Brave Search as an alternative to Google, DuckDuckGo, and Baidu search engines.

## Features

- Comprehensive search results with title, URL, and snippet
- Configurable search parameters (language, country, safe search)
- Automatic retry with exponential backoff
- Fallback to other search engines if Brave Search fails

## Configuration

To use Brave Search, you need to obtain an API key from the [Brave Search API](https://brave.com/search/api/) website.

### Setting up the API Key

You can configure the Brave Search API key in two ways:

1. **Environment Variable**:
   ```
   BRAVE_SEARCH_API_KEY=your_api_key_here
   ```

2. **Configuration File**:
   Add the following to your `config.toml` file:
   ```toml
   [search]
   engine = "brave"  # Set Brave as the default search engine (optional)
   brave_api_key = "your_api_key_here"
   ```

### Search Engine Priority

You can set Brave Search as the default search engine by setting the `engine` parameter in the `[search]` section of your `config.toml` file:

```toml
[search]
engine = "brave"
```

If Brave Search is not set as the default, it will be used as a fallback if the default search engine fails.

## Usage

The Brave Search integration is automatically loaded when the WebSearch tool is initialized. You don't need to do anything special to use it.

```python
from app.tools.browser.web_search import WebSearch

async def search_example():
    web_search = WebSearch()
    results = await web_search.execute("your search query")
    for result in results:
        print(result)
```

## Error Handling

The Brave Search integration includes robust error handling:

1. If the API key is not found, Brave Search will be skipped
2. If a request fails, it will be retried up to 3 times with exponential backoff
3. If all retries fail, the system will fall back to other search engines

## Limitations

- The Brave Search API has a maximum of 50 results per request
- API usage is subject to Brave's rate limits and terms of service
- Some features of the Brave Search API (like news and images) are not currently implemented

## Future Enhancements

- Support for additional Brave Search API features (news, images, videos)
- Integration with the enhanced browser tool for more comprehensive search results
- Caching of search results to reduce API usage
