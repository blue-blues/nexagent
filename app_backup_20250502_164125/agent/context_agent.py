"""
Context Agent for Nexagent.

This module provides an agent that manages contextual information extraction,
keyword analysis, and context tracking for other agents.
"""

import json
import time
from typing import Dict, List, Optional, Any, Set, Union
import asyncio

from pydantic import Field, model_validator

from app.agent.base import BaseAgent
from app.agent.toolcall import ToolCallAgent
from app.schema import Message, AgentState, ToolChoice
from app.tool import ToolCollection
from app.tool.terminate import Terminate
from app.tool.input_parser import InputParser
from app.tool.keyword_extractor import KeywordExtractor
from app.logger import logger


class ContextAgent(ToolCallAgent):
    """
    An agent that manages contextual information extraction and tracking.
    
    This agent is responsible for:
    - Extracting keywords and key concepts from user input
    - Analyzing project context to identify relevant information
    - Tracking context across multiple interactions
    - Providing contextual information to other agents
    """

    name: str = "context_agent"
    description: str = "An agent that manages contextual information extraction and tracking"

    system_prompt: str = """
    You are a specialized context analysis agent. Your role is to extract, analyze, and track
    contextual information from user requests and project data. You help other agents understand
    the context of user requests by identifying key concepts, domains, and requirements.
    
    Your responsibilities include:
    1. Extracting keywords and key concepts from user input
    2. Analyzing project context to identify relevant information
    3. Tracking context across multiple interactions
    4. Providing contextual information to other agents
    
    When analyzing requests, focus on:
    - Technical domains (web development, data science, etc.)
    - Programming languages and frameworks
    - Project requirements and constraints
    - User goals and objectives
    
    Provide clear, structured output that can be used by other agents.
    """

    next_step_prompt: str = """
    Based on the current context and any new information, determine the next action:
    
    1. If new input needs to be analyzed:
       - Extract keywords and concepts
       - Identify the technical domain
       - Determine project requirements
    
    2. If context needs to be updated:
       - Incorporate new information
       - Update relevance scores
       - Prune outdated information
    
    3. If context needs to be provided to other agents:
       - Format the context appropriately
       - Highlight the most relevant information
    
    What is the next action you should take?
    """
    
    # Context tracking
    context_store: Dict[str, Any] = Field(default_factory=dict)
    context_history: List[Dict[str, Any]] = Field(default_factory=list)
    current_domain: Optional[str] = None
    
    # Keyword tracking
    extracted_keywords: List[Dict[str, Any]] = Field(default_factory=list)
    keyword_history: Dict[str, List[float]] = Field(default_factory=dict)
    
    # Session tracking
    session_id: Optional[str] = None
    session_start_time: Optional[float] = None
    
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            InputParser(),
            KeywordExtractor(),
            Terminate()
        )
    )

    @model_validator(mode="after")
    def initialize_agent(self) -> "ContextAgent":
        """Initialize the agent with required tools."""
        # Ensure required tools are available
        if "input_parser" not in self.available_tools.tool_map:
            self.available_tools.add_tool(InputParser())
            
        if "keyword_extractor" not in self.available_tools.tool_map:
            self.available_tools.add_tool(KeywordExtractor())
            
        # Initialize session
        self.session_id = f"session_{int(time.time())}"
        self.session_start_time = time.time()
        
        # Initialize context store
        self.context_store = {
            "session_id": self.session_id,
            "start_time": self.session_start_time,
            "domains": {},
            "keywords": {},
            "requirements": [],
            "constraints": [],
            "history": []
        }

        return self

    async def analyze_request(self, request: str) -> Dict[str, Any]:
        """
        Analyze a user request to extract contextual information.
        
        Args:
            request: The user's request to analyze
            
        Returns:
            Dictionary containing extracted contextual information
        """
        logger.info(f"Analyzing request: {request[:50]}...")
        
        # Parse the request using the input parser
        parse_result = await self.available_tools.execute(
            name="input_parser",
            tool_input={"command": "parse", "text": request}
        )
        
        parsed_info = {}
        if hasattr(parse_result, "output"):
            try:
                parsed_info = json.loads(parse_result.output)
                logger.info(f"Parsed request information: {json.dumps(parsed_info, indent=2)}")
            except json.JSONDecodeError:
                logger.error("Failed to parse input parser output as JSON")
        
        # Extract keywords using the keyword extractor
        keyword_result = await self.available_tools.execute(
            name="keyword_extractor",
            tool_input={"command": "extract", "text": request, "max_keywords": 15}
        )
        
        keywords = []
        if hasattr(keyword_result, "output"):
            try:
                keyword_data = json.loads(keyword_result.output)
                keywords = keyword_data.get("keywords", [])
                logger.info(f"Extracted keywords: {json.dumps(keywords, indent=2)}")
            except json.JSONDecodeError:
                logger.error("Failed to parse keyword extractor output as JSON")
        
        # Detect domain
        domain_result = await self.available_tools.execute(
            name="keyword_extractor",
            tool_input={"command": "analyze", "text": request}
        )
        
        domain_info = {}
        if hasattr(domain_result, "output"):
            try:
                domain_info = json.loads(domain_result.output)
                detected_domain = domain_info.get("text_statistics", {}).get("detected_domain")
                if detected_domain:
                    self.current_domain = detected_domain
                    logger.info(f"Detected domain: {detected_domain}")
            except json.JSONDecodeError:
                logger.error("Failed to parse domain analysis output as JSON")
        
        # Combine all information
        analysis_result = {
            "timestamp": time.time(),
            "request": request,
            "parsed_info": parsed_info,
            "keywords": keywords,
            "domain": self.current_domain,
            "domain_info": domain_info
        }
        
        # Update context store
        self._update_context_store(analysis_result)
        
        return analysis_result
    
    def _update_context_store(self, analysis_result: Dict[str, Any]) -> None:
        """
        Update the context store with new analysis results.
        
        Args:
            analysis_result: The analysis result to incorporate
        """
        # Update domains
        domain = analysis_result.get("domain")
        if domain:
            if domain not in self.context_store["domains"]:
                self.context_store["domains"][domain] = {
                    "confidence": 1.0,
                    "first_seen": time.time(),
                    "last_seen": time.time(),
                    "occurrences": 1
                }
            else:
                self.context_store["domains"][domain]["occurrences"] += 1
                self.context_store["domains"][domain]["last_seen"] = time.time()
                self.context_store["domains"][domain]["confidence"] = min(
                    1.0, 
                    self.context_store["domains"][domain]["confidence"] + 0.1
                )
        
        # Update keywords
        keywords = analysis_result.get("keywords", [])
        for keyword_info in keywords:
            keyword = keyword_info.get("keyword")
            relevance = keyword_info.get("relevance", 0.5)
            
            if keyword:
                if keyword not in self.context_store["keywords"]:
                    self.context_store["keywords"][keyword] = {
                        "relevance": relevance,
                        "first_seen": time.time(),
                        "last_seen": time.time(),
                        "occurrences": 1,
                        "relevance_history": [relevance]
                    }
                else:
                    self.context_store["keywords"][keyword]["occurrences"] += 1
                    self.context_store["keywords"][keyword]["last_seen"] = time.time()
                    self.context_store["keywords"][keyword]["relevance_history"].append(relevance)
                    
                    # Update relevance as a weighted average (recent values have more weight)
                    history = self.context_store["keywords"][keyword]["relevance_history"]
                    weights = [i/len(history) for i in range(1, len(history)+1)]
                    weighted_avg = sum(r*w for r, w in zip(history, weights)) / sum(weights)
                    self.context_store["keywords"][keyword]["relevance"] = weighted_avg
        
        # Update requirements and constraints
        parsed_info = analysis_result.get("parsed_info", {})
        requirements = parsed_info.get("requirements", [])
        constraints = parsed_info.get("constraints", [])
        
        for req in requirements:
            if req not in self.context_store["requirements"]:
                self.context_store["requirements"].append(req)
        
        for constraint in constraints:
            if constraint not in self.context_store["constraints"]:
                self.context_store["constraints"].append(constraint)
        
        # Add to history
        history_entry = {
            "timestamp": analysis_result.get("timestamp"),
            "request": analysis_result.get("request"),
            "domain": domain,
            "keywords": [k.get("keyword") for k in keywords]
        }
        self.context_store["history"].append(history_entry)
        
        # Prune old or low-relevance information
        self._prune_context_store()
    
    def _prune_context_store(self) -> None:
        """Prune old or low-relevance information from the context store."""
        current_time = time.time()
        
        # Prune keywords with low relevance and no recent occurrences
        keywords_to_remove = []
        for keyword, info in self.context_store["keywords"].items():
            # If keyword hasn't been seen in the last hour and has low relevance
            if (current_time - info["last_seen"] > 3600) and info["relevance"] < 0.3:
                keywords_to_remove.append(keyword)
        
        for keyword in keywords_to_remove:
            del self.context_store["keywords"][keyword]
        
        # Limit history to last 10 entries
        if len(self.context_store["history"]) > 10:
            self.context_store["history"] = self.context_store["history"][-10:]
    
    async def get_context(self, format_type: str = "full") -> Dict[str, Any]:
        """
        Get the current context in the specified format.
        
        Args:
            format_type: The format to return (full, summary, keywords_only)
            
        Returns:
            Dictionary containing the context information
        """
        if format_type == "full":
            return self.context_store
        
        elif format_type == "summary":
            # Create a summary of the most relevant context
            summary = {
                "session_id": self.session_id,
                "primary_domain": self._get_primary_domain(),
                "top_keywords": self._get_top_keywords(10),
                "key_requirements": self.context_store["requirements"],
                "key_constraints": self.context_store["constraints"],
                "recent_history": self.context_store["history"][-3:] if self.context_store["history"] else []
            }
            return summary
        
        elif format_type == "keywords_only":
            return {
                "top_keywords": self._get_top_keywords(20),
                "domain": self._get_primary_domain()
            }
        
        else:
            return {"error": f"Unknown format type: {format_type}"}
    
    def _get_primary_domain(self) -> Optional[str]:
        """Get the primary domain based on confidence and recency."""
        if not self.context_store["domains"]:
            return None
        
        # Sort domains by a combination of confidence and recency
        current_time = time.time()
        sorted_domains = sorted(
            self.context_store["domains"].items(),
            key=lambda x: (
                x[1]["confidence"],
                -1 * (current_time - x[1]["last_seen"])  # Negative for descending order
            ),
            reverse=True
        )
        
        return sorted_domains[0][0] if sorted_domains else None
    
    def _get_top_keywords(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the top keywords by relevance."""
        if not self.context_store["keywords"]:
            return []
        
        # Sort keywords by relevance
        sorted_keywords = sorted(
            self.context_store["keywords"].items(),
            key=lambda x: x[1]["relevance"],
            reverse=True
        )
        
        # Convert to the required format
        return [
            {
                "keyword": keyword,
                "relevance": info["relevance"],
                "occurrences": info["occurrences"]
            }
            for keyword, info in sorted_keywords[:limit]
        ]
    
    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with an optional initial request."""
        if request:
            analysis_result = await self.analyze_request(request)
            
            # Format the analysis result for display
            formatted_result = json.dumps(analysis_result, indent=2)
            return f"Context analysis complete. Results:\n{formatted_result}"
        
        return await super().run()
    
    async def think(self) -> bool:
        """Decide the next action based on current context."""
        # Include current context in the thinking prompt
        context_summary = await self.get_context(format_type="summary")
        context_json = json.dumps(context_summary, indent=2)
        
        prompt = f"CURRENT CONTEXT:\n{context_json}\n\n{self.next_step_prompt}"
        self.messages.append(Message.user_message(prompt))
        
        # Call the parent think method
        result = await super().think()
        return result


async def main():
    # Configure and run the agent
    agent = ContextAgent()
    result = await agent.run("Build a REST API for a weather app that fetches data from OpenWeatherMap API")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
