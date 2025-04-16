# Nexagent Tool Module

This module contains all the tools used by the Nexagent system. Tools are organized into categories based on their functionality.

## Tool Categories

### Command Execution Tools
- `terminal.py` - Basic terminal command execution
- `bash.py` - Bash command execution
- `enhanced_terminal.py` - Enhanced terminal with additional features
- `long_running_command.py` - For commands that take a long time to complete
- `python_execute.py` - For executing Python code

### Browser and Web Tools
- `browser_use_tool.py` - Basic browser functionality
- `enhanced_browser_tool.py` - Enhanced browser with additional features
- `fallback_browser_tool.py` - Fallback browser when primary browser fails
- `web_ui_browser_tool.py` - Browser for web UI interactions
- `web_search.py` - Web search functionality

### File and Data Tools
- `file_saver.py` - Save content to files
- `str_replace_editor.py` - String replacement in files
- `data_processor.py` - Process data from various sources
- `financial_data_extractor.py` - Extract financial data

### Analysis Tools
- `code_analyzer.py` - Analyze code
- `task_analytics.py` - Analyze task history and generate insights

### Management Tools
- `conversation_manager.py` - Manage conversations
- `mcp_server.py` - Master Control Program server for data management
- `planning.py` - Planning functionality
- `terminate.py` - Terminate functionality
- `persistent_terminate.py` - Persistent terminate functionality

### Utility Tools
- `create_chat_completion.py` - Create chat completions
- `error_handler.py` - Handle errors
- `error_handler_integration.py` - Integration for error handling
- `tool_collection.py` - Collection of tools

## Base Classes
- `base.py` - Base classes for all tools

## Search Engines
- `search/` - Directory containing search engine implementations