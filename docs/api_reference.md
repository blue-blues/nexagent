# Nexagent API Reference

## Overview

This document provides a comprehensive reference for the Nexagent API, allowing developers to integrate Nexagent's capabilities into their own applications.

## API Server

Nexagent provides a FastAPI-based server that exposes its functionality through HTTP endpoints.

### Starting the API Server

```bash
python run_api_server.py
```

For conversation organization features:

```bash
python run_api_server_with_organization.py
```

## Endpoints

### Conversation API

#### Create a New Conversation

- **Endpoint**: `/api/conversation`
- **Method**: POST
- **Description**: Creates a new conversation session
- **Response**: JSON object containing the conversation ID

```json
{
  "conversation_id": "unique-conversation-id"
}
```

#### Send a Message

- **Endpoint**: `/api/conversation/{conversation_id}/message`
- **Method**: POST
- **Description**: Sends a message to the agent in the specified conversation
- **Request Body**:

```json
{
  "message": "Your message to the agent"
}
```

- **Response**: JSON object containing the agent's response

```json
{
  "response": "Agent's response to your message"
}
```

### WebSocket API

#### Real-time Conversation

- **Endpoint**: `/ws/{conversation_id}`
- **Description**: Establishes a WebSocket connection for real-time interaction with the agent

##### Message Format

Messages sent to the WebSocket should be JSON objects with the following structure:

```json
{
  "type": "message",
  "content": "Your message to the agent"
}
```

Responses from the WebSocket will have the following structure:

```json
{
  "type": "response",
  "content": "Agent's response to your message"
}
```

##### Thinking Updates

The WebSocket may also send thinking updates with the following structure:

```json
{
  "type": "thinking",
  "content": "Current thinking process of the agent"
}
```

## Client Libraries

### Python Client

```python
import requests

class NexagentClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.conversation_id = None
    
    def create_conversation(self):
        response = requests.post(f"{self.base_url}/api/conversation")
        data = response.json()
        self.conversation_id = data["conversation_id"]
        return self.conversation_id
    
    def send_message(self, message):
        if not self.conversation_id:
            self.create_conversation()
        
        response = requests.post(
            f"{self.base_url}/api/conversation/{self.conversation_id}/message",
            json={"message": message}
        )
        return response.json()["response"]

# Example usage
client = NexagentClient()
client.create_conversation()
response = client.send_message("Generate a Python function to calculate Fibonacci numbers")
print(response)
```

## Error Handling

API errors are returned with appropriate HTTP status codes and a JSON response body with the following structure:

```json
{
  "error": "Error message",
  "details": "Additional error details (if available)"
}
```

Common error codes:

- **400**: Bad Request - The request was malformed
- **404**: Not Found - The requested resource was not found
- **500**: Internal Server Error - An unexpected error occurred on the server

## Rate Limiting

The API implements rate limiting to prevent abuse. Clients should respect the following headers in API responses:

- `X-RateLimit-Limit`: The maximum number of requests allowed in a time window
- `X-RateLimit-Remaining`: The number of requests remaining in the current time window
- `X-RateLimit-Reset`: The time at which the current rate limit window resets (Unix timestamp)

When rate limits are exceeded, the API will return a 429 Too Many Requests response.