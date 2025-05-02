from typing import Any, Dict, List, Optional, Tuple, Union
import re
import asyncio
import json
from datetime import datetime

from app.tool.base import ToolResult
from app.logger import logger


class ErrorHandler:
    """
    A utility class for handling errors in tool execution and implementing fallback strategies.
    
    This class provides methods for detecting errors, implementing fallback strategies,
    and tracking error history to make informed decisions about future fallback attempts.
    """
    
    # Error patterns to detect specific types of failures
    ERROR_PATTERNS = {
        "timeout": [r"timed? out", r"timeout", r"took too long", r"request timed out", r"connection timed out"],
        "connection": [r"connection (error|failed|refused|reset)", r"network (error|issue|unreachable)", r"unable to connect", r"host unreachable", r"no route to host"],
        "anti_scraping": [r"captcha", r"cloudflare", r"access denied", r"forbidden", r"blocked", r"403", r"bot detection", r"automated access", r"too many requests", r"rate limited", r"429"],
        "not_found": [r"404", r"not found", r"does not exist", r"no longer available", r"removed", r"deleted"],
        "extraction": [r"extraction (error|failed)", r"no (content|data|text) found", r"empty (result|response)", r"invalid (format|structure)", r"parsing (failed|error)", r"no elements matching", r"selector not found"],
        "syntax": [r"syntax error", r"unexpected token", r"parsing error", r"invalid (json|html|xml|format)", r"malformed"],
        "authentication": [r"login required", r"authentication (failed|required)", r"not authorized", r"401", r"permission denied", r"invalid (token|credentials|api key)"],
        "server_error": [r"500", r"502", r"503", r"504", r"internal server error", r"bad gateway", r"service unavailable", r"gateway timeout"]
    }
    
    def __init__(self):
        self.error_history = []
        self.fallback_attempts = {}
        self.max_fallback_attempts = 3
        self.last_error_time = None
    
    def detect_error_type(self, error_message: str) -> Optional[str]:
        """
        Detect the type of error from an error message.
        
        Args:
            error_message: The error message to analyze
            
        Returns:
            The detected error type or None if no specific type is detected
        """
        if not error_message:
            return None
            
        error_message = error_message.lower()
        
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return error_type
        
        return "unknown"
    
    def record_error(self, tool_name: str, action: str, error_message: str, params: Dict = None):
        """
        Record an error for future reference and fallback decision making.
        
        Args:
            tool_name: The name of the tool that encountered the error
            action: The specific action being performed (e.g., "navigate", "get_text")
            error_message: The error message
            params: The parameters used in the failed action
        """
        error_type = self.detect_error_type(error_message)
        timestamp = datetime.now()
        
        error_record = {
            "tool": tool_name,
            "action": action,
            "error_type": error_type,
            "message": error_message,
            "params": params or {},
            "timestamp": timestamp
        }
        
        self.error_history.append(error_record)
        self.last_error_time = timestamp
        
        # Update fallback attempt counter
        key = f"{tool_name}:{action}"
        self.fallback_attempts[key] = self.fallback_attempts.get(key, 0) + 1
        
        logger.warning(f"🚨 Error detected in {tool_name}.{action}: {error_type} - {error_message}")
    
    def should_try_fallback(self, tool_name: str, action: str) -> bool:
        """
        Determine if a fallback strategy should be attempted based on error history.
        
        Args:
            tool_name: The name of the tool
            action: The specific action
            
        Returns:
            True if a fallback should be attempted, False otherwise
        """
        key = f"{tool_name}:{action}"
        attempts = self.fallback_attempts.get(key, 0)
        
        return attempts < self.max_fallback_attempts
    
    def get_fallback_strategy(self, tool_name: str, action: str, error_type: str, original_params: Dict) -> Tuple[str, Dict]:
        """
        Get an appropriate fallback strategy based on the error type and history.
        
        Args:
            tool_name: The name of the tool
            action: The specific action
            error_type: The type of error detected
            original_params: The original parameters used
            
        Returns:
            A tuple of (fallback_action, fallback_params)
        """
        key = f"{tool_name}:{action}"
        attempt_number = self.fallback_attempts.get(key, 0)
        
        # Clone the original parameters for modification
        fallback_params = original_params.copy() if original_params else {}
        
        # Default to the same action unless changed below
        fallback_action = action
        
        # Extract URL for context-aware strategies
        url = fallback_params.get('url', '')
        
        # Handle browser tool fallbacks
        if tool_name == "enhanced_browser":
            if error_type == "timeout":
                # Adaptive timeout strategy - increase exponentially with each attempt
                timeout = fallback_params.get("timeout", 30000)
                fallback_params["timeout"] = int(timeout * (1.5 ** attempt_number))
                
                # First attempt: Enable stealth mode with random delays
                if attempt_number == 0:
                    logger.info(f"🕵️ Enabling stealth mode with increased timeout: {fallback_params['timeout']}ms")
                    fallback_params["action"] = "stealth_mode"
                    fallback_params["enable"] = True
                    # Add random delays to mimic human behavior
                    fallback_params["min_delay"] = 800
                    fallback_params["max_delay"] = 2500
                    return "enhanced_browser", fallback_params
                    
                # Second attempt: Try with different user agent and simplified approach
                elif attempt_number == 1:
                    logger.info(f"🔄 Rotating user agent and simplifying request approach")
                    fallback_params["action"] = "rotate_user_agent"
                    
                    # For complex actions, try a simpler approach
                    if action in ["navigate_and_extract", "extract_structured"]:
                        fallback_action = "navigate"
                        return fallback_action, fallback_params
                
                # Third attempt: Try a completely different approach or tool
                elif attempt_number >= 2:
                    # For content extraction, try a different method
                    if action in ["navigate_and_extract", "extract_structured", "get_html", "get_text"]:
                        # Try web search as an alternative data source
                        logger.info(f"🔍 Switching to web search for alternative data source")
                        search_query = f"information from {url}" if url else "information about the topic"
                        
                        # Extract context from URL for better search
                        if url:
                            # Try to extract meaningful terms from the URL
                            url_terms = re.sub(r'https?://|www\.|[\W_]+', ' ', url).strip()
                            if url_terms:
                                search_query = url_terms
                        
                        return "web_search", {"query": search_query}
            
            elif error_type == "anti_scraping":
                # First attempt: Enable comprehensive stealth mode
                if attempt_number == 0:
                    logger.info(f"🕵️ Enabling comprehensive stealth mode to bypass detection")
                    fallback_params["action"] = "stealth_mode"
                    fallback_params["enable"] = True
                    # Add random delays to mimic human behavior
                    fallback_params["min_delay"] = 1500  # Longer delays for anti-scraping
                    fallback_params["max_delay"] = 4000
                    return "enhanced_browser", fallback_params
                
                # Second attempt: Rotate user agent and try with simplified approach
                elif attempt_number == 1:
                    logger.info(f"🔄 Rotating user agent and adding additional anti-detection measures")
                    fallback_params["action"] = "rotate_user_agent"
                    
                    # Execute anti-detection JavaScript
                    if "script" not in fallback_params:
                        fallback_params["action"] = "execute_js"
                        fallback_params["script"] = """
                        // Hide automation fingerprints
                        Object.defineProperty(navigator, 'webdriver', {get: () => false});
                        Object.defineProperty(navigator, 'plugins', {get: () => [{name: 'Chrome PDF Plugin'}, {name: 'Chrome PDF Viewer'}]});
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                        """
                        return "enhanced_browser", fallback_params
                
                # Third attempt: Try cached version or alternative source
                elif attempt_number >= 2:
                    logger.info(f"🔍 Trying cached version or alternative source")
                    
                    # Try to get cached version via search
                    if url:
                        # First try web search for cached version
                        return "web_search", {"query": f"cached {url}"}
                    else:
                        # Fall back to general web search
                        return "web_search", {"query": f"information about {fallback_params.get('text', 'the topic')}"}
            
            elif error_type in ["extraction", "syntax", "not_found"]:
                # First attempt: Try with more general selectors or different extraction method
                if attempt_number == 0:
                    logger.info(f"🔍 Trying more general selectors or different extraction method")
                    
                    if action == "extract_structured":
                        # Try with a more general selector
                        fallback_params["selector"] = "body"
                    elif action in ["get_text", "get_html"]:
                        # Try the other method
                        fallback_action = "get_html" if action == "get_text" else "get_text"
                    
                    return fallback_action, fallback_params
                
                # Second attempt: Try JavaScript-based extraction
                elif attempt_number == 1:
                    logger.info(f"🔧 Attempting JavaScript-based extraction")
                    
                    # Use JavaScript to extract content
                    fallback_params["action"] = "execute_js"
                    
                    if "selector" in fallback_params:
                        # Extract content using the selector via JavaScript
                        selector = fallback_params["selector"]
                        fallback_params["script"] = f"""
                        function extractContent() {{
                            const elements = document.querySelectorAll('{selector}');
                            if (elements.length === 0) return 'No elements found';
                            
                            return Array.from(elements).map(el => el.innerText || el.textContent).join('\n\n');
                        }}
                        return extractContent();
                        """
                    else:
                        # Extract all visible text
                        fallback_params["script"] = """
                        function extractVisibleText() {
                            const walker = document.createTreeWalker(
                                document.body, 
                                NodeFilter.SHOW_TEXT, 
                                { acceptNode: node => {
                                    if (node.parentElement.offsetParent !== null) {
                                        return NodeFilter.FILTER_ACCEPT;
                                    }
                                    return NodeFilter.FILTER_REJECT;
                                }
                            });
                            
                            let text = [];
                            let node;
                            while (node = walker.nextNode()) {
                                let trimmed = node.textContent.trim();
                                if (trimmed.length > 0) {
                                    text.push(trimmed);
                                }
                            }
                            
                            return text.join('\n\n');
                        }
                        return extractVisibleText();
                        """
    
    def is_result_successful(self, result: Union[str, ToolResult]) -> bool:
        """
        Determine if a tool result was successful.
        
        Args:
            result: The result to check
            
        Returns:
            True if the result indicates success, False otherwise
        """
        # For string results
        if isinstance(result, str):
            # Check if the result contains any error patterns
            has_error_pattern = any(re.search(pattern, result, re.IGNORECASE) 
                                  for patterns in self.ERROR_PATTERNS.values() 
                                  for pattern in patterns)
            
            # Check if the result is empty or too short to be meaningful
            is_empty_or_short = not result or len(result.strip()) < 10
            
            # Check for common error indicators in the content
            has_error_indicators = any(indicator in result.lower() for indicator in [
                "error", "exception", "failed", "failure", "unable to", "cannot", 
                "could not", "not found", "invalid", "unexpected"
            ])
            
            # Consider the result successful if it doesn't have error patterns,
            # is not empty/too short, and doesn't contain error indicators
            return not (has_error_pattern or is_empty_or_short or has_error_indicators)
        
        # For ToolResult objects
        if isinstance(result, ToolResult):
            # Check if there's an explicit error
            if result.error:
                return False
            
            # Check if the output exists and is meaningful
            if not result.output:
                return False
                
            # For string outputs, apply additional checks
            if isinstance(result.output, str):
                # Check if the output is too short to be meaningful
                if len(result.output.strip()) < 10:
                    return False
                    
                # Check for error indicators in the content
                if any(indicator in result.output.lower() for indicator in [
                    "error", "exception", "failed", "failure", "unable to", 
                    "cannot", "could not", "not found", "invalid", "unexpected"
                ]):
                    # Do a more nuanced check - sometimes error words appear in valid content
                    # Count the ratio of error words to total words
                    words = result.output.lower().split()
                    error_word_count = sum(1 for word in words if any(indicator in word for indicator in [
                        "error", "exception", "fail", "unable", "cannot", "invalid"
                    ]))
                    
                    # If error words make up more than 10% of the content, likely an error
                    if len(words) > 0 and error_word_count / len(words) > 0.1:
                        return False
            
            # If we've passed all checks, consider it successful
            return True
        
        # For any other type, consider it unsuccessful
        return False
        
    def generate_improvement_suggestions(self) -> List[str]:
        """
        Generate suggestions for improving tool execution based on error history.
        
        This method analyzes the error history to identify patterns and generate
        specific suggestions for improving future tool executions.
        
        Returns:
            A list of improvement suggestions
        """
        if not self.error_history:
            return ["No errors encountered, no improvements needed."]
        
        suggestions = []
        
        # Analyze error frequency by type
        error_type_counts = {}
        for error in self.error_history:
            error_type = error.get("error_type", "unknown")
            if error_type not in error_type_counts:
                error_type_counts[error_type] = 0
            error_type_counts[error_type] += 1
        
        # Analyze tool-specific errors
        tool_errors = {}
        for error in self.error_history:
            tool = error.get("tool")
            if tool not in tool_errors:
                tool_errors[tool] = []
            tool_errors[tool].append(error)
        
        # Generate general suggestions based on error types
        for error_type, count in error_type_counts.items():
            if error_type == "timeout" and count >= 2:
                suggestions.append("Increase default timeout values for all requests")
                suggestions.append("Consider breaking complex tasks into smaller steps")
                suggestions.append("Implement progressive timeout strategy that increases with each retry")
            
            elif error_type == "anti_scraping" and count >= 1:
                suggestions.append("Implement more sophisticated stealth techniques")
                suggestions.append("Consider using official APIs instead of web scraping")
                suggestions.append("Add random delays between actions to mimic human behavior")
                suggestions.append("Implement user agent rotation to avoid detection")
                suggestions.append("Consider using a proxy rotation service for challenging websites")
            
            elif error_type == "extraction" and count >= 2:
                suggestions.append("Use more robust and flexible selectors for extraction")
                suggestions.append("Implement multiple extraction methods as fallbacks")
                suggestions.append("Try JavaScript-based extraction when DOM selectors fail")
                suggestions.append("Consider using AI-based content extraction for complex layouts")
            
            elif error_type == "connection" and count >= 2:
                suggestions.append("Implement automatic retry with exponential backoff")
                suggestions.append("Check network connectivity before attempting connections")
                suggestions.append("Consider using a different network interface if available")
            
            elif error_type == "not_found" and count >= 2:
                suggestions.append("Implement content verification before extraction attempts")
                suggestions.append("Check for alternative URLs or sources for the same content")
                suggestions.append("Consider using web archives or cached versions")
            
            elif error_type == "authentication" and count >= 1:
                suggestions.append("Implement proper authentication handling with credential management")
                suggestions.append("Consider using API tokens instead of browser-based authentication")
                suggestions.append("Develop session management to maintain authenticated state")
            
            elif error_type == "server_error" and count >= 1:
                suggestions.append("Implement automatic retry with increasing delays for server errors")
                suggestions.append("Consider checking service status before retrying")
                suggestions.append("Look for alternative mirrors or endpoints for the same service")
            
            elif error_type == "syntax" and count >= 2:
                suggestions.append("Improve parsing robustness with multiple format handlers")
                suggestions.append("Implement format detection before parsing attempts")
                suggestions.append("Consider using more lenient parsing libraries")
        
        # Generate tool-specific suggestions
        for tool, errors in tool_errors.items():
            if tool == "enhanced_browser" and len(errors) >= 3:
                suggestions.append("Consider using a headless browser with more advanced capabilities")
                suggestions.append("Implement browser fingerprint randomization techniques")
                suggestions.append("Try different browser engines (Chrome/Firefox/WebKit) for problematic sites")
            
            elif tool == "web_search" and len(errors) >= 2:
                suggestions.append("Try alternative search engines or specialized search APIs")
                suggestions.append("Implement query reformulation strategies for better results")
                suggestions.append("Consider using domain-specific search engines for specialized content")
        
        # Analyze patterns in URL-based errors
        url_patterns = {}
        for error in self.error_history:
            params = error.get("params", {})
            url = params.get("url", "")
            if url:
                domain = re.search(r'https?://([^/]+)', url)
                if domain:
                    domain = domain.group(1)
                    if domain not in url_patterns:
                        url_patterns[domain] = 0
                    url_patterns[domain] += 1
        
        # Generate domain-specific suggestions
        for domain, count in url_patterns.items():
            if count >= 2:
                suggestions.append(f"Develop specialized handling for {domain} which has frequent errors")
                
                # Special handling for known problematic domains
                if "huggingface" in domain:
                    suggestions.append("For Hugging Face, consider using their API or CLI tools instead of web scraping")
                    suggestions.append("Implement Hugging Face token authentication for better access")
                
                elif any(term in domain for term in ["github", "gitlab"]):
                    suggestions.append(f"For {domain}, consider using their API instead of web scraping")
                    suggestions.append(f"Implement proper rate limiting for {domain} requests")
        
        # Deduplicate suggestions
        return list(dict.fromkeys(suggestions))
    
    def get_error_summary(self) -> str:
        """
        Generate a summary of encountered errors for reporting to the user.
        
        Returns:
            A formatted string summarizing the errors
        """
        if not self.error_history:
            return "No errors encountered."
        
        summary = ["Error Summary:"]
        
        # Group errors by type
        error_types = {}
        for error in self.error_history:
            error_type = error.get("error_type", "unknown")
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(error)
        
        # Summarize each error type
        for error_type, errors in error_types.items():
            summary.append(f"  {error_type.capitalize()} errors: {len(errors)}")
            # Include the most recent error message of this type
            if errors:
                latest = max(errors, key=lambda e: e.get("timestamp", datetime.min))
                summary.append(f"    Latest: {latest.get('message', 'No message')}")
        
        return "\n".join(summary)
    
    def get_manual_fallback_instructions(self, task_description: str) -> str:
        """
        Generate manual fallback instructions when all automated methods fail.
        
        Args:
            task_description: Description of the task that failed
            
        Returns:
            Instructions for manual intervention
        """
        # Extract key information from error history
        tools_tried = set(error.get("tool") for error in self.error_history)
        actions_tried = set(error.get("action") for error in self.error_history)
        error_types = set(error.get("error_type") for error in self.error_history)
        
        # Generate appropriate manual instructions based on the context
        instructions = ["All automated methods have been exhausted. Here are manual instructions to complete the task:"]
        
        # For Hugging Face model downloads
        if "model" in task_description.lower() and "download" in task_description.lower():
            model_name = None
            # Try to extract model name from task description or error history
            for error in self.error_history:
                params = error.get("params", {})
                url = params.get("url", "")
                if "huggingface.co" in url and "/" in url:
                    model_name = url.split("/")[-1]
                    break
            
            if model_name:
                instructions.append(f"\n1. Install the Hugging Face CLI if not already installed:\n   pip install huggingface_hub")
                instructions.append(f"\n2. Log in to Hugging Face (if required):\n   huggingface-cli login")
                instructions.append(f"\n3. Download the model using the CLI:\n   huggingface-cli download {model_name} --local-dir ./models/{model_name}")
            else:
                instructions.append(f"\n1. Install the Hugging Face CLI:\n   pip install huggingface_hub")
                instructions.append(f"\n2. Log in to Hugging Face (if required):\n   huggingface-cli login")
                instructions.append(f"\n3. Download the model using the CLI:\n   huggingface-cli download MODEL_NAME --local-dir ./models/MODEL_NAME")
                instructions.append(f"\n   Replace MODEL_NAME with the actual model name from the task.")
        
        # For website data extraction
        elif any(term in task_description.lower() for term in ["extract", "scrape", "data", "content"]):
            instructions.append(f"\n1. Try accessing the website manually in a regular browser.")
            instructions.append(f"\n2. If the website loads properly, you can:")
            instructions.append(f"   - Use the browser's 'Save As' feature to save the complete webpage")
            instructions.append(f"   - Use browser developer tools to inspect and copy the needed data")
            instructions.append(f"   - Consider using a browser extension like 'Web Scraper' for structured data")
            
            if "anti_scraping" in error_types or "timeout" in error_types:
                instructions.append(f"\n3. If you encounter anti-scraping measures:")
                instructions.append(f"   - Try using a different browser or clearing cookies")
                instructions.append(f"   - Consider using a VPN service")
                instructions.append(f"   - Look for official APIs that might provide the same data")
        
        # Generic fallback
        else:
            instructions.append(f"\n1. Review the error summary to understand what went wrong.")
            instructions.append(f"\n2. Consider alternative approaches to accomplish the task.")
            instructions.append(f"\n3. Check if there are official APIs or documentation that can help.")
        
        return "\n".join(instructions)