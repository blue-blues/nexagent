# NexAgent CLI

## Overview
This is the CLI version of NexAgent with the web implementation removed. The core functionality remains intact, but it now operates exclusively through a command-line interface.

## Changes Made
- Removed FastAPI web server implementation
- Removed WebSocket handlers and related web endpoints
- Removed all frontend React components and web-related files
- Created a dedicated CLI implementation in `app/cli.py`
- Created a new entry point `main_cli.py` for running the CLI version

## How to Use
To run NexAgent in CLI mode, use the following command:

```bash
python main_cli.py
```

### Available Commands
- Type your query and press Enter to interact with the AI
- Type `exit` to quit the application
- Type `stats` to see performance statistics and routing information
- Type `feedback` to provide feedback on the last response
- Type `save` to save the learning system state
- Type `mode [chat|agent|auto]` to set the processing mode:
  - `mode chat`: Use chat mode for direct LLM responses
  - `mode agent`: Use agent mode for tool-assisted responses
  - `mode auto`: Automatically detect the appropriate mode (default)

## Core Functionality
The CLI version preserves all the core functionality of NexAgent:
- Automatic routing between general-purpose and software development AI assistants
- Session management for maintaining context
- All tools and capabilities of the original system

## Implementation Details
The CLI implementation is contained in `app/cli.py` and provides:
- A simplified interface for interacting with the IntegratedFlow
- Session management similar to the web version
- Statistics tracking and display
- Error handling and timeout management