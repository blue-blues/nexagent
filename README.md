# Nexagent: Advanced Intelligent Agent

<div align="center">
  <img src="https://github.com/blue-blues/nexagent/raw/main/assets/nexagent-logo.png" alt="Nexagent Logo" width="250"/>
  <br>
  <br>
  <strong>A versatile AI agent with state-of-the-art capabilities</strong>
  <br>
  <br>
</div>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)
[![GitHub stars](https://img.shields.io/github/stars/blue-blues/nexagent?style=social)](https://github.com/blue-blues/nexagent/stargazers)

## 🚀 Overview

Nexagent is a powerful, intelligent agent framework that offers multiple specialized assistants. Built on a solid agent architecture, Nexagent stands out for its exceptional abilities:

### General-Purpose Assistant
- **Extract complete content** from even the most complex sources
- **Dynamically adapt** to different structures and anti-extraction measures
- **Process information** intelligently with flexible step planning
- **Handle complex data structures** automatically
- **Navigate complex applications** with intelligent fallback mechanisms

### Software Development Assistant
- **Generate high-quality code** across multiple programming languages
- **Debug and optimize** existing codebases automatically
- **Design software architecture** with best practices and patterns
- **Integrate APIs** and external services seamlessly
- **Create automated tests** and ensure code quality

## 🌟 Key Features

### Advanced Data Extraction

- **Comprehensive extraction modes**: From basic text to full structured content
- **Stealth operation**: Undetectable operation with advanced anti-detection bypasses
- **Complex data handling**: Automatically detects and processes dynamically loaded content
- **Structure preservation**: Maintains original document hierarchy and relationships

### Intelligent Processing

- **Dynamic step planning**: Automatically calculates appropriate step limits based on task complexity
- **Multi-level fallback**: Gracefully handles failures with multiple retry strategies
- **Self-healing navigation**: Adapts to changes and connection issues automatically
- **Content-focused extraction**: Intelligently identifies and prioritizes main content
- **Smart response handling**: Provides direct answers to simple queries without invoking the full agent system

### Flexible Architecture

- **Modular tool system**: Easily extensible with new capabilities
- **Multiple extraction strategies**: Extract exactly what you need, from text to full data structures
- **Configurable behavior**: Fine-tune operation behavior to suit different sources
- **Enhanced data formatting**: Output data in multiple human-readable formats (JSON, YAML, CSV, tables)

### Plan Versioning System

- **Version control for plans**: Create, manage, and version plans for complex tasks
- **Version comparison**: Compare different versions to see what has changed
- **Rollback capability**: Roll back to previous versions if needed
- **Version history**: Track the history of changes to a plan
- **Version tagging**: Tag important versions for easy reference

### Adaptive Learning System

- **Interaction memory**: Stores and indexes past interactions for future reference
- **Performance analytics**: Analyzes performance across different tasks to identify strengths and weaknesses
- **Strategy adaptation**: Dynamically adjusts approach based on past performance data
- **Knowledge distillation**: Extracts generalizable knowledge from specific experiences
- **Feedback integration**: Incorporates explicit and implicit user feedback to guide learning

### Terminal UI Component

- **Syntax highlighting**: Automatically highlights code based on language detection
- **Command history**: Tracks and allows reuse of previous commands
- **Autocomplete functionality**: Suggests commands as you type
- **Code folding**: Collapse and expand code sections for better readability
- **Multiple tabs**: Work with multiple terminal sessions simultaneously
- **Search and replace**: Find and modify text within the terminal

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

# Check if all required dependencies are installed
python check_dependencies.py
```

## 🚀 Running Nexagent

### CLI Mode

```bash
# Run in CLI mode with the legacy interface
python main.py

# Run in CLI mode with the new architecture
python main.py --new

> Enter prompt <
```

Nexagent now operates exclusively through a command-line interface for improved performance and reliability. The web interface has been removed in favor of a more streamlined terminal-based experience.

### New Architecture

Nexagent has been redesigned with a new modular architecture that follows a layered approach:

1. **Core Layer**: Provides foundational functionality like LLM interfaces, context management, schema definitions, and versioned memory.
2. **Agent Layer**: Implements the agent loop and various agent types including TaskBasedNexagent, ManusAgent, and SWEAgent.
3. **Tools Layer**: Provides tools that agents can use to interact with the world, organized by functionality (browser, code, terminal, etc.).
4. **UI Layer**: Provides user interfaces for interacting with the system through CLI.
5. **Integration Layer**: Provides integration points with external systems and the Adaptive Learning System.

The new architecture offers several advantages:
- **Improved modularity**: Each component has a clear responsibility and can be replaced independently
- **Better extensibility**: New agent types and tools can be added without modifying existing code
- **Enhanced maintainability**: Clear separation of concerns makes the codebase easier to understand and maintain
- **Adaptive learning**: The system can learn from past interactions and improve over time

To use the new architecture, run the application with the `--new` flag:

```bash
python main.py --new
```

You can also run the simple agent example to see the new architecture in action:

```bash
python examples/simple_agent_example.py
```

### Terminal UI Component

```bash
# Run the Terminal UI Component demo
python run_terminal_ui.py
```

The Terminal UI Component provides a rich terminal interface with syntax highlighting, command history, autocomplete, code folding, and multiple tabs.

#### Terminal UI Commands

```
# Tab management
tab <tab_name> - Create a new tab with the specified name
new-tab - Create a new tab with a default name
list-tabs - List all tabs
switch-tab <tab_name> - Switch to the specified tab
close-tab [tab_name] - Close the specified tab or the active tab if not specified

# History and navigation
history - Show command history
clear - Clear the terminal screen

# Exit
exit, quit - Exit the Terminal UI
```

### CLI Commands

```
# Basic commands
stats - Show routing statistics
upload <file_path> - Upload and process a file
attach <file_path> - Attach a file to your next message
plan - Access the plan versioning system
exit - Quit the application

# Plan versioning commands
plan help - Show help for plan commands
plan list - List all plans
plan create <plan_id> <title> - Create a new plan
plan get <plan_id> - Get a plan
plan update <plan_id> <title> - Update a plan
plan version create <plan_id> <version_id> <description> - Create a version
plan version list <plan_id> - List versions of a plan
plan version get <plan_id> <version_id> - Get a specific version
plan version compare <plan_id> <version_id1> <version_id2> - Compare versions
plan version rollback <plan_id> <version_id> - Rollback to a version
plan version history <plan_id> - Get version history
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

# Adaptive Learning System configuration
[adaptive_learning]
enabled = true
storage_path = "data/adaptive_learning"
backup_enabled = true
backup_frequency_hours = 24
max_backups = 7

# Feedback configuration
[adaptive_learning.feedback]
explicit_feedback_weight = 2.0
implicit_feedback_weight = 1.0
feedback_history_size = 100
```

### Advanced Configuration

For more advanced configuration options, see the [installation guide](docs/installation.md).


## Examples
Given Prompt to Nexagent
```
Identify the top-performing small- and mid-cap stocks with strong growth potential.
Consider key financial metrics such as revenue growth, earnings per share (EPS), price-to-earnings (P/E) ratio, return on equity (ROE), and
debt-to-equity ratio. Analyze technical indicators like moving averages, relative strength index (RSI), and trading volume trends.
Additionally, assess industry trends, recent news, and market sentiment to refine stock selection. Provide a ranked list of the top 10 stocks
with a brief justification for each pick and create list and save to local
```

Given Results by Nexagent (JSON Format)
```json
{
  "top_performing_stocks": [
    {
      "rank": 1,
      "name": "Persistent Systems",
      "ticker": "PERSISTENT.NS",
      "sector": "Technology",
      "industry": "Software",
      "market_cap": "$4.2B",
      "growth_metrics": {
        "revenue_growth": "24.3%",
        "eps_growth": "32.1%",
        "pe_ratio": 28.5,
        "roe": "21.4%",
        "debt_to_equity": 0.12
      },
      "technical_indicators": {
        "rsi": 62,
        "50day_ma": "Above",
        "200day_ma": "Above",
        "volume_trend": "Increasing"
      },
      "justification": "Strong revenue growth in enterprise software with expanding profit margins and low debt."
    },
    {
      "rank": 2,
      "name": "Tata Elxsi",
      "ticker": "TATAELXSI.NS",
      "sector": "Technology",
      "industry": "Design Services",
      "market_cap": "$5.1B"
    },
    {
      "rank": 3,
      "name": "Zensar Technologies",
      "ticker": "ZENSARTECH.NS",
      "sector": "Technology",
      "industry": "IT Services",
      "market_cap": "$1.8B"
    }
  ],
  "sectors_to_research": [
    "Healthcare",
    "Renewable Energy",
    "E-commerce"
  ],
  "analysis_date": "2023-06-15"
}
```

Given Results by Nexagent (Table Format)
```
+------+------------------------+------------------+-------------+------------------+
| Rank | Company                | Ticker           | Market Cap  | Key Strength     |
+------+------------------------+------------------+-------------+------------------+
| 1    | Persistent Systems     | PERSISTENT.NS    | $4.2B       | Revenue Growth   |
| 2    | Tata Elxsi            | TATAELXSI.NS     | $5.1B       | Design Services  |
| 3    | Zensar Technologies   | ZENSARTECH.NS    | $1.8B       | IT Services      |
+------+------------------------+------------------+-------------+------------------+

Sectors requiring further research:
- Healthcare
- Renewable Energy
- E-commerce
```
## 🔍 Usage Examples

### Basic Data Extraction

```python
from nexagent import Nexagent

async def main():
    agent = Nexagent()

    # Launch a basic extraction task
    result = await agent.run("Extract all product information from https://example.com/products")
    print(result)

    await agent.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Comprehensive Data Extraction

```python
from nexagent.tool.enhanced_browser_tool import EnhancedBrowserTool

async def extract_complete_source():
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
    asyncio.run(extract_complete_source())
```

## 📊 Advanced Usage

### New Architecture Development

The new architecture provides a more modular and extensible framework for building AI agents. Here's how to use it:

#### Creating a New Agent

To create a new agent type:

1. Create a new class that inherits from `AgentLoop` in the `app/agent/types` directory.
2. Implement the `step` method to define the agent's behavior.
3. Register the agent type in `app/agent/factory/__init__.py`.

Example:

```python
from app.agent.loop.agent_loop import AgentLoop

class MyAgent(AgentLoop):
    async def step(self) -> str:
        # Implement your agent's behavior here
        return "Step result"

# In app/agent/factory/__init__.py
AgentFactory.register_agent_type("my_agent", MyAgent)
```

#### Creating a New Tool

To create a new tool:

1. Create a function that implements the tool's behavior.
2. Register the tool in the `ToolRegistry`.

Example:

```python
from app.tools.registry.tool_registry import ToolRegistry

async def my_tool(arg1: str, arg2: int) -> str:
    # Implement your tool's behavior here
    return f"Result: {arg1}, {arg2}"

# Register the tool
ToolRegistry.register_function_as_tool(
    name="my_tool",
    description="A custom tool that does something",
    function=my_tool,
    parameters={
        "type": "object",
        "properties": {
            "arg1": {"type": "string"},
            "arg2": {"type": "integer"}
        },
        "required": ["arg1", "arg2"]
    },
    category="custom"
)
```

### Handling Complex Data Structures

Nexagent automatically detects and handles complex data structures with enhanced formatting options:

```python
# Extract comprehensive data
result = await browser.execute(
    action="navigate_and_extract",
    url="https://example.com/complex-data-gallery",
    extract_type="comprehensive",
    timeout=60000  # Allow more time for processing and loading
)

# Process and format the extracted data for better readability
from app.tool.data_processor import DataProcessor
from app.tool.output_formatter import OutputFormatter

# Format as nicely indented JSON
data_processor = DataProcessor()
formatted_result = await data_processor.execute(
    data=result.output,
    format="json",
    indent=4,
    sort_keys=True
)
print(formatted_result.output)

# Or format as a readable table
table_result = await data_processor.execute(
    data=result.output,
    format="table"
)
print(table_result.output)
```

### Following Complex Structures

```python
async def extract_all_structures(base_url):
    browser = EnhancedBrowserTool()
    all_results = []

    try:
        current_url = base_url
        page = 1

        while True:
            print(f"Processing structure {page}: {current_url}")

            result = await browser.execute(
                action="navigate_and_extract",
                url=current_url,
                extract_type="comprehensive"
            )

            # Process this structure's results
            content = json.loads(result.output.split("\n\n", 1)[1])
            all_results.append(content)

            # Check for complex structures
            if "complex_structure" in content and content["complex_structure"].get("structureLinks"):
                # Find the "next" link
                next_link = None
                for link in content["complex_structure"]["structureLinks"]:
                    if link.get("isNext"):
                        next_link = link["href"]
                        break

                if next_link:
                    current_url = next_link
                    page += 1
                else:
                    print("No more structures found.")
                    break
            else:
                print("No complex structures detected.")
                break

    finally:
        await browser.close()

    return all_results
```

## 🧩 Component Reference

### EnhancedBrowserTool

The core data extraction component with the following main actions:

| Action | Description |
|--------|-------------|
| `navigate` | Navigate to a URL |
| `navigate_and_extract` | Navigate and extract content in one step |
| `stealth_mode` | Enable/disable stealth operation |
| `random_delay` | Set random delays between actions |
| `extract_structured` | Extract structured data from the source |
| `get_text` | Get text content from the current source |
| `get_html` | Get HTML content from the current source |

### Nexagent

The high-level agent that manages the entire extraction process:

- Dynamically calculates appropriate step limits based on task complexity
- Provides multi-level fallbacks for robust operation
- Manages sessions and resources automatically

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
- Built with [browser-use](https://github.com/browser-use/browser-use) for foundational automation
