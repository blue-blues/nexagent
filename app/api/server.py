
import json
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import threading
from datetime import datetime
import uuid
import asyncio
import time
from app.logger import logger
from app.flow.integrated_flow import IntegratedFlow
from app.timeline.timeline import Timeline
from app.util.response_formatter import format_response, extract_agent_thoughts

# Models for API requests and responses
class MessageRequest(BaseModel):
    content: str = Field(..., description="Message content from the user")
    conversation_id: Optional[str] = Field(None, description="Conversation ID if continuing an existing conversation")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt to override default")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional parameters for the agent")
    processing_mode: Optional[str] = Field("auto", description="Processing mode: 'auto', 'chat', or 'agent'")

class MessageResponse(BaseModel):
    id: str = Field(..., description="Message ID")
    content: str = Field(..., description="Response content from the assistant")
    conversation_id: str = Field(..., description="Conversation ID")
    timestamp: int = Field(..., description="Timestamp of the response")
    timeline: Optional[Dict[str, Any]] = Field(None, description="Timeline data for the message processing")

class ConversationResponse(BaseModel):
    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    messages: List[Dict[str, Any]] = Field(..., description="List of messages in the conversation")
    created_at: int = Field(..., description="Creation timestamp")
    updated_at: int = Field(..., description="Last update timestamp")

# Server class
class NexagentServer:
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    _app = None
    _server_thread = None
    _conversations = {}
    _port = 8000
    _host = "127.0.0.1"
    _running = False
    _active_websockets = []
    _websocket_by_conversation = {}  # Dictionary to track one active WebSocket per conversation
    _health_check_rate_limit = {}
    _rate_limit_window = 10  # seconds (increased from 5)
    _rate_limit_max_requests = 10  # max requests per window (increased from 2)
    _tools = {}  # Dictionary to store registered tools
    _memory_reasoning = None  # Memory reasoning instance
    _flow_initializers = []  # List of flow initializer functions

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialize()

    def _initialize(self):
        """Initialize the Nexagent API server"""
        # Initialize FastAPI app
        self._init_app()
        self._initialized = True

    def _init_app(self):
        """Initialize the FastAPI application"""
        app = FastAPI(title="Nexagent API", description="API for Nexagent AI Assistant")

        # Add CORS middleware to allow requests from the frontend
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*", "http://localhost:3000", "http://127.0.0.1:3000"],  # In production, specify your frontend URL
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["*"],
            max_age=86400,  # 24 hours
        )

        logger.info("CORS middleware configured with allow_origins=['*', 'http://localhost:3000', 'http://127.0.0.1:3000']")

        # Define API routes
        @app.get("/")
        async def root():
            return {"message": "Nexagent API is running", "status": "active"}

        @app.get("/api/health")
        async def health_check(request: Request, response: Response):
            # Get client details without verbose logging
            client_host = request.client.host if request.client else "unknown"
            client_port = request.client.port if request.client else "unknown"
            client_id = f"{client_host}:{client_port}"

            # Apply rate limiting
            current_time = time.time()

            # Clean up old rate limit entries
            self._health_check_rate_limit = {k: v for k, v in self._health_check_rate_limit.items()
                                           if current_time - v["first_request"] < self._rate_limit_window}

            # Check if client is rate limited
            if client_id in self._health_check_rate_limit:
                rate_limit_info = self._health_check_rate_limit[client_id]

                # If within window, increment count
                if current_time - rate_limit_info["first_request"] < self._rate_limit_window:
                    rate_limit_info["count"] += 1

                    # If over limit, return 429 Too Many Requests
                    if rate_limit_info["count"] > self._rate_limit_max_requests:
                        response.status_code = 429
                        return {
                            "status": "error",
                            "message": "Too many requests",
                            "retry_after": int(self._rate_limit_window - (current_time - rate_limit_info["first_request"]))
                        }
                else:
                    # Window expired, reset
                    rate_limit_info["first_request"] = current_time
                    rate_limit_info["count"] = 1
            else:
                # First request from this client
                self._health_check_rate_limit[client_id] = {
                    "first_request": current_time,
                    "count": 1
                }

            # Prepare response
            health_response = {
                "status": "ok",
                "server": "Nexagent API",
                "version": "1.0.0",
                "timestamp": int(datetime.now().timestamp() * 1000),
                "connections": len(self._active_websockets),
                "conversations": len(self._conversations),
                "client": client_id
            }

            # No need to log every health check response
            return health_response

        @app.post("/api/message", response_model=MessageResponse)
        async def process_message(request: MessageRequest):
            # Create or get conversation
            conversation_id = request.conversation_id
            # Store the current conversation ID for use in _format_response_for_display
            self._current_conversation_id = conversation_id
            if not conversation_id or conversation_id not in self._conversations:
                conversation_id = str(uuid.uuid4())
                self._conversations[conversation_id] = {
                    "id": conversation_id,
                    "title": f"Conversation {len(self._conversations) + 1}",
                    "messages": [],
                    "created_at": int(datetime.now().timestamp() * 1000),
                    "updated_at": int(datetime.now().timestamp() * 1000),
                }

            # Add user message to conversation
            user_message = {
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": request.content,
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            self._conversations[conversation_id]["messages"].append(user_message)

            # Process the message with the agent
            try:
                # Initialize the flow with the conversation ID
                flow = IntegratedFlow(conversation_id=conversation_id)

                # Initialize the flow with registered initializers
                self.initialize_flow(flow)

                # Create a timeline for this request
                timeline = Timeline()

                # Process the request with timeline tracking
                # Pass the processing_mode parameter if provided
                processing_mode = request.processing_mode if request.processing_mode else "auto"
                result = await flow.execute(
                    input_text=request.content,
                    conversation_id=conversation_id,
                    timeline=timeline,
                    processing_mode=processing_mode
                )

                # Get the timeline data
                timeline_data = timeline.to_dict() if timeline else None

                # Create assistant message
                # Ensure the result is properly formatted for display to the user
                formatted_result = self._format_response_for_display(result)

                assistant_message = {
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": formatted_result,
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "timeline": timeline_data
                }

                # Add assistant message to conversation
                self._conversations[conversation_id]["messages"].append(assistant_message)
                self._conversations[conversation_id]["updated_at"] = assistant_message["timestamp"]

                # Broadcast timeline updates to connected websockets
                if timeline_data:
                    await self._broadcast_timeline_update(conversation_id, timeline_data)

                return {
                    "id": assistant_message["id"],
                    "content": formatted_result,  # Use the formatted result here
                    "conversation_id": conversation_id,
                    "timestamp": assistant_message["timestamp"],
                    "timeline": timeline_data
                }
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

        @app.get("/api/conversations", response_model=List[ConversationResponse])
        async def get_conversations():
            return list(self._conversations.values())

        @app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
        async def get_conversation(conversation_id: str):
            if conversation_id not in self._conversations:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return self._conversations[conversation_id]

        @app.get("/api/conversations/{conversation_id}/timeline")
        async def get_conversation_timeline(conversation_id: str):
            # Handle mock conversations or conversations that don't exist yet
            if conversation_id.startswith("mock-") or conversation_id.startswith("new-"):
                # Create the conversation if it doesn't exist
                if conversation_id not in self._conversations:
                    self._conversations[conversation_id] = {
                        "id": conversation_id,
                        "title": f"New Conversation",
                        "messages": [],
                        "created_at": int(datetime.now().timestamp() * 1000),
                        "updated_at": int(datetime.now().timestamp() * 1000),
                    }
                    logger.info(f"Created new conversation with ID {conversation_id} for timeline request")

                # Return an empty timeline for mock/new conversations
                return {"events": [], "event_count": 0}

            # For regular conversations, check if it exists
            if conversation_id not in self._conversations:
                raise HTTPException(status_code=404, detail="Conversation not found")

            # Get the most recent message with timeline data
            messages = self._conversations[conversation_id]["messages"]
            for message in reversed(messages):
                if message.get("role") == "assistant" and message.get("timeline"):
                    return message["timeline"]

            # No timeline data found
            return {"events": [], "event_count": 0}

        @app.websocket("/api/ws/timeline/{conversation_id}")
        async def timeline_websocket(websocket: WebSocket, conversation_id: str):
            # Flag to track if the WebSocket is connected
            is_connected = False

            try:
                # Check if there's already an active connection for this conversation
                if conversation_id in self._websocket_by_conversation:
                    existing_ws = self._websocket_by_conversation[conversation_id]
                    # Check if the existing connection is still active
                    try:
                        if not (hasattr(existing_ws, '_closed') and existing_ws._closed):
                            # Try to close the existing connection gracefully
                            logger.info(f"Closing existing WebSocket connection for conversation {conversation_id}")
                            await existing_ws.close(code=1000, reason="New connection established")
                    except Exception as e:
                        logger.warning(f"Error closing existing WebSocket for conversation {conversation_id}: {str(e)}")

                    # Remove the old connection from active_websockets
                    self._active_websockets = [(ws, cid) for ws, cid in self._active_websockets
                                              if ws != existing_ws]

                # Accept the new WebSocket connection
                await websocket.accept()
                is_connected = True

                # Log the connection
                logger.info(f"WebSocket connection accepted for conversation {conversation_id}")

                # Add the websocket to active connections and update the tracking dictionary
                self._active_websockets.append((websocket, conversation_id))
                self._websocket_by_conversation[conversation_id] = websocket

                # If this is a new conversation, create it
                if conversation_id.startswith("new-") and conversation_id not in self._conversations:
                    self._conversations[conversation_id] = {
                        "id": conversation_id,
                        "title": f"New Conversation",
                        "messages": [],
                        "created_at": int(datetime.now().timestamp() * 1000),
                        "updated_at": int(datetime.now().timestamp() * 1000),
                    }
                    logger.info(f"Created new conversation with ID {conversation_id}")

                # Wait a short time to ensure the connection is stable
                await asyncio.sleep(1.0)  # Increased from 0.5 to 1.0 seconds to improve stability

                # Check if the WebSocket is already closed before trying to send anything
                if hasattr(websocket, '_closed') and websocket._closed:
                    logger.debug(f"Cannot send initial ping to {conversation_id}: WebSocket already closed")
                    return  # Exit early if the WebSocket is already closed

                try:
                    # Send an initial ping to verify the connection
                    await websocket.send_json({
                        "type": "connection_established",
                        "conversation_id": conversation_id,
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    })
                    logger.debug(f"Sent connection_established message to {conversation_id}")

                    # Wait a longer time between messages
                    await asyncio.sleep(1.0)  # Increased from 0.5 to 1.0 seconds to improve stability
                except WebSocketDisconnect:
                    logger.debug(f"WebSocket disconnected during initial ping to {conversation_id}")
                    return  # Exit early if the WebSocket is disconnected
                except RuntimeError as re:
                    if "WebSocket is not connected" in str(re) or "Cannot call \"send\" once a close message has been sent" in str(re):
                        logger.debug(f"Cannot send initial ping to {conversation_id}: {str(re)}")
                        return  # Exit early if the WebSocket is not connected
                    else:
                        logger.error(f"Error sending initial ping to {conversation_id}: {str(re)}")
                        return  # Exit early instead of re-raising
                except Exception as e:
                    logger.error(f"Error sending initial ping to {conversation_id}: {str(e)}")
                    return  # Exit early instead of re-raising

                # Prepare the timeline data first before attempting to send it
                timeline_data = None
                try:
                    # If this is a new conversation, prepare an empty timeline
                    if conversation_id not in self._conversations or not any(msg.get("timeline") for msg in self._conversations[conversation_id].get("messages", [])):
                        timeline_data = {
                            "type": "timeline_update",
                            "conversation_id": conversation_id,
                            "timeline": {"events": [], "event_count": 0}
                        }
                        logger.debug(f"Prepared empty timeline for {conversation_id}")
                    # If the conversation exists with timeline data, prepare the current timeline
                    elif conversation_id in self._conversations:
                        # Get the most recent message with timeline data
                        messages = self._conversations[conversation_id]["messages"]
                        timeline_found = False

                        for message in reversed(messages):
                            if message.get("role") == "assistant" and message.get("timeline"):
                                timeline_data = {
                                    "type": "timeline_update",
                                    "conversation_id": conversation_id,
                                    "timeline": message["timeline"]
                                }
                                timeline_found = True
                                logger.debug(f"Prepared existing timeline for {conversation_id}")
                                break

                        # If no timeline was found, prepare an empty one
                        if not timeline_found:
                            timeline_data = {
                                "type": "timeline_update",
                                "conversation_id": conversation_id,
                                "timeline": {"events": [], "event_count": 0}
                            }
                            logger.debug(f"Prepared empty timeline (no existing timeline found) for {conversation_id}")
                except Exception as e:
                    import traceback
                    error_traceback = traceback.format_exc()
                    logger.error(f"Error preparing timeline data for {conversation_id}: {str(e)}\n{error_traceback}")
                    # Don't re-raise, just continue with a default empty timeline
                    timeline_data = {
                        "type": "timeline_update",
                        "conversation_id": conversation_id,
                        "timeline": {"events": [], "event_count": 0}
                    }

                # Now try to send the prepared data
                if timeline_data:
                    # Check if the WebSocket is already closed before trying to send anything
                    if hasattr(websocket, '_closed') and websocket._closed:
                        logger.debug(f"Cannot send timeline data to {conversation_id}: WebSocket already closed")
                        return  # Exit early if the WebSocket is already closed

                    try:
                        await websocket.send_json(timeline_data)
                        logger.debug(f"Successfully sent timeline data to {conversation_id}")
                    except WebSocketDisconnect:
                        logger.debug(f"WebSocket disconnected while sending timeline data to {conversation_id}")
                        return  # Exit early
                    except RuntimeError as re:
                        if "WebSocket is not connected" in str(re) or "Cannot call \"send\" once a close message has been sent" in str(re):
                            logger.debug(f"Cannot send timeline data to {conversation_id}: {str(re)}")
                            return  # Exit early
                        else:
                            logger.error(f"Error sending timeline data to {conversation_id}: {str(re)}")
                            return  # Exit early
                    except Exception as e:
                        logger.error(f"Error sending timeline data to {conversation_id}: {str(e)}")
                        return  # Exit early
            except WebSocketDisconnect:
                logger.warning(f"WebSocket disconnected during setup for conversation {conversation_id}")
                return
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Error during WebSocket setup for conversation {conversation_id}: {str(e)}\n{error_traceback}")
                # If we failed before accepting the connection, try to close it gracefully
                if not is_connected:
                    try:
                        # Check if the WebSocket is already closed before trying to close it
                        if not (hasattr(websocket, '_closed') and websocket._closed):
                            await websocket.close(code=1011, reason="Server error during setup")
                    except Exception as close_error:
                        logger.error(f"Error closing WebSocket for conversation {conversation_id}: {str(close_error)}")
                return

            # Now that setup is complete, enter the main WebSocket loop
            try:
                # Keep the connection alive
                while True:
                    # Check if the connection is still open using a safer approach
                    try:
                        # Check if the WebSocket is already closed
                        if hasattr(websocket, '_closed') and websocket._closed:
                            logger.info(f"WebSocket connection for {conversation_id} is already closed")
                            break

                        # Try a small ping to check connection - less frequently
                        # Only send a ping every 30 seconds to reduce connection overhead
                        current_time = time.time()
                        if not hasattr(websocket, '_last_ping_time') or current_time - getattr(websocket, '_last_ping_time', 0) > 30:
                            await websocket.send_json({"type": "ping", "timestamp": int(datetime.now().timestamp() * 1000)})
                            setattr(websocket, '_last_ping_time', current_time)
                    except WebSocketDisconnect:
                        logger.info(f"WebSocket disconnected for conversation {conversation_id} during connection check")
                        break
                    except RuntimeError as re:
                        if "WebSocket is not connected" in str(re) or "Cannot call \"send\" once a close message has been sent" in str(re):
                            logger.info(f"WebSocket connection for {conversation_id} is no longer connected: {str(re)}")
                            break
                        else:
                            logger.error(f"RuntimeError in WebSocket loop for {conversation_id}: {str(re)}")
                            break
                    except Exception as e:
                        logger.info(f"WebSocket connection lost for conversation {conversation_id}: {str(e)}")
                        break

                    # Wait for messages (client pings) with a timeout
                    try:
                        message = await asyncio.wait_for(websocket.receive_text(), timeout=60)  # Increased from 30 to 60 second timeout for better stability

                        # Parse the message if it's JSON
                        try:
                            data = json.loads(message)
                            message_type = data.get("type", "unknown")

                            # Handle different message types
                            if message_type == "ping":
                                # Respond to ping with pong
                                try:
                                    await websocket.send_json({"type": "pong", "timestamp": int(datetime.now().timestamp() * 1000)})
                                    logger.debug(f"Received ping from {conversation_id}, sent pong")
                                except RuntimeError as re:
                                    if "WebSocket is not connected" in str(re):
                                        logger.warning(f"Cannot send pong to {conversation_id}: WebSocket not connected")
                                        break
                                    else:
                                        raise
                                except WebSocketDisconnect:
                                    logger.warning(f"WebSocket disconnected while sending pong to {conversation_id}")
                                    break
                            else:
                                # Echo back a simple acknowledgment for other messages
                                try:
                                    await websocket.send_json({"type": "ack", "message": message})
                                    logger.debug(f"Received message from {conversation_id}, sent ack")
                                except RuntimeError as re:
                                    if "WebSocket is not connected" in str(re):
                                        logger.warning(f"Cannot send ack to {conversation_id}: WebSocket not connected")
                                        break
                                    else:
                                        raise
                                except WebSocketDisconnect:
                                    logger.warning(f"WebSocket disconnected while sending ack to {conversation_id}")
                                    break
                        except json.JSONDecodeError:
                            # If not JSON, just echo back a simple acknowledgment
                            try:
                                await websocket.send_json({"type": "ack", "message": message})
                                logger.debug(f"Received non-JSON message from {conversation_id}, sent ack")
                            except RuntimeError as re:
                                if "WebSocket is not connected" in str(re):
                                    logger.warning(f"Cannot send ack to {conversation_id}: WebSocket not connected")
                                    break
                                else:
                                    raise
                            except WebSocketDisconnect:
                                logger.warning(f"WebSocket disconnected while sending ack to {conversation_id}")
                                break
                    except WebSocketDisconnect:
                        logger.info(f"WebSocket disconnected for conversation {conversation_id} during receive")
                        break
                    except asyncio.TimeoutError:
                        # Send a ping to check if the connection is still alive
                        try:
                            logger.debug(f"Sending ping to {conversation_id} (timeout check)")
                            await websocket.send_json({"type": "ping", "timestamp": int(datetime.now().timestamp() * 1000)})
                        except RuntimeError as re:
                            if "WebSocket is not connected" in str(re):
                                logger.info(f"WebSocket connection for {conversation_id} is no longer connected")
                                break
                            else:
                                raise
                        except WebSocketDisconnect:
                            logger.info(f"WebSocket disconnected for conversation {conversation_id} during ping")
                            break
                        except Exception as e:
                            # If sending fails, the connection is probably dead
                            logger.info(f"WebSocket connection lost for conversation {conversation_id} (ping timeout): {str(e)}")
                            break

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for conversation {conversation_id}")
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"WebSocket error for conversation {conversation_id}: {str(e)}\n{error_traceback}")
            finally:
                # Remove the websocket when disconnected or on error
                try:
                    # Remove from active_websockets list
                    self._active_websockets = [(ws, cid) for ws, cid in self._active_websockets
                                              if ws != websocket]

                    # Remove from the tracking dictionary if this is the current websocket for the conversation
                    if conversation_id in self._websocket_by_conversation and self._websocket_by_conversation[conversation_id] == websocket:
                        del self._websocket_by_conversation[conversation_id]

                    logger.info(f"WebSocket removed from active connections for conversation {conversation_id}")

                    # Try to close the connection gracefully if it's still open
                    try:
                        # Check if the WebSocket is already closed
                        if hasattr(websocket, '_closed') and not websocket._closed:
                            await websocket.close()
                        elif is_connected:
                            await websocket.close()
                    except RuntimeError as re:
                        if "Cannot call \"send\" once a close message has been sent" in str(re) or "Unexpected ASGI message 'websocket.close'" in str(re):
                            logger.info(f"WebSocket for conversation {conversation_id} is already closed")
                        else:
                            logger.error(f"Error closing WebSocket for conversation {conversation_id}: {str(re)}")
                    except Exception as close_error:
                        logger.error(f"Error closing WebSocket for conversation {conversation_id}: {str(close_error)}")
                except Exception as e:
                    import traceback
                    error_traceback = traceback.format_exc()
                    logger.error(f"Error cleaning up WebSocket for conversation {conversation_id}: {str(e)}\n{error_traceback}")

        self._app = app

    async def _broadcast_timeline_update(self, conversation_id: str, timeline_data: Dict[str, Any]):
        """Broadcast timeline updates to connected websockets."""
        # Prepare the message once
        message = {
            "type": "timeline_update",
            "conversation_id": conversation_id,
            "timeline": timeline_data
        }

        # First try to use the dedicated WebSocket for this conversation
        if conversation_id in self._websocket_by_conversation:
            websocket = self._websocket_by_conversation[conversation_id]
            try:
                # Check if the websocket is still connected
                if not (hasattr(websocket, '_closed') and websocket._closed):
                    await websocket.send_json(message)
                    logger.debug(f"Timeline update broadcast to dedicated WebSocket for conversation {conversation_id}")
                    return  # Successfully sent to the dedicated WebSocket
                else:
                    # WebSocket is closed, remove it from tracking
                    logger.warning(f"Dedicated WebSocket for conversation {conversation_id} is closed, removing from tracking")
                    del self._websocket_by_conversation[conversation_id]
                    # Continue to try other WebSockets
            except RuntimeError as re:
                if "WebSocket is not connected" in str(re) or "Cannot call \"send\" once a close message has been sent" in str(re):
                    logger.warning(f"Cannot broadcast to dedicated WebSocket for conversation {conversation_id}: {str(re)}")
                    del self._websocket_by_conversation[conversation_id]
                    # Continue to try other WebSockets
                else:
                    logger.error(f"Error broadcasting to dedicated WebSocket for conversation {conversation_id}: {str(re)}")
                    del self._websocket_by_conversation[conversation_id]
                    # Continue to try other WebSockets
            except WebSocketDisconnect:
                logger.warning(f"Dedicated WebSocket disconnected while broadcasting to conversation {conversation_id}")
                del self._websocket_by_conversation[conversation_id]
                # Continue to try other WebSockets
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Error broadcasting timeline update to dedicated WebSocket for conversation {conversation_id}: {str(e)}\n{error_traceback}")
                del self._websocket_by_conversation[conversation_id]
                # Continue to try other WebSockets

        # If we get here, either there was no dedicated WebSocket or it failed
        # Try to find any other WebSockets for this conversation
        # Create a copy of the active websockets to avoid modification during iteration
        active_websockets = list(self._active_websockets)
        websockets_to_remove = []
        success = False

        for websocket, ws_conversation_id in active_websockets:
            if ws_conversation_id == conversation_id:
                try:
                    # Check if the websocket is still connected
                    if not (hasattr(websocket, '_closed') and websocket._closed):
                        await websocket.send_json(message)
                        logger.debug(f"Timeline update broadcast to alternative WebSocket for conversation {conversation_id}")
                        success = True
                        # Update the dedicated WebSocket if we found a working one
                        self._websocket_by_conversation[conversation_id] = websocket
                        break  # Successfully sent to an alternative WebSocket
                    else:
                        websockets_to_remove.append(websocket)
                except RuntimeError as re:
                    if "WebSocket is not connected" in str(re) or "Cannot call \"send\" once a close message has been sent" in str(re):
                        logger.warning(f"Cannot broadcast to alternative WebSocket for conversation {conversation_id}: {str(re)}")
                        websockets_to_remove.append(websocket)
                    else:
                        logger.error(f"Error broadcasting to alternative WebSocket for conversation {conversation_id}: {str(re)}")
                        websockets_to_remove.append(websocket)
                except WebSocketDisconnect:
                    logger.warning(f"Alternative WebSocket disconnected while broadcasting to conversation {conversation_id}")
                    websockets_to_remove.append(websocket)
                except Exception as e:
                    import traceback
                    error_traceback = traceback.format_exc()
                    logger.error(f"Error broadcasting timeline update to alternative WebSocket for conversation {conversation_id}: {str(e)}\n{error_traceback}")
                    websockets_to_remove.append(websocket)

        # Remove any dead websockets
        if websockets_to_remove:
            self._active_websockets = [(ws, cid) for ws, cid in self._active_websockets
                                      if ws not in websockets_to_remove]
            logger.info(f"Removed {len(websockets_to_remove)} dead WebSocket connections")

        if not success:
            logger.warning(f"Failed to broadcast timeline update to any WebSocket for conversation {conversation_id}")

    def start(self, host: str = None, port: int = None):
        """Start the Nexagent API server"""
        if self._running:
            logger.warning("Nexagent API server is already running")
            return

        if host:
            self._host = host

        if port:
            self._port = port

        def run_server():
            uvicorn.run(self._app, host=self._host, port=self._port)

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()
        self._running = True

        logger.info(f"Nexagent API server started at http://{self._host}:{self._port}")

    def stop(self):
        """Stop the Nexagent API server"""
        if not self._running:
            logger.warning("Nexagent API server is not running")
            return

        # There's no clean way to stop uvicorn in a thread, so we'll just mark it as stopped
        # In a production environment, you would use a proper process manager
        self._running = False
        logger.info("Nexagent API server stopped")

    def is_running(self):
        """Check if the Nexagent API server is running"""
        return self._running

    def get_url(self):
        """Get the URL of the Nexagent API server"""
        return f"http://{self._host}:{self._port}"

    def register_tool(self, tool):
        """Register a tool with the Nexagent server

        Args:
            tool: The tool to register
        """
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, tool_name):
        """Get a registered tool by name

        Args:
            tool_name: The name of the tool to get

        Returns:
            The tool if found, None otherwise
        """
        return self._tools.get(tool_name)

    def register_memory_reasoning(self, memory_reasoning):
        """Register a memory reasoning instance with the Nexagent server

        Args:
            memory_reasoning: The memory reasoning instance to register
        """
        self._memory_reasoning = memory_reasoning
        logger.info("Registered memory reasoning system")

    def get_memory_reasoning(self):
        """Get the registered memory reasoning instance

        Returns:
            The memory reasoning instance if registered, None otherwise
        """
        return self._memory_reasoning

    def register_flow_initializer(self, initializer_func):
        """Register a flow initializer function

        Args:
            initializer_func: A function that takes a flow instance and initializes it
        """
        self._flow_initializers.append(initializer_func)
        logger.info(f"Registered flow initializer: {initializer_func.__name__ if hasattr(initializer_func, '__name__') else 'anonymous'}")

    def initialize_flow(self, flow):
        """Initialize a flow with all registered initializers

        Args:
            flow: The flow instance to initialize
        """
        for initializer in self._flow_initializers:
            try:
                initializer(flow)
            except Exception as e:
                logger.error(f"Error in flow initializer {initializer.__name__ if hasattr(initializer, '__name__') else 'anonymous'}: {str(e)}")

    def _format_response_for_display(self, response: str) -> str:
        """
        Format the response to ensure it's properly structured for display to the user.
        This method ensures the response is well-formatted while preserving important content.

        Args:
            response: The raw response from the agent

        Returns:
            The formatted response suitable for display to the user
        """
        # Get the conversation ID from the current request if available
        conversation_id = None
        if hasattr(self, '_current_conversation_id'):
            conversation_id = self._current_conversation_id

        # Extract agent thoughts from the conversation history if available
        agent_thoughts = None
        if conversation_id and conversation_id in self._conversations:
            messages = self._conversations[conversation_id].get('messages', [])
            # Extract thoughts from the messages
            for msg in reversed(messages):
                if msg.get('role') == 'assistant' and msg.get('content'):
                    content = msg.get('content', '')
                    if "Nexagent's thoughts:" in content:
                        # Extract the thoughts
                        thoughts_parts = content.split("Nexagent's thoughts:", 1)
                        if len(thoughts_parts) > 1:
                            agent_thoughts = thoughts_parts[1].strip()
                            break

        # Use the response formatter to format the response
        formatted_response = format_response(response, agent_thoughts)

        # If the formatted response is too short, try to extract more information
        if len(formatted_response) < 100 and agent_thoughts:
            # Use the agent thoughts directly
            return agent_thoughts

        return formatted_response

# Singleton instance
nexagent_server = NexagentServer()