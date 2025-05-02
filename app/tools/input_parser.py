"""
Input Parser Tool for extracting key intents and requirements from user input.

This tool uses regex patterns and structured templates to parse user instructions
and extract key information needed for planning and execution.
"""

import re
import json
from typing import Dict, List, Optional, Any
from pydantic import Field

from app.tools.base import BaseTool, ToolResult
from app.logger import logger


class InputParser(BaseTool):
    """
    Tool for parsing user input to extract key intents and requirements.
    
    This tool uses regex patterns and structured templates to analyze user instructions
    and extract structured information for planning and execution.
    """
    
    name: str = "input_parser"
    description: str = """
    Parse user input to extract key intents, requirements, and constraints.
    This tool helps convert natural language instructions into structured data
    that can be used for planning and execution.
    """
    
    # Domain-specific patterns for common programming tasks
    DOMAIN_PATTERNS = {
        "web_development": {
            "api": r"(?:REST|GraphQL|API).*?(?:for|to)\s+([a-zA-Z0-9\s]+)",
            "frontend": r"(?:frontend|UI|interface).*?(?:for|to)\s+([a-zA-Z0-9\s]+)",
            "database": r"(?:database|DB|data\s+model).*?(?:for|to)\s+([a-zA-Z0-9\s]+)",
            "authentication": r"(?:auth|authentication|login).*?(?:system|mechanism|flow)",
        },
        "data_science": {
            "analysis": r"(?:analyze|analysis|examine).*?(?:data|dataset)\s+(?:for|of|about)\s+([a-zA-Z0-9\s]+)",
            "visualization": r"(?:visualize|visualization|chart|plot|graph).*?(?:for|of|about)\s+([a-zA-Z0-9\s]+)",
            "model": r"(?:model|ML|machine\s+learning|predict).*?(?:for|to)\s+([a-zA-Z0-9\s]+)",
        },
        "automation": {
            "script": r"(?:script|automate|automation).*?(?:for|to)\s+([a-zA-Z0-9\s]+)",
            "workflow": r"(?:workflow|process).*?(?:for|to)\s+([a-zA-Z0-9\s]+)",
        }
    }
    
    # General patterns for common requirements
    GENERAL_PATTERNS = {
        "language": r"(?:using|in|with)\s+(Python|JavaScript|TypeScript|Java|C\+\+|Go|Rust|PHP|Ruby|C#|Swift)",
        "framework": r"(?:using|with)\s+(React|Angular|Vue|Django|Flask|Express|Spring|Laravel|Rails|ASP\.NET)",
        "database": r"(?:using|with)\s+(MySQL|PostgreSQL|MongoDB|SQLite|Oracle|SQL\s+Server|Redis|Cassandra)",
        "platform": r"(?:on|for)\s+(AWS|Azure|GCP|Heroku|Netlify|Vercel|Docker|Kubernetes)",
        "deadline": r"(?:by|before|within)\s+(\d+)\s+(day|days|week|weeks|hour|hours)",
    }
    
    async def execute(self, command: str, text: str, extraction_mode: str = "auto", 
                     domain: Optional[str] = None) -> ToolResult:
        """
        Execute the input parser tool.
        
        Args:
            command: The command to execute (parse, extract_keywords, validate)
            text: The user input text to parse
            extraction_mode: Mode for extraction (auto, domain_specific, general)
            domain: Optional domain to focus extraction on
            
        Returns:
            ToolResult containing the parsed information
        """
        try:
            if command == "parse":
                result = self._parse_input(text, extraction_mode, domain)
                return ToolResult(output=json.dumps(result, indent=2))
                
            elif command == "extract_keywords":
                keywords = self._extract_keywords(text, domain)
                return ToolResult(output=json.dumps({"keywords": keywords}, indent=2))
                
            elif command == "validate":
                validation_result = self._validate_input(text)
                return ToolResult(output=json.dumps(validation_result, indent=2))
                
            else:
                return ToolResult(error=f"Unknown command: {command}")
                
        except Exception as e:
            logger.error(f"Error in InputParser: {str(e)}")
            return ToolResult(error=f"Failed to parse input: {str(e)}")
    
    def _parse_input(self, text: str, extraction_mode: str = "auto", 
                    domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse user input to extract structured information.
        
        Args:
            text: The user input text to parse
            extraction_mode: Mode for extraction
            domain: Optional domain to focus extraction on
            
        Returns:
            Dictionary containing parsed information
        """
        result = {
            "raw_input": text,
            "main_intent": self._extract_main_intent(text),
            "requirements": [],
            "constraints": [],
            "extracted_entities": {},
        }
        
        # Extract domain-specific information if domain is provided or auto-detected
        if extraction_mode in ["auto", "domain_specific"]:
            if domain is None:
                domain = self._detect_domain(text)
            
            if domain and domain in self.DOMAIN_PATTERNS:
                domain_extractions = self._extract_domain_specific(text, domain)
                result["extracted_entities"].update(domain_extractions)
                
                # Convert domain extractions to requirements
                for key, value in domain_extractions.items():
                    if value:
                        result["requirements"].append(f"{key.replace('_', ' ').title()}: {value}")
        
        # Extract general information
        if extraction_mode in ["auto", "general"]:
            general_extractions = self._extract_general_info(text)
            result["extracted_entities"].update(general_extractions)
            
            # Convert general extractions to constraints
            for key, value in general_extractions.items():
                if value:
                    result["constraints"].append(f"{key.title()}: {value}")
        
        return result
    
    def _extract_main_intent(self, text: str) -> str:
        """Extract the main intent from the user input."""
        # Look for common action verbs at the beginning of the text
        action_verbs = [
            "create", "build", "develop", "implement", "design", "make",
            "write", "code", "generate", "analyze", "automate", "optimize"
        ]
        
        # Try to find the first sentence or main clause
        first_sentence = text.split(".")[0].strip()
        
        # Check if the first sentence starts with an action verb
        for verb in action_verbs:
            if first_sentence.lower().startswith(verb):
                return first_sentence
        
        # If no action verb is found at the beginning, look for the first occurrence
        for verb in action_verbs:
            pattern = rf"\b{verb}\b\s+([^.!?]+)"
            match = re.search(pattern, text.lower())
            if match:
                return match.group(0)
        
        # If no clear intent is found, return the first sentence
        return first_sentence
    
    def _detect_domain(self, text: str) -> Optional[str]:
        """Detect the domain of the user input."""
        domain_keywords = {
            "web_development": [
                "website", "web app", "frontend", "backend", "api", "rest", 
                "http", "html", "css", "javascript", "react", "angular", "vue"
            ],
            "data_science": [
                "data", "analysis", "dataset", "visualization", "model", "predict",
                "machine learning", "ml", "ai", "statistics", "pandas", "numpy"
            ],
            "automation": [
                "automate", "script", "workflow", "process", "bot", "scheduled",
                "cron", "task", "automation"
            ]
        }
        
        # Count occurrences of domain keywords
        domain_scores = {domain: 0 for domain in domain_keywords}
        
        for domain, keywords in domain_keywords.items():
            for keyword in keywords:
                if re.search(rf"\b{keyword}\b", text.lower()):
                    domain_scores[domain] += 1
        
        # Return the domain with the highest score, if any
        max_domain = max(domain_scores.items(), key=lambda x: x[1])
        return max_domain[0] if max_domain[1] > 0 else None
    
    def _extract_domain_specific(self, text: str, domain: str) -> Dict[str, str]:
        """Extract domain-specific information from the user input."""
        result = {}
        
        if domain not in self.DOMAIN_PATTERNS:
            return result
        
        for key, pattern in self.DOMAIN_PATTERNS[domain].items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match and match.groups():
                result[key] = match.group(1).strip()
            elif match:
                result[key] = "Required"
        
        return result
    
    def _extract_general_info(self, text: str) -> Dict[str, str]:
        """Extract general information from the user input."""
        result = {}
        
        for key, pattern in self.GENERAL_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match and match.groups():
                result[key] = match.group(1).strip()
        
        return result
    
    def _extract_keywords(self, text: str, domain: Optional[str] = None) -> List[str]:
        """Extract keywords from the user input."""
        keywords = []
        
        # Extract domain-specific keywords
        if domain and domain in self.DOMAIN_PATTERNS:
            for key, pattern in self.DOMAIN_PATTERNS[domain].items():
                match = re.search(pattern, text, re.IGNORECASE)
                if match and match.groups():
                    keywords.append(match.group(1).strip())
                elif match:
                    keywords.append(key.replace("_", " "))
        
        # Extract general keywords
        for key, pattern in self.GENERAL_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match and match.groups():
                keywords.append(match.group(1).strip())
        
        # Add additional keywords based on common programming terms
        common_terms = [
            "API", "REST", "GraphQL", "database", "authentication", "frontend",
            "backend", "full-stack", "mobile", "web", "cloud", "serverless",
            "microservices", "container", "docker", "kubernetes", "CI/CD",
            "testing", "deployment", "security", "performance", "scalability"
        ]
        
        for term in common_terms:
            if re.search(rf"\b{term}\b", text, re.IGNORECASE):
                keywords.append(term.lower())
        
        return list(set(keywords))  # Remove duplicates
    
    def _validate_input(self, text: str) -> Dict[str, Any]:
        """Validate the user input for completeness and clarity."""
        validation_result = {
            "is_valid": True,
            "missing_information": [],
            "ambiguities": [],
            "suggestions": []
        }
        
        # Check for minimum length
        if len(text) < 10:
            validation_result["is_valid"] = False
            validation_result["missing_information"].append("Input is too short")
            validation_result["suggestions"].append("Please provide a more detailed description of what you need")
        
        # Check for key components in common requests
        if re.search(r"\b(api|rest|graphql)\b", text.lower()):
            if not re.search(r"\bendpoints?\b", text.lower()):
                validation_result["missing_information"].append("API endpoints not specified")
                validation_result["suggestions"].append("Consider specifying the required API endpoints")
        
        if re.search(r"\b(website|web app|frontend)\b", text.lower()):
            if not re.search(r"\b(pages?|screens?|views?|components?)\b", text.lower()):
                validation_result["missing_information"].append("Website/app pages or components not specified")
                validation_result["suggestions"].append("Consider specifying the required pages or components")
        
        if re.search(r"\b(database|data model)\b", text.lower()):
            if not re.search(r"\b(tables?|collections?|entities|fields|attributes)\b", text.lower()):
                validation_result["missing_information"].append("Database structure not specified")
                validation_result["suggestions"].append("Consider specifying the required database tables/entities")
        
        # Check for ambiguities
        ambiguous_terms = ["it", "this", "that", "they", "them", "these", "those"]
        for term in ambiguous_terms:
            if re.search(rf"\b{term}\b", text.lower()):
                validation_result["ambiguities"].append(f"Ambiguous reference: '{term}'")
                validation_result["suggestions"].append(f"Consider clarifying what '{term}' refers to")
        
        # Update validity based on findings
        if validation_result["missing_information"] or validation_result["ambiguities"]:
            validation_result["is_valid"] = False
        
        return validation_result
