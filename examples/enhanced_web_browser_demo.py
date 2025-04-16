"""
Enhanced Web Browser Demo

This script demonstrates the advanced web browsing capabilities of the Nexagent
Enhanced Web Browser, including:
1. Stealth mode configuration
2. Structured data extraction
3. Multi-source validation
4. Exponential backoff retry mechanism
"""

import asyncio
import json
import sys
import os
import time

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tool.enhanced_web_browser import EnhancedWebBrowser

async def demo_stealth_mode():
    """Demonstrate stealth mode capabilities."""
    print("\n=== Demonstrating Stealth Mode ===")
    browser = EnhancedWebBrowser()

    try:
        # Enable stealth mode
        print("Enabling stealth mode...")
        result = await browser.execute(action="enable_stealth_mode")
        print(f"Result: {result.output if not result.error else result.error}")

        # Navigate to a simple website instead of a bot detection site for the demo
        print("\nNavigating to a website with stealth mode enabled...")
        url = "https://example.com/"  # A simple website that loads quickly
        result = await browser.execute(action="navigate", url=url)
        print(f"Navigation result: {'Success' if not result.error else result.error}")

        # Extract the content
        print("\nExtracting page content...")
        result = await browser.execute(action="extract_data", url=url, data_type="text")

        # Show a summary of the results
        if not result.error:
            print("\nExtracted content summary:")
            content = result.output
            if "Successfully" in content and "\n\n" in content:
                content = content.split("\n\n", 1)[1]

            # Just show the first few lines as a summary
            lines = content.split("\n")
            for i in range(min(5, len(lines))):
                print(lines[i])
            print("...")
        else:
            print(f"Error: {result.error}")

        # Disable stealth mode
        print("\nDisabling stealth mode...")
        result = await browser.execute(action="disable_stealth_mode")
        print(f"Result: {result.output if not result.error else result.error}")

    finally:
        await browser.close()

async def demo_structured_data_extraction():
    """Demonstrate structured data extraction capabilities."""
    print("\n=== Demonstrating Structured Data Extraction ===")
    browser = EnhancedWebBrowser()

    try:
        # Enable stealth mode for reliable extraction
        await browser.execute(action="enable_stealth_mode")

        # Define a schema for webpage data
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "main_content": {"type": "string"},
                "links": {"type": "array"},
            },
            "required": ["title"]
        }

        # Extract structured data from a simple page
        print("Extracting structured data...")
        url = "https://example.com/"  # Simple example URL

        result = await browser.execute(
            action="extract_structured_data",
            url=url,
            schema=schema
        )

        # Display the results
        if not result.error:
            print("\nExtracted structured data:")
            try:
                data = json.loads(result.output)
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                print(result.output)
        else:
            print(f"Error: {result.error}")

    finally:
        await browser.close()

async def demo_multi_source_validation():
    """Demonstrate multi-source validation capabilities."""
    print("\n=== Demonstrating Multi-Source Validation ===")
    browser = EnhancedWebBrowser()

    try:
        # Enable stealth mode
        await browser.execute(action="enable_stealth_mode")

        # Define multiple sources for the same information
        urls = [
            "https://example.com/",
            "https://example.org/",
            "https://example.net/"
        ]

        print(f"Extracting data from {len(urls)} example sources...")
        result = await browser.execute(
            action="multi_source_extract",
            urls=urls,
            data_type="text",
            validation_level="basic"
        )

        # Display the results
        if not result.error:
            print("\nMulti-source validation results:")
            try:
                data = json.loads(result.output)

                print(f"Number of sources: {data.get('sources', 0)}")
                print(f"Validation level: {data.get('validation_level', 'unknown')}")

                # Show a simplified summary
                print("\nSources summary:")
                results = data.get('results', [])
                for i, result in enumerate(results):
                    url = result.get('url', 'unknown')
                    content = result.get('content', '')
                    if content:
                        content_preview = content[:100] + "..." if len(content) > 100 else content
                        print(f"Source {i+1}: {url}\nPreview: {content_preview}\n")

                # Show any errors
                errors = data.get('errors', [])
                if errors:
                    print("\nErrors encountered:")
                    for error in errors:
                        print(f"  - {error}")

            except json.JSONDecodeError:
                print(result.output)
        else:
            print(f"Error: {result.error}")

    finally:
        await browser.close()

async def demo_retry_mechanism():
    """Demonstrate exponential backoff retry mechanism."""
    print("\n=== Demonstrating Exponential Backoff Retry Mechanism ===")
    browser = EnhancedWebBrowser()

    try:
        # Simulate a retry scenario with a non-existent domain
        url = "https://non-existent-domain-for-testing-123456.com/"  # This should fail and trigger retries

        print(f"Attempting to access {url} with retry mechanism...")
        print("This should fail and trigger the retry mechanism...")
        start_time = time.time()

        result = await browser.execute(
            action="navigate",
            url=url,
            max_retries=2  # Set to 2 retries with exponential backoff
        )

        end_time = time.time()
        duration = end_time - start_time

        print(f"\nRetry mechanism completed in {duration:.2f} seconds")
        print(f"Final result: {'Success' if not result.error else 'Failed as expected with retries'}")

        # Now try a URL that should succeed
        print("\nNow trying a URL that should succeed...")
        url = "https://example.com/"

        result = await browser.execute(
            action="navigate",
            url=url,
            max_retries=2
        )

        print(f"Result: {'Success' if not result.error else result.error}")

    finally:
        await browser.close()

async def main():
    """Run all demos with improved error handling."""
    print("=== Enhanced Web Browser Demo ===\n")
    print("This demo showcases the advanced web browsing capabilities of Nexagent.")

    demos = [
        ("Stealth Mode", demo_stealth_mode),
        ("Structured Data Extraction", demo_structured_data_extraction),
        ("Multi-Source Validation", demo_multi_source_validation),
        ("Retry Mechanism", demo_retry_mechanism)
    ]

    success_count = 0

    for name, demo_func in demos:
        print(f"\n{'-' * 40}")
        print(f"Running demo: {name}")
        print(f"{'-' * 40}")

        try:
            await demo_func()
            success_count += 1
            print(f"✅ {name} demo completed successfully")
        except Exception as e:
            print(f"❌ Error during {name} demo: {str(e)}")
            import traceback
            traceback.print_exc()
            print("Continuing with next demo...")

    print("\n=== Demo Summary ===")
    print(f"Successfully completed {success_count}/{len(demos)} demos")

    if success_count == len(demos):
        print("\n🎉 All enhanced web browsing features have been demonstrated successfully!")
    else:
        print(f"\n⚠️ {len(demos) - success_count} demos encountered errors. See above for details.")

if __name__ == "__main__":
    asyncio.run(main())
