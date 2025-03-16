import asyncio
import json
import sys

from app.tool.enhanced_browser_tool import EnhancedBrowserTool
from app.agent.franklin_templeton_agent import FranklinTempletonAgent


async def test_enhanced_browser():
    """Test the enhanced browser tool directly"""
    browser = EnhancedBrowserTool()

    try:
        # First enable stealth mode
        await browser.execute(
            action="stealth_mode",
            enable=True
        )

        # Rotate user agent
        await browser.execute(
            action="rotate_user_agent"
        )

        # Test the navigate_and_extract action
        result = await browser.execute(
            action="navigate_and_extract",
            url="https://www.franklintempleton.lu/our-funds/price-and-performance/products/4753/Z/franklin-india-fund/LU0231203729",
            extract_type="all"
        )

        if result.error:
            print(f"Error: {result.error}")
        else:
            # Print the first part of the result
            print(f"Successfully extracted data. First 500 characters:\n{result.output[:500]}...")

            # Save the full result to a file
            with open("franklin_templeton_data.json", "w") as f:
                content = result.output.split("\n\n", 1)[1]  # Skip the first line which is the success message
                f.write(content)
                print(f"Full data saved to franklin_templeton_data.json")
    finally:
        await browser.close()


async def test_franklin_templeton_agent():
    """Test the Franklin Templeton agent"""
    agent = FranklinTempletonAgent()

    try:
        # Fetch data for a specific fund
        result = await agent.fetch_fund_data(
            "https://www.franklintempleton.lu/our-funds/price-and-performance/products/4753/Z/franklin-india-fund/LU0231203729"
        )

        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print("Successfully fetched and processed fund data:")
            print(json.dumps(result, indent=2))

            # Save the result to a file
            with open("franklin_templeton_processed.json", "w") as f:
                json.dump(result, f, indent=2)
                print(f"Processed data saved to franklin_templeton_processed.json")
    finally:
        await agent.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "agent":
        asyncio.run(test_franklin_templeton_agent())
    else:
        asyncio.run(test_enhanced_browser())
