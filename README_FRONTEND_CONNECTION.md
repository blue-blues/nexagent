# Connecting Frontend to Backend

This document provides instructions for resolving connection issues between the Nexagent frontend and backend.

## Overview

The Nexagent frontend is designed to connect to the backend API server running on `http://localhost:8000`. If the backend server is not available, the frontend will switch to "mock mode" and display simulated data.

## Common Connection Issues

1. **"Backend server is not available" message**: This indicates that the frontend cannot connect to the backend server.
2. **WebSocket connection failures**: The frontend may fail to establish WebSocket connections for real-time updates.
3. **Mock data being displayed**: The frontend is using mock data instead of real data from the backend.

## How to Fix Connection Issues

### 1. Start the Backend Server

Make sure the backend server is running:

```bash
# Start the basic API server
python run_api_server.py

# Or start the server with conversation organization features
python run_api_server_with_organization.py
```

### 2. Verify the Backend Server is Running

Check if the backend server is running by accessing the health check endpoint:

```bash
curl http://localhost:8000/api/health
```

You should see a response like:

```json
{
  "status": "ok",
  "server": "Nexagent API",
  "version": "1.0.0",
  "timestamp": 1234567890123,
  "connections": 0,
  "conversations": 0
}
```

### 3. Test WebSocket Connections

Use the provided test script to verify WebSocket connections are working:

```bash
python test_websocket.py
```

### 4. Check for Firewall or Network Issues

Make sure there are no firewall rules or network configurations blocking connections to the backend server.

### 5. Clear Browser Cache and Reload

Sometimes browser caching can cause issues. Try clearing your browser cache and reloading the page:

1. Press `Ctrl+Shift+Delete` (Windows/Linux) or `Cmd+Shift+Delete` (Mac)
2. Select "Cached images and files"
3. Click "Clear data"
4. Reload the page

### 6. Check for CORS Issues

If you're seeing CORS-related errors in the browser console, make sure the backend server is properly configured to allow cross-origin requests. The server should include the following headers in its responses:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

### 7. Restart Both Frontend and Backend

Sometimes a full restart of both the frontend and backend can resolve connection issues:

1. Stop the backend server (press `Ctrl+C` in the terminal where it's running)
2. Stop the frontend development server (press `Ctrl+C` in the terminal where it's running)
3. Start the backend server again
4. Start the frontend development server again

## Troubleshooting

### Backend Server Logs

Check the backend server logs for any error messages or warnings:

```bash
# Look for error messages in the terminal where the backend server is running
```

### Frontend Console Logs

Check the browser console for any error messages or warnings:

1. Open your browser's developer tools (press `F12` or right-click and select "Inspect")
2. Go to the "Console" tab
3. Look for any error messages related to API requests or WebSocket connections

### WebSocket Connection Issues

If you're having issues with WebSocket connections, try the following:

1. Make sure the backend server is running
2. Check if the WebSocket endpoint is accessible
3. Verify that there are no proxy or firewall issues blocking WebSocket connections
4. Test the WebSocket connection using the provided test script

```bash
python test_websocket.py --conversation-id=test-conversation
```

## Still Having Issues?

If you're still experiencing connection issues after trying the above steps, please:

1. Check the project documentation for any specific configuration requirements
2. Look for any recent changes to the codebase that might affect connectivity
3. Verify that all required dependencies are installed
4. Check for any environment-specific issues (e.g., different behavior on different operating systems)
