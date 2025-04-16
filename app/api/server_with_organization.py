import json
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import threading
from datetime import datetime
import uuid
import re

from app.logger import logger
from app.agent.manus import Nexagent
from app.flow.integrated_flow import IntegratedFlow
from app.api.conversation_handler import ConversationHandler

# Models for API requests and responses
class MessageRequest(BaseModel):
    content: str = Field(..., description="Message content from the user")
    conversation_id: Optional[str] = Field(None, description="Conversation ID if continuing an existing conversation")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt to override default")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional parameters for the agent")

class MessageResponse(BaseModel):
    id: str = Field(..., description="Message ID")
    content: str = Field(..., description="Response content from the assistant")
    conversation_id: str = Field(..., description="Conversation ID")
    timestamp: int = Field(..., description="Timestamp of the response")
    conversation_title: Optional[str] = Field(None, description="Title of the conversation, provided for new conversations")

class ConversationResponse(BaseModel):
    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    messages: List[Dict[str, Any]] = Field(..., description="List of messages in the conversation")
    created_at: int = Field(..., description="Creation timestamp")
    updated_at: int = Field(..., description="Last update timestamp")
    folder_path: Optional[str] = Field(None, description="Path to the conversation folder")

class MaterialRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID")
    material_name: str = Field(..., description="Name of the material")
    material_content: str = Field(..., description="Content of the material")

class MaterialResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    material_path: Optional[str] = Field(None, description="Path to the saved material")

class GenerateOutputRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID")
    output_format: str = Field("pdf", description="Format of the output document (pdf or markdown)")

class GenerateOutputResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    output_path: Optional[str] = Field(None, description="Path to the generated output")

# Server class
class NexagentServerWithOrganization:
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
        self.conversation_handler = ConversationHandler()

    def _generate_conversation_title(self, message_content: str) -> str:
        """Generate a meaningful title from the first message content.

        Args:
            message_content: The content of the first message

        Returns:
            A generated title for the conversation
        """
        # Remove special characters and extra whitespace
        cleaned_content = re.sub(r'[^\w\s]', '', message_content).strip()

        # If the message is too short, return a generic title
        if len(cleaned_content) < 10:
            return f"Chat about {cleaned_content}"

        # If the message is too long, truncate it
        if len(cleaned_content) > 50:
            # Try to find a natural break point (end of a sentence or phrase)
            match = re.search(r'^(.{15,45}[.!?]\s)', cleaned_content)
            if match:
                return match.group(1).strip()
            else:
                # Just take the first 40 characters and add ellipsis
                return cleaned_content[:40].strip() + "..."

        return cleaned_content

    def _init_app(self):
        """Initialize the FastAPI application"""
        app = FastAPI(title="Nexagent API", description="API for Nexagent AI Assistant with Conversation Organization")

        # Add CORS middleware to allow requests from the frontend
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify your frontend URL
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Define API routes
        @app.get("/")
        async def root():
            return {"message": "Nexagent API is running", "status": "active"}

        @app.post("/api/message", response_model=MessageResponse)
        async def process_message(request: MessageRequest):
            # Create or get conversation
            conversation_id = request.conversation_id
            if not conversation_id or conversation_id not in self._conversations:
                conversation_id = str(uuid.uuid4())
                # Generate a title based on the first message content
                conversation_title = self._generate_conversation_title(request.content)

                # Create conversation in memory
                self._conversations[conversation_id] = {
                    "id": conversation_id,
                    "title": conversation_title,
                    "messages": [],
                    "created_at": int(datetime.now().timestamp() * 1000),
                    "updated_at": int(datetime.now().timestamp() * 1000),
                }

                # Create conversation folder
                folder_result = await self.conversation_handler.handle_new_conversation(
                    conversation_id, conversation_title
                )

                if folder_result.get("success"):
                    self._conversations[conversation_id]["folder_path"] = folder_result.get("folder_path")

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

                # Process the request
                result = await flow.execute(request.content, conversation_id=conversation_id)

                # Extract timeline data if available
                timeline_data = None
                if isinstance(result, dict) and "timeline" in result:
                    timeline_data = result.get("timeline")
                    result = result.get("result", result)

                # Create assistant message
                assistant_message = {
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": result,
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "timeline": timeline_data
                }

                # Add assistant message to conversation
                self._conversations[conversation_id]["messages"].append(assistant_message)
                self._conversations[conversation_id]["updated_at"] = assistant_message["timestamp"]

                # Broadcast timeline updates to connected websockets
                if timeline_data:
                    await self._broadcast_timeline_update(conversation_id, timeline_data)

                # Save conversation messages to folder
                await self.conversation_handler.save_conversation_messages(
                    conversation_id, self._conversations[conversation_id]["messages"]
                )

                # Generate output document after each message exchange
                await self.conversation_handler.generate_output(conversation_id)

                # Determine if this is a new conversation (first message exchange)
                is_new_conversation = len(self._conversations[conversation_id]["messages"]) <= 2

                return {
                    "id": assistant_message["id"],
                    "content": assistant_message["content"],
                    "conversation_id": conversation_id,
                    "timestamp": assistant_message["timestamp"],
                    "conversation_title": self._conversations[conversation_id]["title"] if is_new_conversation else None
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
            if conversation_id not in self._conversations:
                raise HTTPException(status_code=404, detail="Conversation not found")

            # Get the most recent message with timeline data
            messages = self._conversations[conversation_id]["messages"]
            for message in reversed(messages):
                if message.get("role") == "assistant" and message.get("timeline"):
                    return message["timeline"]

            # No timeline data found
            return {"events": [], "event_count": 0}

        @app.post("/api/materials", response_model=MaterialResponse)
        async def save_material(request: MaterialRequest):
            if request.conversation_id not in self._conversations:
                raise HTTPException(status_code=404, detail="Conversation not found")

            result = await self.conversation_handler.save_material(
                request.conversation_id,
                request.material_name,
                request.material_content
            )

            if not result.get("success"):
                raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

            return result

        @app.post("/api/generate-output", response_model=GenerateOutputResponse)
        async def generate_output(request: GenerateOutputRequest):
            if request.conversation_id not in self._conversations:
                raise HTTPException(status_code=404, detail="Conversation not found")

            result = await self.conversation_handler.generate_output(
                request.conversation_id,
                request.output_format
            )

            if not result.get("success"):
                raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

            return result

        @app.get("/api/health")
        async def health_check():
            return {
                "status": "ok",
                "server": "Nexagent API with Organization",
                "version": "1.0.0",
                "timestamp": int(datetime.now().timestamp() * 1000),
                "connections": len(self._active_websockets),
                "conversations": len(self._conversations)
            }

        @app.websocket("/api/ws/timeline/{conversation_id}")
        async def timeline_websocket(websocket: WebSocket, conversation_id: str):
            # Accept all WebSocket connections, even for new or mock conversations
            # This allows the frontend to connect even before a conversation is created
            await websocket.accept()

            # Log the connection
            logger.info(f"WebSocket connection accepted for conversation {conversation_id}")

            # Add the websocket to active connections
            self._active_websockets.append((websocket, conversation_id))

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

            try:
                # Keep the connection alive
                while True:
                    # Wait for messages (client pings)
                    message = await websocket.receive_text()
                    # Echo back a simple acknowledgment
                    await websocket.send_json({"type": "ack", "message": message})
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for conversation {conversation_id}")
                # Remove the websocket when disconnected
                self._active_websockets = [(ws, cid) for ws, cid in self._active_websockets
                                          if ws != websocket]

        self._app = app

    async def _broadcast_timeline_update(self, conversation_id: str, timeline_data: Dict[str, Any]):
        """Broadcast timeline updates to connected websockets."""
        for websocket, ws_conversation_id in self._active_websockets:
            if ws_conversation_id == conversation_id:
                try:
                    await websocket.send_json({
                        "type": "timeline_update",
                        "conversation_id": conversation_id,
                        "timeline": timeline_data
                    })
                except Exception as e:
                    logger.error(f"Error sending timeline update to websocket: {str(e)}")

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

        self._server_thread = threading.Thread(target=run_server)
        self._server_thread.daemon = True
        self._server_thread.start()
        self._running = True
        logger.info(f"Nexagent API server started at http://{self._host}:{self._port}")

    def stop(self):
        """Stop the Nexagent API server"""
        if not self._running:
            logger.warning("Nexagent API server is not running")
            return

        # There's no clean way to stop uvicorn in a thread, so we'll just set the flag
        self._running = False
        logger.info("Nexagent API server stopped")

# Create a singleton instance
server = NexagentServerWithOrganization()