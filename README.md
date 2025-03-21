Nexagent: Next‑Gen Intelligent Data Extraction Agent
<div align="center"> <img src="https://github.com/blue-blues/nexagent/raw/main/assets/nexagent-logo.png" alt="Nexagent Logo" width="250"/> <br><br> <strong>Your versatile AI agent for dynamic data extraction and intelligent processing</strong> <br><br> </div>


🚀 Overview
Nexagent is a cutting‑edge intelligent agent built for comprehensive data extraction and processing. Leveraging advanced AI and asynchronous execution, Nexagent is designed to:

Extract full content even from dynamic and complex sources.
Adapt dynamically to various data structures and anti‑extraction measures.
Process and analyze data intelligently through multi‑step planning.
Handle complex data hierarchies with robust fallback mechanisms.
Integrate seamlessly with external APIs and local resources for enhanced functionality.
🌟 Key Features
Advanced Data Extraction
Comprehensive extraction modes: Supports plain text, structured content, and dynamic page elements.
Stealth operation: Incorporates advanced anti‑detection techniques and randomized delays.
Adaptive parsing: Automatically detects, parses, and preserves document structure.
Asynchronous execution: Utilizes modern async/await patterns for non‑blocking extraction.
Intelligent Processing & Reasoning
Dynamic step planning: Automatically adjusts execution steps based on task complexity.
Multi‑level fallback: Implements retries, exponential backoff, and self‑healing strategies.
Smarter reasoning: Integrates enhanced LLM integrations for improved tool selection and decision making.
Context‑aware insights: Prioritizes main content with intelligent prioritization of extraction targets.
Flexible & Modular Architecture
Modular tool system: Easily extend with new extraction strategies and processing modules.
Configurable behavior: Fine‑tune settings via a simple TOML configuration file.
Robust dependency management: Automatically installs missing modules and verifies execution environments.
Seamless API integration: Supports external APIs (e.g., Google Gemini, Gemma API) for data enrichment.
🛠️ Installation
Clone the repository:

bash
Copy
Edit
git clone https://github.com/blue-blues/nexagent.git
cd nexagent
Create and activate a virtual environment (recommended):

bash
Copy
Edit
python -m venv venv
# On Unix/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
Install dependencies:

bash
Copy
Edit
pip install -r requirements.txt
Configure the agent:

Copy the example config:
bash
Copy
Edit
cp config/config.example.toml config/config.toml
Edit config/config.toml to add your API keys and adjust settings as needed.
Run Nexagent:

bash
Copy
Edit
python main.py
When prompted, enter your extraction or analysis prompt.

⚙️ Configuration
Nexagent uses a TOML configuration file located at config/config.toml. Key configuration parameters include:

toml
Copy
Edit
# LLM Model Settings
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Your API key
max_tokens = 4096
temperature = 0.0

# Browser Extraction Settings
[browser]
headless = true     # Use headless mode in production
timeout = 60000     # Adjust timeout (ms) for slow-loading sites
random_delay_min = 800
random_delay_max = 2500

# Execution and Retry Settings
[execution]
default_timeout = 10  # Timeout for Python code execution (seconds)
max_retries = 3       # Max retries for API calls
🔍 Usage Examples
Basic Data Extraction
python
Copy
Edit
import asyncio
from nexagent import Nexagent

async def main():
    agent = Nexagent()
    try:
        # Extract product information from a website
        result = await agent.run("Extract all product information from https://example.com/products")
        print(result)
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
Advanced Comprehensive Extraction
python
Copy
Edit
import asyncio
from nexagent.tool.enhanced_browser_tool import EnhancedBrowserTool

async def extract_complete_site():
    browser = EnhancedBrowserTool()
    try:
        # Enable stealth mode and random delays to avoid detection
        await browser.execute(action="stealth_mode", enable=True)
        await browser.execute(action="random_delay", min_delay=800, max_delay=2500)
        
        # Extract comprehensive content from a complex website
        result = await browser.execute(
            action="navigate_and_extract",
            url="https://example.com/complex-site",
            extract_type="comprehensive"
        )
        
        # Save the results locally
        with open("extraction_results.json", "w") as f:
            content = result.output.split("\n\n", 1)[1]  # Remove any header message
            f.write(content)
        print("Extraction complete. Results saved.")
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_complete_site())
Handling Dynamic Workflows
python
Copy
Edit
import asyncio
import json
from nexagent.tool.enhanced_browser_tool import EnhancedBrowserTool

async def extract_complex_structures(base_url):
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
                extract_type="comprehensive",
                timeout=60000  # Extended timeout for complex pages
            )
            content = json.loads(result.output.split("\n\n", 1)[1])
            all_results.append(content)
            
            # Determine next page link
            next_link = None
            for link in content.get("structureLinks", []):
                if link.get("isNext"):
                    next_link = link["href"]
                    break
            if next_link:
                current_url = next_link
                page += 1
            else:
                print("No further pages found.")
                break
    finally:
        await browser.close()
    
    return all_results

if __name__ == "__main__":
    results = asyncio.run(extract_complex_structures("https://example.com/complex-data-gallery"))
    print(results)
📊 Advanced Features
Auto‑Installation of Missing Modules
Nexagent now includes an auto‑installer that scans for required Python modules before executing code. If a module is missing, it automatically installs it via pip, ensuring smoother execution.

Enhanced Reasoning & Fallback Mechanisms
Smarter LLM Integration:
Nexagent now uses improved LLM logic to generate meaningful “thoughts” and decides which tools to execute based on context.
Adaptive API Delays:
Implements configurable delays and dynamic backoff to prevent rate limit issues.
Loop Escape Strategies:
Detects repetitive execution cycles and adjusts the workflow to ensure continuous progress.
🤝 Contributing
Contributions are welcome! To contribute:

Fork the repository.
Create a feature branch:
bash
Copy
Edit
git checkout -b feature/your-feature-name
Commit your changes with clear messages.
Push to your branch and open a Pull Request.
📄 License
This project is licensed under the MIT License – see the LICENSE file for details.

🙏 Acknowledgements
Special thanks to the OpenManus team for inspiration.
Built on the foundational principles of browser-use.
