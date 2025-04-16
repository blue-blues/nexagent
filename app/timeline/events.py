"""
Timeline event utilities and helper functions.

This module provides utility functions for creating and managing
timeline events for different agent actions.
"""

from typing import Dict, Any, Optional, List, Union

from app.timeline.timeline import Timeline, TimelineEvent, TimelineEventType


def create_thinking_event(timeline: Timeline, thought: str) -> TimelineEvent:
    """
    Create a thinking event in the timeline.
    
    Args:
        timeline: The timeline to add the event to
        thought: The agent's thought content
        
    Returns:
        The created timeline event
    """
    return timeline.add_event(
        event_type=TimelineEventType.THINKING,
        title="Agent Thinking",
        description=thought[:100] + "..." if len(thought) > 100 else thought,
        data={"thought": thought}
    )


def create_tool_call_event(
    timeline: Timeline, 
    tool_name: str, 
    tool_args: Dict[str, Any]
) -> TimelineEvent:
    """
    Create a tool call event in the timeline.
    
    Args:
        timeline: The timeline to add the event to
        tool_name: The name of the tool being called
        tool_args: The arguments passed to the tool
        
    Returns:
        The created timeline event
    """
    # Create a readable description of the tool call
    arg_str = ", ".join(f"{k}={v}" for k, v in tool_args.items())
    description = f"{tool_name}({arg_str})"
    
    return timeline.add_event(
        event_type=TimelineEventType.TOOL_CALL,
        title=f"Tool Call: {tool_name}",
        description=description[:100] + "..." if len(description) > 100 else description,
        data={
            "tool_name": tool_name,
            "tool_args": tool_args
        }
    )


def create_tool_result_event(
    timeline: Timeline,
    tool_name: str,
    result: Any,
    event: Optional[TimelineEvent] = None
) -> TimelineEvent:
    """
    Create a tool result event in the timeline or update an existing tool call event.
    
    Args:
        timeline: The timeline to add the event to
        tool_name: The name of the tool that was called
        result: The result returned by the tool
        event: Optional existing tool call event to update
        
    Returns:
        The created or updated timeline event
    """
    if event:
        # Update the existing event with the result
        return event.mark_success(result)
    
    # Create a new event for the tool result
    result_str = str(result)
    return timeline.add_event(
        event_type=TimelineEventType.TOOL_RESULT,
        title=f"Tool Result: {tool_name}",
        description=result_str[:100] + "..." if len(result_str) > 100 else result_str,
        data={
            "tool_name": tool_name,
            "result": result
        }
    )


def create_error_event(
    timeline: Timeline,
    error: Union[str, Exception],
    context: str,
    event: Optional[TimelineEvent] = None
) -> TimelineEvent:
    """
    Create an error event in the timeline or update an existing event with an error.
    
    Args:
        timeline: The timeline to add the event to
        error: The error that occurred
        context: Context information about where the error occurred
        event: Optional existing event to update with the error
        
    Returns:
        The created or updated timeline event
    """
    if event:
        # Update the existing event with the error
        return event.mark_error(error)
    
    # Create a new event for the error
    error_str = str(error)
    error_type = type(error).__name__ if isinstance(error, Exception) else "Error"
    
    return timeline.add_event(
        event_type=TimelineEventType.ERROR,
        title=f"Error: {error_type}",
        description=error_str[:100] + "..." if len(error_str) > 100 else error_str,
        data={
            "error": error_str,
            "error_type": error_type,
            "context": context
        }
    )


def create_plan_event(
    timeline: Timeline,
    plan: Union[str, List[str]],
    plan_type: str = "execution"
) -> TimelineEvent:
    """
    Create a plan event in the timeline.
    
    Args:
        timeline: The timeline to add the event to
        plan: The plan content, either as a string or list of steps
        plan_type: The type of plan (e.g., "execution", "recovery")
        
    Returns:
        The created timeline event
    """
    if isinstance(plan, list):
        plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
    else:
        plan_str = plan
    
    return timeline.add_event(
        event_type=TimelineEventType.PLAN,
        title=f"{plan_type.capitalize()} Plan",
        description=f"{plan_type.capitalize()} plan with {len(plan) if isinstance(plan, list) else 'multiple'} steps",
        data={
            "plan": plan,
            "plan_type": plan_type
        }
    )


def create_web_browse_event(
    timeline: Timeline,
    url: str,
    action: str = "visit"
) -> TimelineEvent:
    """
    Create a web browsing event in the timeline.
    
    Args:
        timeline: The timeline to add the event to
        url: The URL being accessed
        action: The browsing action (e.g., "visit", "extract", "click")
        
    Returns:
        The created timeline event
    """
    return timeline.add_event(
        event_type=TimelineEventType.WEB_BROWSE,
        title=f"Web {action.capitalize()}: {url}",
        description=f"{action.capitalize()} web page at {url}",
        data={
            "url": url,
            "action": action
        }
    )


def create_code_execution_event(
    timeline: Timeline,
    code: str,
    language: str = "python"
) -> TimelineEvent:
    """
    Create a code execution event in the timeline.
    
    Args:
        timeline: The timeline to add the event to
        code: The code being executed
        language: The programming language
        
    Returns:
        The created timeline event
    """
    code_preview = code.split("\n")[0]
    if len(code_preview) > 50:
        code_preview = code_preview[:50] + "..."
    
    return timeline.add_event(
        event_type=TimelineEventType.CODE_EXECUTION,
        title=f"Execute {language.capitalize()} Code",
        description=code_preview,
        data={
            "code": code,
            "language": language
        }
    )


def create_file_operation_event(
    timeline: Timeline,
    operation: str,
    path: str,
    content: Optional[str] = None
) -> TimelineEvent:
    """
    Create a file operation event in the timeline.
    
    Args:
        timeline: The timeline to add the event to
        operation: The file operation (e.g., "read", "write", "delete")
        path: The file path
        content: Optional file content for write operations
        
    Returns:
        The created timeline event
    """
    return timeline.add_event(
        event_type=TimelineEventType.FILE_OPERATION,
        title=f"File {operation.capitalize()}: {path}",
        description=f"{operation.capitalize()} file at {path}",
        data={
            "operation": operation,
            "path": path,
            "content": content[:100] + "..." if content and len(content) > 100 else content
        }
    )


def create_system_event(
    timeline: Timeline,
    title: str,
    description: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> TimelineEvent:
    """
    Create a system event in the timeline.
    
    Args:
        timeline: The timeline to add the event to
        title: The event title
        description: Optional detailed description
        data: Optional additional data
        
    Returns:
        The created timeline event
    """
    return timeline.add_event(
        event_type=TimelineEventType.SYSTEM,
        title=title,
        description=description,
        data=data or {}
    )


def create_user_input_event(
    timeline: Timeline,
    input_text: str
) -> TimelineEvent:
    """
    Create a user input event in the timeline.
    
    Args:
        timeline: The timeline to add the event to
        input_text: The user's input text
        
    Returns:
        The created timeline event
    """
    return timeline.add_event(
        event_type=TimelineEventType.USER_INPUT,
        title="User Input",
        description=input_text[:100] + "..." if len(input_text) > 100 else input_text,
        data={"input": input_text}
    ).mark_success()


def create_agent_response_event(
    timeline: Timeline,
    response: str
) -> TimelineEvent:
    """
    Create an agent response event in the timeline.
    
    Args:
        timeline: The timeline to add the event to
        response: The agent's response text
        
    Returns:
        The created timeline event
    """
    return timeline.add_event(
        event_type=TimelineEventType.AGENT_RESPONSE,
        title="Agent Response",
        description=response[:100] + "..." if len(response) > 100 else response,
        data={"response": response}
    ).mark_success()
