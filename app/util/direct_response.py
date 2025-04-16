"""
Direct response utility for handling simple prompts without agent processing.

This module provides functions to identify simple prompts that don't require
the full agent system and generate appropriate direct responses.
"""

import re
from typing import Dict, Tuple, List, Optional

# Simple greeting patterns
GREETING_PATTERNS = [
    r"^hello$", r"^hi$", r"^hey$", r"^greetings$", r"^howdy$",
    r"^hello\s+there$", r"^hi\s+there$", r"^hey\s+there$",
    r"^good\s+morning$", r"^good\s+afternoon$", r"^good\s+evening$"
]

# Simple question patterns
SIMPLE_QUESTION_PATTERNS = [
    r"^how\s+are\s+you$", r"^what'?s\s+up$", r"^how'?s\s+it\s+going$",
    r"^what\s+can\s+you\s+do$", r"^who\s+are\s+you$", r"^what\s+are\s+you$",
    r"^which\s+model\s+is\s+this$", r"^what\s+model\s+are\s+you$", r"^which\s+llm\s+are\s+you$",
    r"^what\s+llm\s+are\s+you$", r"^which\s+ai\s+are\s+you$", r"^what\s+ai\s+are\s+you$",
    r"^what\s+is\s+\d+\s*[+\-*/]\s*\d+$",
    r"^\d+\s*[+\-*/]\s*\d+$",
    r"^who\s+is\s+elon\??$", r"^who\s+is\s+elon\s+musk\??$"
]

# Farewell patterns
FAREWELL_PATTERNS = [
    r"^bye$", r"^goodbye$", r"^see\s+you$", r"^farewell$", r"^exit$", r"^quit$"
]

# Thank you patterns
THANKS_PATTERNS = [
    r"^thanks$", r"^thank\s+you$", r"^thx$", r"^ty$", r"^thanks\s+a\s+lot$"
]

# Compile all patterns for efficiency
ALL_PATTERNS = {
    "greeting": [re.compile(pattern, re.IGNORECASE) for pattern in GREETING_PATTERNS],
    "question": [re.compile(pattern, re.IGNORECASE) for pattern in SIMPLE_QUESTION_PATTERNS],
    "farewell": [re.compile(pattern, re.IGNORECASE) for pattern in FAREWELL_PATTERNS],
    "thanks": [re.compile(pattern, re.IGNORECASE) for pattern in THANKS_PATTERNS]
}

# Response templates for each category
RESPONSES = {
    "greeting": [
        "Hello! How can I help you today?",
        "Hi there! What can I assist you with?",
        "Hey! I'm Nexagent. What would you like me to help you with?",
        "Greetings! I'm ready to assist you."
    ],
    "question": {
        "how are you": [
            "I'm doing well, thank you for asking! How can I help you today?",
            "I'm functioning optimally and ready to assist you!"
        ],
        "what's up": [
            "Just waiting to help you with your tasks! What can I do for you?",
            "Ready and available to assist you! What's on your mind?"
        ],
        "how's it going": [
            "Everything is going well! I'm here and ready to help.",
            "All systems operational! What can I help you with today?"
        ],
        "what can you do": [
            "I can help with a variety of tasks including web browsing, code generation, planning, and more. What would you like assistance with?",
            "I'm designed to assist with tasks like information gathering, code development, planning, and problem-solving. Just let me know what you need!"
        ],
        "who are you": [
            "I'm Nexagent, an AI assistant designed to help with a variety of tasks including web browsing, code generation, and planning.",
            "I'm Nexagent, your AI assistant. I can help with information gathering, code development, planning, and more."
        ],
        "what are you": [
            "I'm an AI assistant called Nexagent, designed to help with tasks like web browsing, code generation, planning, and more.",
            "I'm an AI system designed to assist with various tasks and provide helpful responses to your questions and requests."
        ],
        "which model": [
            "I am Nexagent, powered by Claude 3.7 Sonnet, an AI assistant developed by Anthropic. I'm designed to be helpful, harmless, and honest in my interactions.",
            "I'm running on Claude 3.7 Sonnet, an AI model developed by Anthropic. I'm part of the Nexagent system designed to assist with various tasks."
        ],
        "math calculation": [
            "I can help with that calculation. Let me solve it for you."
        ],
        "who is elon": [
            "Elon Musk is a businessman known for his leadership of Tesla, SpaceX, and X (formerly Twitter). He is also the wealthiest person in the world.",
            "Elon Musk is an entrepreneur and business magnate who founded or co-founded companies including Tesla, SpaceX, Neuralink, and The Boring Company. He is known for his work in electric vehicles, space exploration, and renewable energy."
        ]
    },
    "farewell": [
        "Goodbye! Feel free to return if you need assistance later.",
        "Farewell! I'll be here if you need help in the future.",
        "See you later! Don't hesitate to come back when you need assistance."
    ],
    "thanks": [
        "You're welcome! Is there anything else I can help you with?",
        "Happy to help! Let me know if you need anything else.",
        "My pleasure! Feel free to ask if you need further assistance."
    ]
}

def is_simple_prompt(prompt: str) -> bool:
    """
    Determine if a prompt is simple enough to handle directly.

    Args:
        prompt: The user's prompt

    Returns:
        bool: True if the prompt is simple, False otherwise
    """
    # Normalize the prompt
    normalized_prompt = prompt.strip().lower()

    # Check against all pattern categories
    for category, patterns in ALL_PATTERNS.items():
        for pattern in patterns:
            if pattern.match(normalized_prompt):
                return True

    return False

def get_prompt_category(prompt: str) -> Optional[str]:
    """
    Identify the category of a simple prompt.

    Args:
        prompt: The user's prompt

    Returns:
        Optional[str]: The category of the prompt, or None if not a simple prompt
    """
    normalized_prompt = prompt.strip().lower()

    for category, patterns in ALL_PATTERNS.items():
        for pattern in patterns:
            if pattern.match(normalized_prompt):
                return category

    return None

def get_specific_question_type(prompt: str) -> Optional[str]:
    """
    Identify the specific question type for question category prompts.

    Args:
        prompt: The user's prompt

    Returns:
        Optional[str]: The specific question type, or None if not identifiable
    """
    normalized_prompt = prompt.strip().lower()

    # Map of patterns to question types
    question_types = {
        "how are you": ["how are you", "how're you"],
        "what's up": ["what's up", "whats up", "what up"],
        "how's it going": ["how's it going", "hows it going", "how is it going"],
        "what can you do": ["what can you do", "what do you do", "what are your capabilities"],
        "who are you": ["who are you", "who're you"],
        "what are you": ["what are you"],
        "which model": ["which model", "what model", "which llm", "what llm", "which ai", "what ai"],
        "math calculation": ["what is", "calculate", "compute", "solve", "+", "-", "*", "/"],
        "who is elon": ["who is elon", "who's elon", "who is elon musk", "who's elon musk"]
    }

    for question_type, patterns in question_types.items():
        if any(pattern in normalized_prompt for pattern in patterns):
            return question_type

    return None

def get_direct_response(prompt: str) -> str:
    """
    Generate a direct response for a simple prompt.

    Args:
        prompt: The user's prompt

    Returns:
        str: The direct response
    """
    import random
    import re

    category = get_prompt_category(prompt)
    if not category:
        return None

    if category == "question":
        question_type = get_specific_question_type(prompt)

        # Special handling for math calculations
        if question_type == "math calculation":
            # Try to extract the math expression
            math_match = re.search(r'what\s+is\s+(\d+\s*[+\-*/]\s*\d+)', prompt.lower())
            if math_match:
                expression = math_match.group(1).replace(' ', '')
                try:
                    result = eval(expression)
                    return f"The result of {expression} is {result}."
                except Exception as e:
                    pass

            # Try to handle direct math expressions like "5+5"
            direct_math_match = re.search(r'^(\d+\s*[+\-*/]\s*\d+)$', prompt.lower())
            if direct_math_match:
                expression = direct_math_match.group(1).replace(' ', '')
                try:
                    result = eval(expression)
                    return f"The result of {expression} is {result}."
                except Exception as e:
                    pass

        if question_type and question_type in RESPONSES["question"]:
            return random.choice(RESPONSES["question"][question_type])
        # Fallback for questions
        return random.choice([
            "I'm here to help! What would you like to know?",
            "I'd be happy to assist you. What can I help with?"
        ])
    else:
        return random.choice(RESPONSES[category])
