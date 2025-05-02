"""
Universal response formatter for Nexagent.

This module provides functions to ensure all responses are well-structured
and comprehensive, regardless of the prompt type.
"""

from typing import Optional, Dict, Any, List
import re


def format_response(response: str, agent_thoughts: Optional[str] = None,
                   extracted_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Format a response to ensure it's well-structured and comprehensive.

    Args:
        response: The raw response to format
        agent_thoughts: Optional agent thoughts to include in the response
        extracted_data: Optional extracted data to include in the response

    Returns:
        A well-structured and comprehensive response
    """
    # Handle None or empty responses
    if not response:
        if agent_thoughts:
            cleaned_thoughts = _clean_agent_thoughts(agent_thoughts)
            return cleaned_thoughts
        elif extracted_data:
            return _format_extracted_data(extracted_data)
        else:
            return "I'm not sure how to respond to that. How can I help you today?"

    # If the response is already well-structured, return it as is
    if _is_well_structured(response):
        return response

    # If we have agent thoughts, use them as the main content
    if agent_thoughts:
        # Clean up the agent thoughts
        cleaned_thoughts = _clean_agent_thoughts(agent_thoughts)

        # Format the thoughts into a proper response
        return cleaned_thoughts

    # If we have extracted data, format it into a proper response
    if extracted_data:
        return _format_extracted_data(extracted_data)

    # If we don't have any additional data, just clean up the response
    return _clean_response(response)


def _is_well_structured(response: str) -> bool:
    """
    Check if a response is already well-structured.

    Args:
        response: The response to check

    Returns:
        True if the response is well-structured, False otherwise
    """
    # Very short responses are considered well-structured as they are
    if len(response) < 50:
        return True

    # Check if the response has multiple paragraphs
    if response.count('\n\n') >= 1:
        return True

    # Check if the response has headings
    if re.search(r'^#+\s+.+$', response, re.MULTILINE):
        return True

    # Check if the response has bullet points
    if re.search(r'^\s*[-*]\s+.+$', response, re.MULTILINE):
        return True

    # Check if the response has numbered lists
    if re.search(r'^\s*\d+\.\s+.+$', response, re.MULTILINE):
        return True

    # If none of the above, the response is not well-structured
    return False


def _clean_agent_thoughts(thoughts: str) -> str:
    """
    Clean up agent thoughts to make them suitable for display to the user.

    Args:
        thoughts: The agent thoughts to clean up

    Returns:
        Cleaned up agent thoughts
    """
    # Remove any system-specific markers
    cleaned = re.sub(r'Nexagent\'s thoughts:', '', thoughts)

    # Remove any tool call markers
    cleaned = re.sub(r'Tools being prepared: \[.*?\]', '', cleaned)

    # Split into paragraphs
    paragraphs = [p.strip() for p in cleaned.split('\n\n')]

    # Filter out empty paragraphs
    paragraphs = [p for p in paragraphs if p]

    # Join paragraphs with proper spacing
    return '\n\n'.join(paragraphs)


def _format_extracted_data(data: Dict[str, Any]) -> str:
    """
    Format extracted data into a proper response.

    Args:
        data: The extracted data to format

    Returns:
        A formatted response
    """
    # If the data is a simple string, return it
    if isinstance(data, str):
        return data

    # If the data is a list, format it as a bulleted list
    if isinstance(data, list):
        return '\n'.join([f"- {item}" for item in data])

    # If the data is a dictionary, format it as a structured response
    if isinstance(data, dict):
        result = []
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                result.append(f"**{key}**:")
                if isinstance(value, list):
                    for item in value:
                        result.append(f"- {item}")
                else:  # dict
                    for k, v in value.items():
                        result.append(f"- **{k}**: {v}")
            else:
                result.append(f"**{key}**: {value}")
        return '\n'.join(result)

    # If we don't know how to format the data, convert it to a string
    return str(data)


def _clean_response(response: str) -> str:
    """
    Clean up a response to make it more presentable.

    Args:
        response: The response to clean up

    Returns:
        A cleaned up response
    """
    # Remove any system-specific markers
    cleaned = re.sub(r'The interaction has been completed with status: \w+\n\n', '', response)

    # If the response is very short, try to make it more comprehensive
    if len(cleaned) < 100:
        # Check if it's a simple greeting or acknowledgment
        if re.match(r'^(hi|hello|thanks|thank you|ok|okay|yes|no|bye|goodbye)$', cleaned.lower()):
            return cleaned

        # Check if it's a math calculation result
        if re.match(r'^The result of \d+[+\-*/]\d+ is [-\d\.]+\.$', cleaned):
            return cleaned

        # If it's not a simple greeting or math result, add some structure
        if not cleaned.endswith('.') and not cleaned.endswith('?') and not cleaned.endswith('!'):
            cleaned += '.'

        # Add a polite closing if the response is still short and doesn't already have a question
        if len(cleaned) < 50 and not cleaned.endswith('?') and not "?" in cleaned:
            cleaned += "\n\nIs there anything else you'd like to know?"

    return cleaned


def extract_agent_thoughts(messages: List[Dict[str, Any]]) -> Optional[str]:
    """
    Extract agent thoughts from a list of messages.

    Args:
        messages: The list of messages to extract thoughts from

    Returns:
        The extracted thoughts, or None if no thoughts were found
    """
    # Look for the most recent assistant message with thoughts
    for msg in reversed(messages):
        if msg.get('role') == 'assistant' and msg.get('content'):
            content = msg.get('content', '')
            if "Nexagent's thoughts:" in content:
                # Extract the thoughts
                thoughts_parts = content.split("Nexagent's thoughts:", 1)
                if len(thoughts_parts) > 1:
                    return thoughts_parts[1].strip()

    # If no thoughts were found, return None
    return None
