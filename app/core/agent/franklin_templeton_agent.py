import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional

from langchain.agents import AgentType, initialize_agent
from langchain.agents.agent import AgentExecutor
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel

from app.agent.franklin_templeton_chain import FranklinTempletonChain
from app.tool.enhanced_browser_tool import EnhancedBrowserTool


class FranklinTempletonAgent:
    """
    Agent for fetching Franklin Templeton fund data.
    """

    def __init__(self):
        self.enhanced_browser = EnhancedBrowserTool()
        self.browser_enabled = True
        self.last_fetch_time = None
        self.last_data = None
        self.cache_duration = 3600  # Cache data for 1 hour

    async def fetch_fund_data(self, fund_url: str) -> Dict[str, Any]:
        """
        Fetch fund data from Franklin Templeton website
        """
        current_time = time.time()

        # Return cached data if available and not expired
        if self.last_data and self.last_fetch_time and (current_time - self.last_fetch_time) < self.cache_duration:
            return self.last_data

        if not self.browser_enabled:
            return {"error": "Browser navigation is disabled"}

        try:
            # Use the new navigate_and_extract action instead of separate navigate and multiple extraction actions
            result = await self.enhanced_browser.execute(
                action="navigate_and_extract",
                url=fund_url,
                extract_type="all"  # This will extract text, links and tables
            )

            if result.error:
                return {"error": result.error}

            # Parse the JSON response
            content = json.loads(result.output.split("\n\n", 1)[1])

            # Process and structure the extracted data
            processed_data = self._process_fund_data(content)

            # Update cache
            self.last_data = processed_data
            self.last_fetch_time = current_time

            return processed_data

        except Exception as e:
            return {"error": f"Error fetching fund data: {str(e)}"}

    def _process_fund_data(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and structure the raw data from the website
        """
        processed_data = {
            "fund_info": {},
            "performance_data": [],
            "holdings": []
        }

        # Extract fund information from text content
        if "text" in content:
            text = content["text"]

            # Extract fund name and basic details
            fund_name_match = re.search(r"(Franklin|Templeton)\s+[\w\s]+(Fund|SICAV)", text)
            if fund_name_match:
                processed_data["fund_info"]["name"] = fund_name_match.group(0)

            # Extract ISIN if present
            isin_match = re.search(r"ISIN[:\s]+([A-Z0-9]{12})", text)
            if isin_match:
                processed_data["fund_info"]["isin"] = isin_match.group(1)

            # Extract fund currency if present
            currency_match = re.search(r"(USD|EUR|GBP|JPY|CHF)", text)
            if currency_match:
                processed_data["fund_info"]["currency"] = currency_match.group(1)

        # Extract performance data from tables
        if "tables" in content:
            tables = content["tables"]
            for table in tables:
                # Look for performance tables
                if (table["headers"] and any(keyword in " ".join(table["headers"]).lower()
                      for keyword in ["performance", "return", "ytd", "1 yr", "3 yr", "5 yr"])):
                    processed_data["performance_data"] = table

                # Look for holdings tables
                elif (table["headers"] and any(keyword in " ".join(table["headers"]).lower()
                       for keyword in ["holding", "weight", "security", "asset", "sector"])):
                    processed_data["holdings"] = table

        # Extract important links
        if "links" in content:
            links = content["links"]
            important_links = []

            for link in links:
                if any(keyword in link.get("text", "").lower() for keyword in
                      ["factsheet", "kiid", "prospectus", "annual report", "monthly"]):
                    important_links.append(link)

            processed_data["important_links"] = important_links

        return processed_data

    async def close(self):
        """Close browser and clean up resources"""
        if self.enhanced_browser:
            await self.enhanced_browser.close()
