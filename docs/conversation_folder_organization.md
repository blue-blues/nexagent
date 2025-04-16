# Conversation Folder Organization

This document describes the conversation folder organization feature in Nexagent, which ensures that for every conversation, a new folder is created to store related documents and generated outputs.

## Overview

The conversation folder organization feature provides a structured way to organize and store outputs generated during conversations with Nexagent. This makes it easier to track, reference, and manage the outputs of each conversation.

## Key Features

- **Automatic Folder Creation**: A new folder is created for each conversation
- **Organized Output Storage**: All outputs are stored in a dedicated folder for each conversation
- **Metadata Tracking**: Metadata about each output is stored for easy reference
- **Support for Different Output Types**: Support for various output types (code, documents, messages, etc.)
- **Easy Retrieval**: Simple API for retrieving outputs from a conversation

## Folder Structure

The folder structure for conversation outputs is as follows:

```
data_store/
└── conversations/
    └── {conversation_id}/
        ├── metadata.json
        └── outputs/
            ├── output1.txt
            ├── output2.py
            └── ...
```

- `data_store/conversations/`: The base directory for all conversation folders
- `{conversation_id}/`: A unique folder for each conversation
- `metadata.json`: Contains metadata about the conversation and its outputs
- `outputs/`: Contains all the outputs generated during the conversation

## Usage

### OutputOrganizer Tool

The `OutputOrganizer` tool is used to manage conversation outputs. It provides the following actions:

#### Set Active Conversation

```python
await output_organizer.execute(
    action="set_active_conversation",
    conversation_id="conversation_123"
)
```

#### Save Output

```python
await output_organizer.execute(
    action="save_output",
    output_name="hello_world_example",
    output_content="print('Hello, World!')",
    output_type="code"
)
```

#### List Outputs

```python
result = await output_organizer.execute(
    action="list_outputs"
)
```

### Integration with IntegratedFlow

The `IntegratedFlow` class has been updated to use the `OutputOrganizer` tool to save outputs during conversations. It automatically creates a new folder for each conversation and saves all outputs to that folder.

```python
# Initialize the flow with a conversation ID
flow = IntegratedFlow(conversation_id="conversation_123")

# Execute the flow
result = await flow.execute("Tell me about Python")
```

## Implementation Details

### OutputOrganizer Tool

The `OutputOrganizer` tool is implemented in `app/tool/output_organizer.py`. It provides a simple API for managing conversation outputs.

### IntegratedFlow Integration

The `IntegratedFlow` class has been updated to use the `OutputOrganizer` tool to save outputs during conversations. It automatically creates a new folder for each conversation and saves all outputs to that folder.

## Examples

See the following example scripts for demonstrations of the conversation folder organization feature:

- `examples/output_organizer_test.py`: A simple test of the `OutputOrganizer` tool
- `examples/simple_conversation_folder_demo.py`: A demonstration of the conversation folder organization feature

## Future Enhancements

- **Output Categorization**: Add support for categorizing outputs (e.g., code, documentation, diagrams)
- **Output Versioning**: Add support for versioning outputs
- **Output Search**: Add support for searching outputs
- **Output Sharing**: Add support for sharing outputs between conversations
- **UI Integration**: Add a UI for browsing and managing conversation outputs
