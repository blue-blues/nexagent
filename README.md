# Nexagent: Advanced Intelligent Web Scraping Agent

<div align="center">
  <img src="https://github.com/blue-blues/nexagent/raw/main/assets/nexagent-logo.png" alt="Nexagent Logo" width="250"/>
  <br>
  <br>
  <strong>A versatile AI agent with state-of-the-art web scraping capabilities</strong>
  <br>
  <br>
</div>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)
[![GitHub stars](https://img.shields.io/github/stars/blue-blues/nexagent?style=social)](https://github.com/blue-blues/nexagent/stargazers)

## 🚀 Overview

Nexagent is a powerful, intelligent agent that specializes in comprehensive web extraction and data processing. Built on a solid agent framework, Nexagent stands out for its exceptional ability to:

- **Extract complete web content** from even the most complex websites
- **Dynamically adapt** to different site structures and anti-scraping measures
- **Process information** intelligently with flexible step planning
- **Handle pagination and infinite scroll** sites automatically
- **Navigate complex web applications** with intelligent fallback mechanisms

## 🌟 Key Features

### Advanced Web Scraping

- **Comprehensive extraction modes**: From basic text to full structured page content
- **Stealth browsing**: Undetectable browsing with advanced anti-detection bypasses
- **Infinite scroll handling**: Automatically detects and loads dynamically loaded content
- **Pagination detection**: Identifies and follows multi-page content
- **Content structure preservation**: Maintains original document hierarchy and relationships

### Intelligent Processing

- **Dynamic step planning**: Automatically calculates appropriate step limits based on task complexity
- **Multi-level fallback**: Gracefully handles failures with multiple retry strategies
- **Self-healing navigation**: Adapts to site changes and connection issues automatically
- **Content-focused extraction**: Intelligently identifies and prioritizes main content

### Flexible Architecture

- **Modular tool system**: Easily extensible with new capabilities
- **Multiple extraction strategies**: Extract exactly what you need, from text to full DOM
- **Configurable behavior**: Fine-tune scraping behavior to suit different sites

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/blue-blues/nexagent.git
cd nexagent

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Configuration

Nexagent requires minimal configuration to get started:

1. Create a `config.toml` file in the `config` directory:

```bash
cp config/config.example.toml config/config.toml
```

2. Edit the configuration file to add any required API keys:

```toml
# LLM model configuration (if using LLM capabilities)
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Your API key
max_tokens = 4096
temperature = 0.0

# Browser configuration
[browser]
headless = false  # Set to true for production use
timeout = 30000   # Default timeout in milliseconds
```

## 🔍 Usage Examples

### Basic Web Scraping

```python
from nexagent import Nexagent

async def main():
    agent = Nexagent()
    
    # Launch a basic scraping task
    result = await agent.run("Extract all product information from https://example.com/products")
    print(result)
    
    await agent.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Comprehensive Web Extraction

```python
from nexagent.tool.enhanced_browser_tool import EnhancedBrowserTool

async def extract_complete_website():
    browser = EnhancedBrowserTool()
    
    try:
        # Enable stealth mode to avoid detection
        await browser.execute(action="stealth_mode", enable=True)
        
        # Use random delays to appear more human-like
        await browser.execute(action="random_delay", min_delay=800, max_delay=2500)
        
        # Extract comprehensive data
        result = await browser.execute(
            action="navigate_and_extract",
            url="https://example.com/complex-site",
            extract_type="comprehensive"  # Use the most thorough extraction mode
        )
        
        # Process and save the results
        import json
        with open("extraction_results.json", "w") as f:
            content = result.output.split("\n\n", 1)[1]  # Skip the success message
            f.write(content)
            print("Extraction complete. Results saved.")
            
    finally:
        await browser.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(extract_complete_website())
```

## 📊 Advanced Usage

### Handling Infinite Scroll Pages

Nexagent automatically detects and handles infinite scroll pages:

```python
result = await browser.execute(
    action="navigate_and_extract",
    url="https://example.com/infinite-scroll-gallery",
    extract_type="comprehensive",
    timeout=60000  # Allow more time for scrolling and loading
)
```

### Following Pagination

```python
async def extract_all_pages(base_url):
    browser = EnhancedBrowserTool()
    all_results = []
    
    try:
        current_url = base_url
        page = 1
        
        while True:
            print(f"Processing page {page}: {current_url}")
            
            result = await browser.execute(
                action="navigate_and_extract",
                url=current_url,
                extract_type="comprehensive"
            )
            
            # Process this page's results
            content = json.loads(result.output.split("\n\n", 1)[1])
            all_results.append(content)
            
            # Check for pagination
            if "pagination" in content and content["pagination"].get("paginationLinks"):
                # Find the "next" link
                next_link = None
                for link in content["pagination"]["paginationLinks"]:
                    if link.get("isNext"):
                        next_link = link["href"]
                        break
                
                if next_link:
                    current_url = next_link
                    page += 1
                else:
                    print("No more pages found.")
                    break
            else:
                print("No pagination detected.")
                break
    
    finally:
        await browser.close()
    
    return all_results
```

## 🧩 Component Reference

### EnhancedBrowserTool

The core web scraping component with the following main actions:

| Action | Description |
|--------|-------------|
| `navigate` | Navigate to a URL |
| `navigate_and_extract` | Navigate and extract content in one step |
| `stealth_mode` | Enable/disable stealth browsing |
| `random_delay` | Set random delays between actions |
| `extract_structured` | Extract structured data from the page |
| `get_text` | Get text content from the current page |
| `get_html` | Get HTML content from the current page |

### Nexagent

The high-level agent that manages the entire extraction process:

- Dynamically calculates appropriate step limits based on task complexity
- Provides multi-level fallbacks for robust operation
- Manages browser sessions and resources automatically

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- Special thanks to the [OpenManus](https://github.com/mannaandpoem/OpenManus) team for inspiration
- Built with [browser-use](https://github.com/browser-use/browser-use) for foundational browser automation
