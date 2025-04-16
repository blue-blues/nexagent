"""Example tool with dependencies to demonstrate the dependency resolution system."""

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.web_search import WebSearch
from app.tool.enhanced_browser_tool import EnhancedBrowserTool


class WebResearchTool(BaseTool):
    """A tool that depends on both web search and browser tools to perform research."""

    name: str = "web_research"
    description: str = "Performs comprehensive web research by searching and browsing multiple sources"
    required_tools: list = ["web_search", "enhanced_browser"]
    version: str = "1.0.0"

    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The research query to investigate",
            },
            "sources": {
                "type": "integer",
                "description": "Number of sources to check (default: 3)",
                "default": 3,
            },
        },
        "required": ["query"],
    }

    async def execute(
        self,
        query: str,
        sources: int = 3,
        **kwargs
    ) -> ToolResult:
        """Execute the web research tool.

        Args:
            query: The research query to investigate
            sources: Number of sources to check

        Returns:
            Research results from multiple sources
        """
        logger.info(f"Starting web research on: {query}")

        # This tool depends on web_search and enhanced_browser
        # The dependency system should ensure they're available

        # First, search for relevant sources
        search_results = []
        try:
            # We would normally get these tools from the agent or tool collection
            # This is just for demonstration purposes
            web_search = WebSearch()
            browser = EnhancedBrowserTool()

            # Search for sources
            search_result = await web_search.execute(query=query, num_results=sources)
            if isinstance(search_result, ToolResult) and not search_result.error:
                search_results = search_result.output.split("\n")
                logger.info(f"Found {len(search_results)} potential sources")
            else:
                return ToolResult(error=f"Search failed: {str(search_result)}")

            # Browse each source for detailed information
            detailed_results = []
            for i, result in enumerate(search_results[:sources]):
                # Extract URL from search result
                url_match = result.split("(")[1].split(")")[0] if "(" in result and ")" in result else None
                if url_match:
                    logger.info(f"Browsing source {i+1}: {url_match}")
                    browse_result = await browser.execute(action="navigate_and_extract", url=url_match)
                    if not browse_result.error:
                        detailed_results.append(f"Source {i+1}: {browse_result.output[:500]}...")
                    else:
                        detailed_results.append(f"Source {i+1}: Failed to browse - {browse_result.error}")

            # Combine results
            combined_result = f"Research results for: {query}\n\n"
            combined_result += "\n\n".join(detailed_results)

            return ToolResult(output=combined_result)

        except Exception as e:
            logger.error(f"Error in web research: {str(e)}")
            return ToolResult(error=f"Research failed: {str(e)}")
