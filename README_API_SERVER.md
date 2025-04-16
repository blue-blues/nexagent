# Nexagent API Server

This document provides instructions for running and using the Nexagent API server, which serves as the backend for the Nexagent frontend application.

## Overview

The Nexagent API server provides a RESTful API for interacting with the Nexagent AI Assistant. It handles:

- Processing user messages and generating responses
- Managing conversations
- Providing real-time timeline updates via WebSockets
- Organizing conversations and associated materials (with the organization version)

## Running the Server

### Basic API Server

To run the basic Nexagent API server:

```bash
python run_api_server.py
```

By default, the server runs on `http://127.0.0.1:8000`. You can specify a different host and port:

```bash
python run_api_server.py --host 0.0.0.0 --port 8080
```

### API Server with Conversation Organization

To run the Nexagent API server with conversation organization features:

```bash
python run_api_server_with_organization.py
```

You can also specify a different host and port:

```bash
python run_api_server_with_organization.py --host 0.0.0.0 --port 8080
```

## API Endpoints

### Health Check

```
GET /api/health
```

Returns a simple status check to verify the server is running.

### Process Message

```
POST /api/message
```

Process a user message and get a response from the assistant.

**Request Body:**
```json
{
  "content": "Your message here",
  "conversation_id": "optional-conversation-id",
  "system_prompt": "optional-system-prompt",
  "parameters": {}
}
```

### Get Conversations

```
GET /api/conversations
```

Get a list of all conversations.

### Get Conversation

```
GET /api/conversations/{conversation_id}
```

Get details of a specific conversation.

### Get Conversation Timeline

```
GET /api/conversations/{conversation_id}/timeline
```

Get the timeline data for a specific conversation.

### WebSocket Connection for Timeline Updates

```
WebSocket: /api/ws/timeline/{conversation_id}
```

Connect to this WebSocket endpoint to receive real-time timeline updates for a specific conversation.

## Additional Endpoints (Organization Version Only)

### Save Material

```
POST /api/materials
```

Save a material to a conversation folder.

### Generate Output

```
POST /api/generate-output
```

Generate a final output document for a conversation.

## Connecting the Frontend

The frontend should be configured to connect to the API server at the appropriate URL. By default, this is `http://localhost:8000`.

In the frontend configuration, ensure that:

1. The API base URL is set correctly
2. WebSocket connections are properly configured
3. CORS is properly handled (the server allows all origins by default)

## Troubleshooting

### Server Won't Start

- Check if another process is using the same port
- Verify that all required dependencies are installed
- Check the logs for specific error messages

### Connection Issues

- Verify that the server is running
- Check that the frontend is using the correct URL
- Ensure that there are no network restrictions blocking the connection

### WebSocket Connection Failures

- Verify that the WebSocket URL is correct
- Check for any proxy or firewall issues
- Ensure the conversation ID in the WebSocket URL is valid
