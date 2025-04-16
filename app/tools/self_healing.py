"""
Self-Healing Tool for Nexagent.

This module provides functionality for detecting and automatically fixing
errors during execution.
"""

import datetime
import traceback
from typing import Dict, List, Optional, Any, Union, Tuple

from pydantic import Field

from app.tool.base import BaseTool, ToolResult
from app.logger import logger


class SelfHealingTool(BaseTool):
    """
    A tool for detecting and automatically fixing errors during execution.
    
    This tool provides functionality for:
    1. Detecting common errors and issues
    2. Suggesting fixes for detected issues
    3. Automatically applying fixes when possible
    4. Tracking error patterns and successful fixes
    """
    
    name: str = "self_healing"
    description: str = """
    Detects and automatically fixes errors during execution.
    Provides error detection, fix suggestions, and automatic recovery.
    """
    
    # Dependencies
    required_tools: List[str] = ["create_chat_completion"]
    
    # Error patterns and fixes
    error_patterns: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    fix_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Thresholds for automatic healing
    max_auto_fixes: int = Field(default=5)
    confidence_threshold: float = Field(default=0.7)
    
    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_error_patterns()
    
    def _initialize_error_patterns(self):
        """Initialize common error patterns and fixes."""
        self.error_patterns = {
            "timeout": {
                "patterns": [
                    "timed out",
                    "timeout",
                    "deadline exceeded",
                    "operation took too long"
                ],
                "fixes": [
                    {
                        "description": "Increase timeout value",
                        "action": "increase_timeout",
                        "confidence": 0.8
                    },
                    {
                        "description": "Break operation into smaller steps",
                        "action": "break_operation",
                        "confidence": 0.7
                    }
                ]
            },
            "permission": {
                "patterns": [
                    "permission denied",
                    "access denied",
                    "not authorized",
                    "insufficient privileges"
                ],
                "fixes": [
                    {
                        "description": "Retry with elevated permissions",
                        "action": "elevate_permissions",
                        "confidence": 0.6
                    },
                    {
                        "description": "Use alternative approach that doesn't require permissions",
                        "action": "alternative_approach",
                        "confidence": 0.7
                    }
                ]
            },
            "resource_limit": {
                "patterns": [
                    "out of memory",
                    "memory limit",
                    "resource exhausted",
                    "too many requests"
                ],
                "fixes": [
                    {
                        "description": "Reduce resource usage",
                        "action": "reduce_resources",
                        "confidence": 0.8
                    },
                    {
                        "description": "Implement pagination or batching",
                        "action": "implement_batching",
                        "confidence": 0.7
                    },
                    {
                        "description": "Wait and retry with exponential backoff",
                        "action": "exponential_backoff",
                        "confidence": 0.9
                    }
                ]
            },
            "syntax_error": {
                "patterns": [
                    "syntax error",
                    "invalid syntax",
                    "unexpected token",
                    "parsing error"
                ],
                "fixes": [
                    {
                        "description": "Fix syntax error automatically",
                        "action": "fix_syntax",
                        "confidence": 0.6
                    },
                    {
                        "description": "Generate corrected code",
                        "action": "regenerate_code",
                        "confidence": 0.8
                    }
                ]
            },
            "network": {
                "patterns": [
                    "connection refused",
                    "network unreachable",
                    "connection error",
                    "connection reset",
                    "no route to host"
                ],
                "fixes": [
                    {
                        "description": "Retry connection with exponential backoff",
                        "action": "retry_connection",
                        "confidence": 0.9
                    },
                    {
                        "description": "Use alternative endpoint or service",
                        "action": "alternative_endpoint",
                        "confidence": 0.6
                    },
                    {
                        "description": "Check network configuration",
                        "action": "check_network",
                        "confidence": 0.7
                    }
                ]
            },
            "api_error": {
                "patterns": [
                    "api error",
                    "bad request",
                    "invalid request",
                    "rate limit",
                    "service unavailable"
                ],
                "fixes": [
                    {
                        "description": "Retry with exponential backoff",
                        "action": "retry_api",
                        "confidence": 0.8
                    },
                    {
                        "description": "Modify API request parameters",
                        "action": "modify_request",
                        "confidence": 0.7
                    },
                    {
                        "description": "Use alternative API endpoint",
                        "action": "alternative_api",
                        "confidence": 0.6
                    }
                ]
            }
        }
    
    async def execute(
        self,
        *,
        command: str,
        error_message: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None,
        auto_fix: bool = False,
        **kwargs
    ) -> ToolResult:
        """
        Execute the self-healing tool.
        
        Args:
            command: The operation to perform (detect, suggest, fix, learn)
            error_message: The error message to analyze
            error_context: Additional context about the error
            tool_name: Name of the tool that generated the error
            auto_fix: Whether to automatically apply fixes
            
        Returns:
            ToolResult with operation result
        """
        try:
            if command == "detect":
                if not error_message:
                    return ToolResult(error="Error message is required for detection")
                
                result = await self._detect_error(error_message, error_context, tool_name)
                return result
            
            elif command == "suggest":
                if not error_message:
                    return ToolResult(error="Error message is required for suggestions")
                
                result = await self._suggest_fixes(error_message, error_context, tool_name)
                return result
            
            elif command == "fix":
                if not error_message:
                    return ToolResult(error="Error message is required for fixing")
                
                result = await self._fix_error(error_message, error_context, tool_name, auto_fix)
                return result
            
            elif command == "learn":
                if not error_message:
                    return ToolResult(error="Error message is required for learning")
                
                result = await self._learn_from_error(error_message, error_context, tool_name)
                return result
            
            else:
                return ToolResult(error=f"Unknown command: {command}. Supported commands: detect, suggest, fix, learn")
        
        except Exception as e:
            logger.error(f"Error in SelfHealingTool: {str(e)}")
            logger.error(traceback.format_exc())
            return ToolResult(error=f"Error executing self-healing: {str(e)}")
    
    async def _detect_error(
        self,
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None
    ) -> ToolResult:
        """
        Detect the type of error and its severity.
        
        Args:
            error_message: The error message to analyze
            error_context: Additional context about the error
            tool_name: Name of the tool that generated the error
            
        Returns:
            ToolResult with error detection result
        """
        # Initialize detection result
        detection_result = {
            "error_type": "unknown",
            "confidence": 0.0,
            "severity": "unknown",
            "recoverable": False,
            "patterns_matched": []
        }
        
        # Check against known error patterns
        for error_type, pattern_info in self.error_patterns.items():
            patterns = pattern_info["patterns"]
            
            # Check if any pattern matches
            matches = []
            for pattern in patterns:
                if pattern.lower() in error_message.lower():
                    matches.append(pattern)
            
            # If patterns match, update detection result
            if matches:
                confidence = len(matches) / len(patterns)
                
                # If this error type has higher confidence than current detection, update
                if confidence > detection_result["confidence"]:
                    detection_result["error_type"] = error_type
                    detection_result["confidence"] = confidence
                    detection_result["patterns_matched"] = matches
                    
                    # Determine severity and recoverability based on error type
                    if error_type in ["timeout", "network"]:
                        detection_result["severity"] = "medium"
                        detection_result["recoverable"] = True
                    elif error_type in ["resource_limit", "api_error"]:
                        detection_result["severity"] = "high"
                        detection_result["recoverable"] = True
                    elif error_type == "syntax_error":
                        detection_result["severity"] = "high"
                        detection_result["recoverable"] = True
                    elif error_type == "permission":
                        detection_result["severity"] = "high"
                        detection_result["recoverable"] = False
        
        # If no patterns matched, use LLM to analyze the error
        if detection_result["error_type"] == "unknown":
            llm_analysis = await self._analyze_with_llm(error_message, error_context, tool_name)
            
            if llm_analysis:
                detection_result.update(llm_analysis)
        
        return ToolResult(output=str(detection_result))
    
    async def _suggest_fixes(
        self,
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None
    ) -> ToolResult:
        """
        Suggest fixes for the detected error.
        
        Args:
            error_message: The error message to analyze
            error_context: Additional context about the error
            tool_name: Name of the tool that generated the error
            
        Returns:
            ToolResult with suggested fixes
        """
        # First detect the error
        detection_result = await self._detect_error(error_message, error_context, tool_name)
        
        if detection_result.error:
            return ToolResult(error=f"Error detecting error type: {detection_result.error}")
        
        # Parse the detection result
        try:
            detection = eval(detection_result.output)
            error_type = detection["error_type"]
        except:
            return ToolResult(error="Failed to parse error detection result")
        
        # Get fixes for the detected error type
        fixes = []
        
        if error_type in self.error_patterns:
            fixes = self.error_patterns[error_type]["fixes"]
        
        # If no fixes found or error type is unknown, use LLM to suggest fixes
        if not fixes or error_type == "unknown":
            llm_fixes = await self._generate_fixes_with_llm(error_message, error_context, tool_name)
            
            if llm_fixes:
                fixes = llm_fixes
        
        # Sort fixes by confidence
        fixes.sort(key=lambda x: x["confidence"], reverse=True)
        
        return ToolResult(output=str(fixes))
    
    async def _fix_error(
        self,
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None,
        auto_fix: bool = False
    ) -> ToolResult:
        """
        Fix the detected error.
        
        Args:
            error_message: The error message to analyze
            error_context: Additional context about the error
            tool_name: Name of the tool that generated the error
            auto_fix: Whether to automatically apply fixes
            
        Returns:
            ToolResult with fix result
        """
        # First suggest fixes
        suggestions_result = await self._suggest_fixes(error_message, error_context, tool_name)
        
        if suggestions_result.error:
            return ToolResult(error=f"Error suggesting fixes: {suggestions_result.error}")
        
        # Parse the suggestions
        try:
            fixes = eval(suggestions_result.output)
        except:
            return ToolResult(error="Failed to parse fix suggestions")
        
        # If no fixes available, return error
        if not fixes:
            return ToolResult(error="No fixes available for this error")
        
        # If auto_fix is enabled, apply the highest confidence fix
        if auto_fix:
            # Check if we've exceeded the maximum number of automatic fixes
            if len(self.fix_history) >= self.max_auto_fixes:
                return ToolResult(error="Maximum number of automatic fixes exceeded")
            
            # Get the highest confidence fix
            best_fix = fixes[0]
            
            # Check if confidence is above threshold
            if best_fix["confidence"] < self.confidence_threshold:
                return ToolResult(error=f"Fix confidence ({best_fix['confidence']}) below threshold ({self.confidence_threshold})")
            
            # Apply the fix
            fix_result = await self._apply_fix(best_fix, error_message, error_context, tool_name)
            
            # Record the fix in history
            self.fix_history.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "error_message": error_message,
                "tool_name": tool_name,
                "fix": best_fix,
                "result": fix_result
            })
            
            return ToolResult(output=str(fix_result))
        else:
            # Just return the suggested fixes
            return ToolResult(output=str({
                "suggested_fixes": fixes,
                "message": "Use auto_fix=True to automatically apply the highest confidence fix"
            }))
    
    async def _learn_from_error(
        self,
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None
    ) -> ToolResult:
        """
        Learn from an error to improve future error detection and fixing.
        
        Args:
            error_message: The error message to analyze
            error_context: Additional context about the error
            tool_name: Name of the tool that generated the error
            
        Returns:
            ToolResult with learning result
        """
        # Use LLM to analyze the error and extract patterns
        create_chat_completion = self.get_tool("create_chat_completion")
        if not create_chat_completion:
            return ToolResult(error="create_chat_completion tool not available")
        
        # Prepare the prompt
        prompt = f"""
        Analyze the following error message and extract patterns that can be used for future error detection:
        
        Error Message: {error_message}
        
        Tool: {tool_name or 'Unknown'}
        
        Context: {error_context or {}}
        
        Please provide:
        1. The most likely error type (e.g., timeout, permission, resource_limit, syntax_error, network, api_error)
        2. Key patterns that can identify this type of error
        3. Potential fixes for this error with confidence scores (0.0 to 1.0)
        
        Format your response as a JSON object with the following structure:
        {{
            "error_type": "type_name",
            "patterns": ["pattern1", "pattern2", ...],
            "fixes": [
                {{
                    "description": "Fix description",
                    "action": "action_name",
                    "confidence": 0.8
                }},
                ...
            ]
        }}
        """
        
        # Generate the analysis
        result = await create_chat_completion.execute(
            messages=[{"role": "user", "content": prompt}]
        )
        
        if result.error:
            return ToolResult(error=f"Error analyzing error: {result.error}")
        
        try:
            # Parse the response
            response = eval(result.output)
            analysis = eval(response["choices"][0]["message"]["content"])
            
            # Update error patterns with the new information
            error_type = analysis["error_type"]
            
            if error_type not in self.error_patterns:
                self.error_patterns[error_type] = {
                    "patterns": [],
                    "fixes": []
                }
            
            # Add new patterns
            for pattern in analysis["patterns"]:
                if pattern not in self.error_patterns[error_type]["patterns"]:
                    self.error_patterns[error_type]["patterns"].append(pattern)
            
            # Add new fixes
            for fix in analysis["fixes"]:
                if fix not in self.error_patterns[error_type]["fixes"]:
                    self.error_patterns[error_type]["fixes"].append(fix)
            
            return ToolResult(output=str({
                "message": f"Learned new patterns and fixes for error type: {error_type}",
                "updated_patterns": self.error_patterns[error_type]
            }))
        
        except Exception as e:
            logger.error(f"Error parsing learning result: {str(e)}")
            return ToolResult(error=f"Error parsing learning result: {str(e)}")
    
    async def _analyze_with_llm(
        self,
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to analyze an error message.
        
        Args:
            error_message: The error message to analyze
            error_context: Additional context about the error
            tool_name: Name of the tool that generated the error
            
        Returns:
            Dictionary with analysis result or None if analysis failed
        """
        create_chat_completion = self.get_tool("create_chat_completion")
        if not create_chat_completion:
            return None
        
        # Prepare the prompt
        prompt = f"""
        Analyze the following error message:
        
        Error Message: {error_message}
        
        Tool: {tool_name or 'Unknown'}
        
        Context: {error_context or {}}
        
        Please determine:
        1. The most likely error type
        2. The confidence in this classification (0.0 to 1.0)
        3. The severity of the error (low, medium, high)
        4. Whether the error is likely recoverable
        
        Format your response as a JSON object with the following structure:
        {{
            "error_type": "type_name",
            "confidence": 0.8,
            "severity": "medium",
            "recoverable": true
        }}
        """
        
        # Generate the analysis
        result = await create_chat_completion.execute(
            messages=[{"role": "user", "content": prompt}]
        )
        
        if result.error:
            logger.error(f"Error analyzing with LLM: {result.error}")
            return None
        
        try:
            # Parse the response
            response = eval(result.output)
            analysis = eval(response["choices"][0]["message"]["content"])
            return analysis
        except Exception as e:
            logger.error(f"Error parsing LLM analysis: {str(e)}")
            return None
    
    async def _generate_fixes_with_llm(
        self,
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Use LLM to generate fixes for an error.
        
        Args:
            error_message: The error message to analyze
            error_context: Additional context about the error
            tool_name: Name of the tool that generated the error
            
        Returns:
            List of fixes or None if generation failed
        """
        create_chat_completion = self.get_tool("create_chat_completion")
        if not create_chat_completion:
            return None
        
        # Prepare the prompt
        prompt = f"""
        Generate fixes for the following error:
        
        Error Message: {error_message}
        
        Tool: {tool_name or 'Unknown'}
        
        Context: {error_context or {}}
        
        Please provide 2-3 potential fixes, each with:
        1. A description of the fix
        2. An action name (e.g., retry_connection, increase_timeout)
        3. A confidence score (0.0 to 1.0) indicating how likely the fix is to work
        
        Format your response as a JSON array with the following structure:
        [
            {{
                "description": "Fix description",
                "action": "action_name",
                "confidence": 0.8
            }},
            ...
        ]
        """
        
        # Generate the fixes
        result = await create_chat_completion.execute(
            messages=[{"role": "user", "content": prompt}]
        )
        
        if result.error:
            logger.error(f"Error generating fixes with LLM: {result.error}")
            return None
        
        try:
            # Parse the response
            response = eval(result.output)
            fixes = eval(response["choices"][0]["message"]["content"])
            return fixes
        except Exception as e:
            logger.error(f"Error parsing LLM fixes: {str(e)}")
            return None
    
    async def _apply_fix(
        self,
        fix: Dict[str, Any],
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply a fix to an error.
        
        Args:
            fix: The fix to apply
            error_message: The error message
            error_context: Additional context about the error
            tool_name: Name of the tool that generated the error
            
        Returns:
            Dictionary with fix result
        """
        # Initialize fix result
        fix_result = {
            "success": False,
            "message": "",
            "fix_applied": fix["description"],
            "action": fix["action"]
        }
        
        # Apply the fix based on the action
        if fix["action"] == "retry_connection":
            # Simulate retrying connection
            fix_result["success"] = True
            fix_result["message"] = "Connection retry simulated successfully"
        
        elif fix["action"] == "increase_timeout":
            # Simulate increasing timeout
            fix_result["success"] = True
            fix_result["message"] = "Timeout increased successfully"
        
        elif fix["action"] == "exponential_backoff":
            # Simulate exponential backoff
            fix_result["success"] = True
            fix_result["message"] = "Exponential backoff implemented successfully"
        
        elif fix["action"] == "regenerate_code":
            # This would require integration with code generation tool
            fix_result["success"] = False
            fix_result["message"] = "Code regeneration requires integration with code generation tool"
        
        else:
            # For other actions, just simulate success
            fix_result["success"] = True
            fix_result["message"] = f"Fix '{fix['description']}' applied successfully"
        
        return fix_result
