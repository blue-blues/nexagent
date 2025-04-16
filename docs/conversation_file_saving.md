# Conversation-Aware File Saving in Nexagent

This document describes the conversation-aware file saving feature in Nexagent, which ensures that files are saved in the conversation-specific folder rather than in temporary directories or other locations.

## Overview

The conversation-aware file saving feature ensures that all files generated during a conversation are saved in the conversation-specific folder. This makes it easier to find and manage files related to a specific conversation.

## How It Works

1. **ConversationFileSaver**: A specialized version of the FileSaver tool that redirects file paths to the conversation-specific folder.

2. **Path Redirection**: When a file path is provided to the ConversationFileSaver, it checks if the path is already in a conversation folder. If not, it redirects the path to the outputs folder of the active conversation.

3. **Integration with Agents**: The IntegratedAgent and IntegratedFlow classes have been updated to use the ConversationFileSaver instead of the regular FileSaver.

## Implementation Details

### ConversationFileSaver Class

The `ConversationFileSaver` class extends the `FileSaver` class to provide conversation-aware file saving:

- **Active Conversation ID**: The ConversationFileSaver maintains an active conversation ID that is used to determine where files should be saved.

- **Path Redirection**: When a file path is provided, the ConversationFileSaver redirects it to the outputs folder of the active conversation.

- **Tool Replacement**: The ConversationFileSaver replaces the regular FileSaver in the agent's tool collection.

### Integration with IntegratedFlow

The `IntegratedFlow` class has been updated to:

1. Initialize a ConversationFileSaver instance with the active conversation ID.
2. Update the ConversationFileSaver's active conversation ID when the conversation ID changes.

### Integration with IntegratedAgent

The `IntegratedAgent` class has been updated to:

1. Initialize a ConversationFileSaver instance when needed.
2. Update the selected agent's tool collection to use the ConversationFileSaver.

### File Path Helper Utilities

The `file_path_helper` module provides utility functions for working with file paths:

- **get_conversation_folder**: Get the folder path for a conversation.
- **get_outputs_folder**: Get the outputs folder path for a conversation.
- **redirect_to_conversation_folder**: Redirect a file path to the conversation folder.
- **is_temp_path**: Check if a file path is in a temporary directory.

## Folder Structure

Each conversation has its own folder with the following structure:

```
data_store/
  conversations/
    <conversation_id>/
      metadata.json
      outputs/
        <file1>
        <file2>
        ...
```

- **metadata.json**: Contains metadata about the conversation.
- **outputs/**: Contains files generated during the conversation.

## Usage

The conversation-aware file saving feature works automatically. When you use the `file_saver` tool, files will be saved in the conversation-specific folder without any additional configuration.

## Benefits

- **Organization**: Files are organized by conversation, making it easier to find and manage related files.
- **Persistence**: Files are saved in a persistent location rather than in temporary directories that might be cleaned up.
- **Context**: Files are saved with the conversation context, providing more context for understanding the files.

## Limitations

- The conversation-aware file saving feature only works with the `file_saver` tool. Other tools that save files might still save them in their default locations.
- The feature relies on the active conversation ID being set correctly. If the conversation ID is not set or is incorrect, files might be saved in the wrong location.
- If the ConversationFileSaver fails to initialize or encounters an error, it will fall back to using the original file path.

## Future Improvements

- **File Browser**: Add a file browser to the web UI to make it easier to browse and manage files.
- **File Preview**: Add file preview functionality to the web UI to make it easier to view files without downloading them.
- **File Sharing**: Add file sharing functionality to make it easier to share files with others.
- **File Versioning**: Add file versioning to track changes to files over time.
