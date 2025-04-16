# Conversation Memory in Nexagent

This document describes the conversation memory feature in Nexagent, which enables short-term memory between conversations.

## Overview

The conversation memory feature allows Nexagent to remember previous conversations and use them as context when responding to new prompts. This enables more natural and contextually relevant responses, as the agent can refer to information shared in previous interactions.

## How It Works

1. **Storing Conversations**: When a user interacts with Nexagent, their prompts and the agent's responses are stored in a conversation memory store.

2. **Retrieving Context**: When a new prompt is received, Nexagent retrieves relevant context from previous conversations and includes it in the system prompt.

3. **Contextual Responses**: The agent uses this context to generate more relevant and personalized responses that take into account the conversation history.

## Implementation Details

### ConversationMemory Class

The `ConversationMemory` class is responsible for storing and retrieving conversation history. It provides the following functionality:

- **Adding Entries**: Stores user prompts and agent responses with associated metadata.
- **Retrieving History**: Retrieves conversation history for a specific conversation ID.
- **Formatting History**: Formats conversation history for inclusion in prompts.
- **Managing Storage**: Automatically prunes old entries and conversations to prevent excessive memory usage.

### Integration with IntegratedFlow

The `IntegratedFlow` class has been modified to:

1. Store conversations in the memory store after processing.
2. Retrieve relevant context from the memory store before processing new prompts.
3. Pass conversation history to the agent as part of the system prompt.

### Integration with IntegratedAgent

The `IntegratedAgent` class has been modified to:

1. Accept a conversation ID parameter in the `run` method.
2. Retrieve conversation history for the specified conversation ID.
3. Include the conversation history in the system prompt for the selected agent.

## Usage

### Viewing Conversation History

A command-line tool is provided to view conversation history:

```bash
# List all conversations
python tools/view_conversation_history.py list

# View a specific conversation
python tools/view_conversation_history.py view <conversation_id>

# Clear a specific conversation
python tools/view_conversation_history.py clear <conversation_id>

# Clear all conversations
python tools/view_conversation_history.py clear-all
```

### Conversation IDs

Conversation IDs are automatically generated when a new conversation is started. They follow the format:

```
conv_<random_hex>_<timestamp>
```

For example: `conv_5ccfac18_1744132550`

## Configuration

The conversation memory feature can be configured by modifying the `ConversationMemory` class:

- `max_entries_per_conversation`: Maximum number of entries to store per conversation (default: 20)
- `max_conversations`: Maximum number of conversations to store (default: 10)
- `storage_path`: Path to store conversation memory (default: `~/.nexagent/conversation_memory`)

## Limitations

- The conversation memory is stored in-memory and persisted to disk as JSON files. For production use, a more robust storage solution may be needed.
- The current implementation does not perform semantic search or advanced retrieval of relevant context. It simply retrieves the most recent conversations.
- The conversation memory is not encrypted. Sensitive information should not be stored in the conversation memory.

## Future Improvements

- **Semantic Search**: Implement semantic search to retrieve the most relevant context based on the current prompt.
- **Long-Term Memory**: Implement long-term memory storage for persistent knowledge across sessions.
- **Memory Consolidation**: Implement more sophisticated memory consolidation strategies to summarize and compress older conversations.
- **User-Specific Memory**: Associate memory with specific users for multi-user environments.
- **Memory Visualization**: Provide a web interface for visualizing and managing conversation memory.
