from typing import Any, Dict, Optional, Tuple, Union
import asyncio
import json
import re

from app.tool.base import ToolResult
from app.tool.error_handler import ErrorHandler
from app.logger import logger


class ErrorHandlerIntegration:
    """
    Integration class for the ErrorHandler with NexAgent's tool execution flow.
    
    This class provides methods to integrate error handling and fallback mechanisms
    into the NexAgent's tool execution process.
    """
    
    def __init__(self):
        self.error_handler = ErrorHandler()
        self.current_fallback_chain = {}
    
    async def execute_with_fallback(self, tool_name: str, action: str, params: Dict, execute_func) -> Any:
        """
        Execute a tool with automatic fallback mechanisms if errors occur.
        
        Args:
            tool_name: The name of the tool to execute
            action: The specific action being performed
            params: The parameters for the tool execution
            execute_func: The function to call for executing the tool
            
        Returns:
            The result of the tool execution or fallback
        """
        # Create a key for tracking this specific tool+action combination
        tool_action_key = f"{tool_name}:{action}"
        
        # Initialize or get the current attempt number
        if tool_action_key not in self.current_fallback_chain:
            self.current_fallback_chain[tool_action_key] = 0
        else:
            self.current_fallback_chain[tool_action_key] += 1
        
        attempt_number = self.current_fallback_chain[tool_action_key]
        
        # Log the attempt
        if attempt_number > 0:
            logger.info(f"🔄 Fallback attempt #{attempt_number} for {tool_name}.{action}")
        
        # Execute the tool
        try:
            result = await execute_func(**params)
            
            # Check if the result indicates success
            if self.error_handler.is_result_successful(result):
                # Reset the fallback chain for this tool+action on success
                self.current_fallback_chain[tool_action_key] = 0
                return result
            
            # Extract error message
            error_message = result.error if isinstance(result, ToolResult) else str(result)
            
            # Record the error
            self.error_handler.record_error(tool_name, action, error_message, params)
            
            # Check if we should try a fallback
            if self.error_handler.should_try_fallback(tool_name, action):
                # Get the error type
                error_type = self.error_handler.detect_error_type(error_message)
                
                # Get fallback strategy
                fallback_tool, fallback_params = self.error_handler.get_fallback_strategy(
                    tool_name, action, error_type, params
                )
                
                # Log the fallback strategy
                logger.info(f"🔀 Using fallback strategy: {fallback_tool} with modified parameters")
                
                # If the fallback tool is different, we need to execute it differently
                if fallback_tool != tool_name:
                    # This would need to be handled by the agent's execute_tool method
                    return {
                        "fallback": True,
                        "tool": fallback_tool,
                        "params": fallback_params,
                        "original_error": error_message
                    }
                
                # Otherwise, recursively try the fallback with the same tool but different params
                return await self.execute_with_fallback(
                    tool_name, 
                    fallback_params.get("action", action),
                    fallback_params,
                    execute_func
                )
            
            # If we've exhausted fallbacks, return the original result
            return result
            
        except Exception as e:
            # Handle any exceptions during execution
            error_message = str(e)
            self.error_handler.record_error(tool_name, action, error_message, params)
            
            # Return as a ToolResult with error
            return ToolResult(error=f"Error executing {tool_name}.{action}: {error_message}")
    
    def analyze_error_patterns(self) -> Dict[str, Any]:
        """
        Analyze error patterns to provide insights for the agent.
        
        Returns:
            A dictionary with error pattern analysis
        """
        if not self.error_handler.error_history:
            return {"patterns": [], "recommendations": [], "critical_issues": [], "success_rate": 100}
        
        # Count errors by type
        error_counts = {}
        for error in self.error_handler.error_history:
            error_type = error.get("error_type", "unknown")
            if error_type not in error_counts:
                error_counts[error_type] = 0
            error_counts[error_type] += 1
        
        # Identify most common error types
        common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Generate recommendations based on error patterns
        recommendations = []
        critical_issues = []
        
        if common_errors:
            most_common_type, count = common_errors[0]
            
            if most_common_type == "timeout" and count >= 2:
                recommendations.append("Consider increasing default timeout values for future requests")
                recommendations.append("Break complex tasks into smaller steps to avoid timeouts")
                
                if count >= 4:
                    critical_issues.append("Persistent timeout issues detected - consider fundamental approach change")
            
            if most_common_type == "anti_scraping" and count >= 2:
                recommendations.append("Website likely has strong anti-scraping measures; consider using APIs or alternative data sources")
                recommendations.append("Implement more sophisticated stealth techniques and user agent rotation")
                
                if count >= 3:
                    critical_issues.append("Strong anti-scraping measures detected - direct scraping may not be viable")
            
            if most_common_type == "extraction" and count >= 2:
                recommendations.append("Extraction patterns may need refinement; consider using more robust selectors")
                recommendations.append("Try multiple extraction methods (CSS, XPath, JavaScript) as fallbacks")
            
            if most_common_type == "server_error" and count >= 2:
                recommendations.append("Target server experiencing issues; implement exponential backoff retry strategy")
                recommendations.append("Consider checking service status before further attempts")
                
                if count >= 3:
                    critical_issues.append("Persistent server errors - service may be down or unstable")
        
        # Check for repeated failures with the same tool
        tool_failures = {}
        tool_attempts = {}
        for error in self.error_handler.error_history:
            tool = error.get("tool")
            if tool not in tool_failures:
                tool_failures[tool] = 0
                tool_attempts[tool] = 0
            tool_failures[tool] += 1
            tool_attempts[tool] += 1
        
        # Calculate success rates and identify problematic tools
        success_rates = {}
        overall_success_count = 0
        overall_attempt_count = sum(tool_attempts.values())
        
        for tool, failure_count in tool_failures.items():
            if tool in tool_attempts and tool_attempts[tool] > 0:
                success_count = tool_attempts[tool] - failure_count
                success_rate = (success_count / tool_attempts[tool]) * 100
                success_rates[tool] = success_rate
                overall_success_count += success_count
                
                if failure_count >= 3:
                    recommendations.append(f"Tool '{tool}' has failed multiple times; consider alternative approaches")
                    
                    if success_rate < 30 and tool_attempts[tool] >= 5:
                        critical_issues.append(f"Tool '{tool}' has very low success rate ({success_rate:.1f}%); urgent review needed")
        
        # Calculate overall success rate
        overall_success_rate = 100.0 if overall_attempt_count == 0 else (overall_success_count / overall_attempt_count) * 100
        
        # Check for domain-specific issues
        domain_failures = {}
        for error in self.error_handler.error_history:
            params = error.get("params", {})
            url = params.get("url", "")
            if url:
                domain_match = re.search(r'https?://([^/]+)', url)
                if domain_match:
                    domain = domain_match.group(1)
                    if domain not in domain_failures:
                        domain_failures[domain] = 0
                    domain_failures[domain] += 1
        
        for domain, count in domain_failures.items():
            if count >= 3:
                recommendations.append(f"Multiple failures with domain '{domain}'; consider specialized handling")
                
                # Special handling for known problematic domains
                if "huggingface" in domain:
                    recommendations.append("For Hugging Face, consider using their API or CLI tools instead of web scraping")
                    if count >= 5:
                        critical_issues.append("Hugging Face access is consistently failing - switch to CLI approach immediately")
        
        return {
            "patterns": common_errors,
            "recommendations": recommendations,
            "critical_issues": critical_issues,
            "success_rate": overall_success_rate,
            "tool_success_rates": success_rates
        }
    
    def get_manual_fallback_instructions(self, task_description: str) -> str:
        """
        Get manual fallback instructions when all automated methods fail.
        
        Args:
            task_description: Description of the task that failed
            
        Returns:
            Instructions for manual intervention
        """
        return self.error_handler.get_manual_fallback_instructions(task_description)
    
    def reset(self):
        """
        Reset the error handler state for a new task.
        """
        self.error_handler = ErrorHandler()
        self.current_fallback_chain = {}
    
    async def adaptive_execute(self, tool_name: str, action: str, params: Dict, execute_func, context: Dict = None) -> Any:
        """
        Execute a tool with adaptive error handling based on historical patterns.
        
        This method enhances execute_with_fallback by applying learned patterns from
        previous errors to preemptively adjust execution parameters.
        
        Args:
            tool_name: The name of the tool to execute
            action: The specific action being performed
            params: The parameters for the tool execution
            execute_func: The function to call for executing the tool
            context: Additional context about the current task
            
        Returns:
            The result of the tool execution or fallback
        """
        # Apply preemptive adjustments based on historical patterns
        adjusted_params = self._apply_preemptive_adjustments(tool_name, action, params, context)
        
        # Execute with the adjusted parameters and fallback mechanisms
        return await self.execute_with_fallback(tool_name, action, adjusted_params, execute_func)
    
    def _apply_preemptive_adjustments(self, tool_name: str, action: str, params: Dict, context: Dict = None) -> Dict:
        """
        Apply preemptive adjustments to parameters based on historical error patterns.
        
        Args:
            tool_name: The name of the tool
            action: The specific action
            params: The original parameters
            context: Additional context about the current task
            
        Returns:
            Adjusted parameters
        """
        # Clone the parameters for modification
        adjusted_params = params.copy() if params else {}
        context = context or {}
        
        # Get error analysis
        analysis = self.analyze_error_patterns()
        common_errors = dict(analysis.get("patterns", []))
        
        # Extract domain information if URL is present
        domain = None
        if "url" in adjusted_params:
            url = adjusted_params["url"]
            domain_match = re.search(r'https?://([^/]+)', url)
            if domain_match:
                domain = domain_match.group(1)
        
        # Apply tool-specific preemptive adjustments
        if tool_name == "enhanced_browser":
            # Check if we've had timeout issues
            if "timeout" in common_errors and common_errors["timeout"] >= 2:
                # Preemptively increase timeout
                current_timeout = adjusted_params.get("timeout", 30000)
                adjusted_params["timeout"] = int(current_timeout * 1.5)
                logger.info(f"🔧 Preemptively increasing timeout to {adjusted_params['timeout']}ms based on historical patterns")
            
            # Check if we've had anti-scraping issues
            if "anti_scraping" in common_errors and common_errors["anti_scraping"] >= 1:
                # Preemptively enable stealth mode
                if action not in ["stealth_mode", "rotate_user_agent"]:
                    logger.info(f"🕵️ Preemptively enabling stealth mode based on historical patterns")
                    # Store original action to restore after stealth mode
                    adjusted_params["_original_action"] = action
                    adjusted_params["action"] = "stealth_mode"
                    adjusted_params["enable"] = True
                    
                    # Add random delays
                    adjusted_params["min_delay"] = 1000
                    adjusted_params["max_delay"] = 3000
            
            # Domain-specific adjustments
            if domain:
                # Check if this domain has had issues
                domain_issues = False
                for error in self.error_handler.error_history:
                    error_params = error.get("params", {})
                    error_url = error_params.get("url", "")
                    if domain in error_url:
                        domain_issues = True
                        break
                
                if domain_issues:
                    logger.info(f"🌐 Applying domain-specific adjustments for {domain}")
                    
                    # Known problematic domains
                    if "huggingface" in domain:
                        # Hugging Face often needs longer timeouts
                        adjusted_params["timeout"] = max(adjusted_params.get("timeout", 30000), 60000)
                    
                    elif any(term in domain for term in ["cloudflare", "cf-protected"]):
                        # Sites with Cloudflare protection need special handling
                        logger.info(f"☁️ Detected Cloudflare-protected site, applying specialized settings")
                        adjusted_params["_cf_protection"] = True
                        
                        # Execute anti-detection JavaScript
                        if action == "navigate":
                            # Store original action to restore after JS execution
                            adjusted_params["_original_action"] = action
                            adjusted_params["action"] = "execute_js"
                            adjusted_params["script"] = """
                            // Advanced Cloudflare bypass techniques
                            // Hide automation fingerprints
                            Object.defineProperty(navigator, 'webdriver', {get: () => false});
                            // Add fake plugins
                            Object.defineProperty(navigator, 'plugins', {get: () => [
                                {name: 'Chrome PDF Plugin'}, {name: 'Chrome PDF Viewer'}, 
                                {name: 'Native Client'}, {name: 'Widevine Content Decryption Module'}
                            ]});
                            // Modify user agent subtly
                            Object.defineProperty(navigator, 'userAgent', {get: () => navigator.userAgent.replace('Headless', '')});
                            // Add touch support
                            Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 5});
                            """
        
        # For web search, adjust based on previous search patterns
        elif tool_name == "web_search":
            query = adjusted_params.get("query", "")
            
            # If we've had extraction issues, make search more specific
            if "extraction" in common_errors and common_errors["extraction"] >= 2:
                if not any(term in query.lower() for term in ["exact", "specific", "detailed"]):
                    adjusted_params["query"] = f"detailed {query}"
                    logger.info(f"🔍 Making search query more specific based on historical extraction issues")
        
        return adjusted_params
    
    def get_proxy_rotation_strategy(self) -> Dict[str, Any]:
        """
        Generate a proxy rotation strategy based on error patterns.
        
        Returns:
            A dictionary with proxy configuration recommendations
        """
        # Analyze error patterns to determine if proxy rotation is needed
        analysis = self.analyze_error_patterns()
        common_errors = dict(analysis.get("patterns", []))
        critical_issues = analysis.get("critical_issues", [])
        
        proxy_strategy = {
            "should_use_proxy": False,
            "rotation_frequency": "low",  # low, medium, high
            "proxy_type": "http",  # http, socks5
            "recommendations": []
        }
        
        # Determine if proxy is needed based on error patterns
        anti_scraping_count = common_errors.get("anti_scraping", 0)
        timeout_count = common_errors.get("timeout", 0)
        connection_count = common_errors.get("connection", 0)
        
        # If we have anti-scraping issues, proxy rotation is recommended
        if anti_scraping_count >= 2:
            proxy_strategy["should_use_proxy"] = True
            proxy_strategy["recommendations"].append("Use proxy rotation to bypass anti-scraping measures")
            
            # Determine rotation frequency based on severity
            if anti_scraping_count >= 5 or any("anti-scraping" in issue.lower() for issue in critical_issues):
                proxy_strategy["rotation_frequency"] = "high"  # Rotate on every request
                proxy_strategy["recommendations"].append("Use high-frequency proxy rotation (every request)")
            elif anti_scraping_count >= 3:
                proxy_strategy["rotation_frequency"] = "medium"  # Rotate every few requests
                proxy_strategy["recommendations"].append("Use medium-frequency proxy rotation (every 3-5 requests)")
        
        # If we have connection issues, consider using more reliable proxies
        if connection_count >= 3:
            proxy_strategy["should_use_proxy"] = True
            proxy_strategy["recommendations"].append("Use premium/reliable proxies to avoid connection issues")
        
        # If we have timeout issues, consider using faster proxies
        if timeout_count >= 3:
            proxy_strategy["should_use_proxy"] = True
            proxy_strategy["recommendations"].append("Use proxies with lower latency to reduce timeout issues")
        
        # Provide implementation suggestions
        if proxy_strategy["should_use_proxy"]:
            proxy_strategy["implementation_suggestions"] = [
                "Consider using a proxy rotation service API",
                "Implement proxy health checking before use",
                "Maintain a list of working proxies with success rates"
            ]
        
        return proxy_strategy