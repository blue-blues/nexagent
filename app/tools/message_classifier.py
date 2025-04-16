"""
Message Classifier Tool

This module provides a tool for classifying messages as either simple chat messages
or messages that require agent processing (agentic factors).
"""

import re
from typing import Dict, List, Optional, Tuple, Any

from pydantic import Field

from app.logger import logger
from app.tools.base import BaseTool, ToolResult


class MessageClassifier(BaseTool):
    """
    A tool for classifying messages as either chat or agent-requiring.

    This tool analyzes input text to determine if it's a simple chat message
    that can be handled directly, or if it requires more complex agent processing.
    """

    name: str = "message_classifier"
    description: str = """
    Classify messages as either simple chat messages or messages requiring agent processing.
    This tool helps determine the appropriate handling path for user inputs.
    """

    # Classification thresholds
    chat_threshold: float = Field(default=0.3, description="Threshold for classifying as chat")
    agent_threshold: float = Field(default=0.6, description="Threshold for classifying as agent-requiring")

    # Patterns that indicate a message is likely a simple chat
    chat_patterns: List[str] = Field(default=[
        r"^hi+\s*$",
        r"^hello+\s*$",
        r"^hey+\s*$",
        r"^thanks+\s*$",
        r"^thank you+\s*$",
        r"^ok+\s*$",
        r"^okay+\s*$",
        r"^yes+\s*$",
        r"^no+\s*$",
        r"^bye+\s*$",
        r"^goodbye+\s*$",
        r"^how are you+\s*$",
        r"^good morning+\s*$",
        r"^good afternoon+\s*$",
        r"^good evening+\s*$",
        r"^good night+\s*$",
    ], description="Regex patterns that indicate a message is likely a simple chat")

    # Compiled regex patterns for efficiency
    compiled_chat_patterns: List[Any] = Field(default=None, description="Compiled regex patterns for efficiency")

    # Keywords that indicate a message likely requires agent processing
    agent_keywords: List[str] = Field(default=[
        "create", "make", "build", "develop", "implement", "code", "program",
        "analyze", "research", "find", "search", "look up", "investigate",
        "explain", "describe", "elaborate", "clarify", "help me understand",
        "solve", "fix", "debug", "troubleshoot", "optimize", "improve",
        "compare", "contrast", "differentiate", "distinguish",
        "summarize", "synthesize", "compile", "gather",
        "plan", "design", "architect", "structure",
        "calculate", "compute", "determine", "evaluate",
        "write", "draft", "compose", "author",
        "translate", "convert", "transform",
        "organize", "arrange", "sort", "classify",
        "predict", "forecast", "project", "estimate",
        "recommend", "suggest", "advise", "propose",
        "can you", "could you", "would you", "please",
    ], description="Keywords that indicate a message likely requires agent processing")

    # Indicators of complexity that suggest agent processing
    complexity_indicators: List[str] = Field(default=[
        "step by step", "detailed", "comprehensive", "thorough",
        "in depth", "extensively", "completely", "fully",
        "specifically", "precisely", "exactly", "accurately",
        "carefully", "meticulously", "rigorously", "systematically",
    ], description="Indicators of complexity that suggest agent processing")

    parameters: dict = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message to classify",
            },
            "conversation_history": {
                "type": "array",
                "description": "Optional conversation history for context",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
            },
            "threshold_override": {
                "type": "object",
                "description": "Optional override for classification thresholds",
                "properties": {
                    "chat_threshold": {"type": "number"},
                    "agent_threshold": {"type": "number"},
                },
            },
        },
        "required": ["message"],
    }

    def __init__(self):
        """Initialize the MessageClassifier tool."""
        super().__init__()
        # Compile regex patterns for efficiency
        if self.compiled_chat_patterns is None:
            self.compiled_chat_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.chat_patterns]

    def _check_chat_patterns(self, message: str) -> bool:
        """Check if the message matches any chat patterns."""
        return any(pattern.match(message) for pattern in self.compiled_chat_patterns)

    def _count_agent_keywords(self, message: str) -> int:
        """Count the number of agent keywords in the message."""
        message_lower = message.lower()
        return sum(1 for keyword in self.agent_keywords if keyword.lower() in message_lower)

    def _count_complexity_indicators(self, message: str) -> int:
        """Count the number of complexity indicators in the message."""
        message_lower = message.lower()
        return sum(1 for indicator in self.complexity_indicators if indicator.lower() in message_lower)

    def _calculate_message_length_score(self, message: str) -> float:
        """Calculate a score based on message length (longer messages are more likely to require agent processing)."""
        # Split into words and count
        word_count = len(message.split())

        # Normalize: 0-10 words: 0.0-0.3, 10-50 words: 0.3-0.7, 50+ words: 0.7-1.0
        if word_count < 10:
            return min(0.3, word_count / 10 * 0.3)
        elif word_count < 50:
            return 0.3 + (word_count - 10) / 40 * 0.4
        else:
            return min(1.0, 0.7 + (word_count - 50) / 100 * 0.3)

    def _calculate_question_score(self, message: str) -> float:
        """Calculate a score based on whether the message is a question."""
        # Check for question marks
        question_mark_count = message.count('?')

        # Check for question words
        question_words = ['what', 'who', 'where', 'when', 'why', 'how', 'which', 'can', 'could', 'would', 'should', 'is', 'are', 'do', 'does', 'did']
        starts_with_question_word = any(message.lower().split()[0] == word for word in question_words if message.split())

        # Calculate score
        if question_mark_count > 0 and starts_with_question_word:
            return 0.8  # Strong indicator of a question requiring agent processing
        elif question_mark_count > 0 or starts_with_question_word:
            return 0.6  # Moderate indicator
        else:
            return 0.0  # Not a question

    def _calculate_code_score(self, message: str) -> float:
        """Calculate a score based on whether the message contains code or code-like elements."""
        # Check for code blocks
        code_block_pattern = re.compile(r'```[\s\S]*?```')
        has_code_blocks = bool(code_block_pattern.search(message))

        # Check for inline code
        inline_code_pattern = re.compile(r'`[^`]+`')
        has_inline_code = bool(inline_code_pattern.search(message))

        # Check for code-like symbols
        code_symbols = ['()', '{}', '[]', ';', '==', '!=', '>=', '<=', '=>', '->', '+=', '-=', '*=', '/=', '%=']
        has_code_symbols = any(symbol in message for symbol in code_symbols)

        # Calculate score
        if has_code_blocks:
            return 1.0  # Definite code requiring agent processing
        elif has_inline_code and has_code_symbols:
            return 0.9  # Very likely code
        elif has_inline_code or has_code_symbols:
            return 0.7  # Possibly code-related
        else:
            return 0.0  # No code detected

    def _analyze_message(self, message: str) -> Dict[str, Any]:
        """
        Analyze a message to determine if it's a chat message or requires agent processing.

        Args:
            message: The message to analyze

        Returns:
            A dictionary with analysis results
        """
        # Check for direct matches with chat patterns
        is_chat_pattern = self._check_chat_patterns(message)

        # Count agent keywords and complexity indicators
        agent_keyword_count = self._count_agent_keywords(message)
        complexity_indicator_count = self._count_complexity_indicators(message)

        # Calculate scores
        length_score = self._calculate_message_length_score(message)
        question_score = self._calculate_question_score(message)
        code_score = self._calculate_code_score(message)

        # Calculate keyword density (normalized by message length)
        word_count = max(1, len(message.split()))
        keyword_density = min(1.0, agent_keyword_count / word_count * 5)  # Scale up for significance
        complexity_density = min(1.0, complexity_indicator_count / word_count * 10)  # Scale up for significance

        # Calculate final scores
        chat_score = 0.0
        agent_score = 0.0

        if is_chat_pattern:
            chat_score = 0.9  # Strong indicator of chat
        else:
            # Chat score decreases with length, question indicators, code, keywords, and complexity
            chat_score = max(0.0, 1.0 - (
                length_score * 0.3 +
                question_score * 0.2 +
                code_score * 0.3 +
                keyword_density * 0.1 +
                complexity_density * 0.1
            ))

        # Agent score increases with length, question indicators, code, keywords, and complexity
        agent_score = (
            length_score * 0.2 +
            question_score * 0.2 +
            code_score * 0.3 +
            keyword_density * 0.2 +
            complexity_density * 0.1
        )

        # Ensure scores are in valid range
        chat_score = max(0.0, min(1.0, chat_score))
        agent_score = max(0.0, min(1.0, agent_score))

        return {
            "chat_score": chat_score,
            "agent_score": agent_score,
            "is_chat_pattern": is_chat_pattern,
            "agent_keyword_count": agent_keyword_count,
            "complexity_indicator_count": complexity_indicator_count,
            "length_score": length_score,
            "question_score": question_score,
            "code_score": code_score,
            "keyword_density": keyword_density,
            "complexity_density": complexity_density,
            "word_count": word_count,
        }

    def _classify_message(self, message: str, chat_threshold: float = None, agent_threshold: float = None) -> Tuple[str, Dict[str, Any]]:
        """
        Classify a message as either chat or agent-requiring.

        Args:
            message: The message to classify
            chat_threshold: Optional override for chat threshold
            agent_threshold: Optional override for agent threshold

        Returns:
            A tuple of (classification, analysis_results)
        """
        # Use provided thresholds or defaults
        chat_threshold = chat_threshold if chat_threshold is not None else self.chat_threshold
        agent_threshold = agent_threshold if agent_threshold is not None else self.agent_threshold

        # Analyze the message
        analysis = self._analyze_message(message)

        # Determine classification
        if analysis["chat_score"] >= chat_threshold and analysis["agent_score"] < agent_threshold:
            classification = "chat"
        else:
            classification = "agent"

        return classification, analysis

    async def execute(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        threshold_override: Optional[Dict[str, float]] = None,
    ) -> ToolResult:
        """
        Classify a message as either chat or agent-requiring.

        Args:
            message: The message to classify
            conversation_history: Optional conversation history for context
            threshold_override: Optional override for classification thresholds

        Returns:
            ToolResult with classification and analysis
        """
        try:
            # Extract threshold overrides if provided
            chat_threshold = threshold_override.get("chat_threshold", self.chat_threshold) if threshold_override else self.chat_threshold
            agent_threshold = threshold_override.get("agent_threshold", self.agent_threshold) if threshold_override else self.agent_threshold

            # Classify the message
            classification, analysis = self._classify_message(message, chat_threshold, agent_threshold)

            # If conversation history is provided, we could use it to refine the classification
            # This is a placeholder for future enhancement
            if conversation_history:
                logger.debug(f"Conversation history provided with {len(conversation_history)} messages")
                # Future enhancement: Use conversation history to refine classification
                # For now, we'll just include it in the result

            # Prepare result
            result = {
                "classification": classification,
                "analysis": analysis,
                "thresholds": {
                    "chat_threshold": chat_threshold,
                    "agent_threshold": agent_threshold,
                }
            }

            # Log the classification
            logger.info(f"Message classified as '{classification}' (chat_score={analysis['chat_score']:.2f}, agent_score={analysis['agent_score']:.2f})")

            return ToolResult(output=result)
        except Exception as e:
            error_msg = f"Error classifying message: {str(e)}"
            logger.error(error_msg)
            return ToolResult(output={"error": error_msg}, error=True)
