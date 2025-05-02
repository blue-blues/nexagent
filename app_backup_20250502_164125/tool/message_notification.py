"""
Message Notification Tools

This module provides tools for sending notifications to users and requesting input
from users in a structured way.
"""

from typing import Dict, List, Optional, Union
from datetime import datetime

from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class MessageNotifyUser(BaseTool):
    """
    A tool for delivering non-blocking communication to the user without requiring a response.

    This tool is optimal for acknowledging message receipt, providing detailed progress updates,
    reporting task completion status, explaining methodological changes, or delivering
    informational content that doesn't necessitate immediate user feedback.
    """

    name: str = "message_notify_user"
    description: str = """
    Deliver non-blocking communication to the user without requiring a response.
    Optimal for acknowledging message receipt, providing detailed progress updates,
    reporting task completion status, explaining methodological changes, or delivering
    informational content that doesn't necessitate immediate user feedback.
    """

    parameters: Dict = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Formatted message content to display to the user. Supports markdown formatting for enhanced readability and structure."
            },
            "attachments": {
                "anyOf": [
                    {"type": "string"},
                    {"items": {"type": "string"}, "type": "array"}
                ],
                "description": "(Optional) Collection of attachments to accompany the message, specified as either file paths to local resources or fully-qualified URLs to external resources. Multiple attachments can be provided as an array."
            }
        },
        "required": ["text"]
    }

    async def execute(self, text: str, attachments: Optional[Union[str, List[str]]] = None) -> ToolResult:
        """
        Execute the message notification tool.

        Args:
            text: The message text to display to the user
            attachments: Optional attachments to include with the message

        Returns:
            ToolResult with the notification status
        """
        try:
            # Log the notification
            logger.info(f"🔔 User notification: {text[:100]}{'...' if len(text) > 100 else ''}")

            # Process attachments if provided
            attachment_info = ""
            if attachments:
                if isinstance(attachments, str):
                    attachments = [attachments]
                attachment_info = f" with {len(attachments)} attachment(s)"
                logger.info(f"📎 Notification includes{attachment_info}")

            # In a real implementation, this would send the notification to the user interface
            # For now, we'll just return a success message
            return ToolResult(
                output=f"Notification sent successfully{attachment_info}",
                system=f"Notification sent at {datetime.now().isoformat()}"
            )
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return ToolResult(
                error=f"Failed to send notification: {str(e)}"
            )


class MessageAskUser(BaseTool):
    """
    A tool for initiating a blocking interaction that requires explicit user response before proceeding.

    This tool is essential for requesting critical clarifications, obtaining authorizations for
    sensitive operations, gathering additional contextual information, confirming understanding
    of requirements, or soliciting user preferences that will significantly impact subsequent
    task execution.
    """

    name: str = "message_ask_user"
    description: str = """
    Initiate a blocking interaction that requires explicit user response before proceeding.
    Essential for requesting critical clarifications, obtaining authorizations for sensitive operations,
    gathering additional contextual information, confirming understanding of requirements, or
    soliciting user preferences that will significantly impact subsequent task execution.
    """

    parameters: Dict = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Precisely formulated question or request presented to the user. Should be clear, specific, and actionable to facilitate an appropriate response. Supports markdown formatting for enhanced clarity."
            },
            "attachments": {
                "anyOf": [
                    {"type": "string"},
                    {"items": {"type": "string"}, "type": "array"}
                ],
                "description": "(Optional) Supplementary files or reference materials that provide context for the question, specified as either file paths or URLs. These may include screenshots, logs, configuration files, or other relevant documentation."
            },
            "suggest_user_takeover": {
                "type": "string",
                "enum": ["none", "browser"],
                "description": "(Optional) Recommendation for user to temporarily assume direct control of a specific system component. Use 'browser' when suggesting the user handle sensitive operations such as authentication, payment processing, or actions with significant side effects."
            }
        },
        "required": ["text"]
    }

    async def execute(
        self,
        text: str,
        attachments: Optional[Union[str, List[str]]] = None,
        suggest_user_takeover: str = "none"
    ) -> ToolResult:
        """
        Execute the message ask user tool.

        Args:
            text: The question or request to present to the user
            attachments: Optional attachments to include with the message
            suggest_user_takeover: Optional recommendation for user to take control

        Returns:
            ToolResult with the user's response
        """
        try:
            # Log the question
            logger.info(f"❓ User question: {text[:100]}{'...' if len(text) > 100 else ''}")

            # Process attachments if provided
            attachment_info = ""
            if attachments:
                if isinstance(attachments, str):
                    attachments = [attachments]
                attachment_info = f" with {len(attachments)} attachment(s)"
                logger.info(f"📎 Question includes{attachment_info}")

            # Process user takeover suggestion if provided
            takeover_info = ""
            if suggest_user_takeover and suggest_user_takeover != "none":
                takeover_info = f" (suggesting {suggest_user_takeover} takeover)"
                logger.info(f"👤 Suggesting user takeover: {suggest_user_takeover}")

            # Display a visually distinct prompt directly in the terminal
            print("\n" + "="*80)
            print("\033[1;31m>>> USER INPUT REQUIRED <<<\033[0m")
            print("="*80)
            print(f"\033[1m🤖 Agent is requesting input:\033[0m\n")
            print(f"{text}\n")

            # Add attachment information if present
            if attachments:
                print(f"\033[1mAttachments:\033[0m {', '.join(attachments)}")

            # Add takeover suggestion if present
            if suggest_user_takeover and suggest_user_takeover != "none":
                print(f"\n\033[1;33m(Suggestion: Consider taking control of {suggest_user_takeover})\033[0m")

            print("\n" + "-"*80)

            # Get user input directly
            print("\033[1;32mYour response (type your answer below):\033[0m")
            print("\033[1;32mFor a single line response, just type and press Enter.\033[0m")
            print("\033[1;32mFor multiple lines, type your response and end with a line containing just 'END'\033[0m")

            # Get the first line
            response_lines = []
            first_line = input()

            # Check if this is going to be a multi-line response
            if first_line.strip() != "END":
                response_lines.append(first_line)

                # Inform the user they can continue typing
                print("\033[1;36mContinue typing (enter 'END' on a new line when finished):\033[0m")

                # Get additional lines until END is entered
                while True:
                    line = input()
                    if line.strip() == "END":
                        break
                    response_lines.append(line)

            # Combine all lines into a single response
            response = "\n".join(response_lines)

            print("-"*80)
            print("\033[1;34mResponse received. Processing...\033[0m\n")

            logger.info(f"Received direct user response")

            return ToolResult(
                output=response,
                system=f"Response received at {datetime.now().isoformat()}{attachment_info}{takeover_info}"
            )
        except Exception as e:
            logger.error(f"Error asking user: {str(e)}")
            return ToolResult(
                error=f"Failed to ask user: {str(e)}"
            )
