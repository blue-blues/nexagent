import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field
import threading
import asyncio
from datetime import datetime

from app.tool.base import BaseTool, ToolResult
from app.logger import logger
from app.config import config, PROJECT_ROOT


class DataItem(BaseModel):
    """Model for a data item stored in the MCP server"""
    id: str = Field(..., description="Unique identifier for the data item")
    content: Dict[str, Any] = Field(..., description="Content of the data item")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata for the data item")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Creation timestamp")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Last update timestamp")


class DataQuery(BaseModel):
    """Model for querying data from the MCP server"""
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filters to apply to the query")
    limit: int = Field(10, description="Maximum number of items to return")
    offset: int = Field(0, description="Offset for pagination")


class MCPServer:
    """Master Control Program (MCP) Server for data management"""
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    _app = None
    _server_thread = None
    _data_store = {}
    _data_dir = PROJECT_ROOT / "data_store"
    _port = 8765
    _host = "127.0.0.1"
    _running = False

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
        """Initialize the MCP server"""
        # Create data directory if it doesn't exist
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing data from disk
        self._load_data()
        
        # Initialize FastAPI app
        self._init_app()
        
        self._initialized = True

    def _init_app(self):
        """Initialize the FastAPI application"""
        app = FastAPI(title="MCP Data Server", description="Master Control Program for data management")
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Define API routes
        @app.get("/")
        async def root():
            return {"message": "MCP Data Server is running", "status": "active"}
        
        @app.get("/data")
        async def get_all_data():
            return {"data": list(self._data_store.values())}
        
        @app.get("/data/{item_id}")
        async def get_data(item_id: str):
            if item_id not in self._data_store:
                raise HTTPException(status_code=404, detail="Data item not found")
            return {"data": self._data_store[item_id]}
        
        @app.post("/data")
        async def create_data(item: DataItem):
            if item.id in self._data_store:
                raise HTTPException(status_code=400, detail="Data item with this ID already exists")
            
            self._data_store[item.id] = item.dict()
            self._save_data()
            return {"message": "Data item created", "data": item}
        
        @app.put("/data/{item_id}")
        async def update_data(item_id: str, item: DataItem):
            if item_id not in self._data_store:
                raise HTTPException(status_code=404, detail="Data item not found")
            
            if item_id != item.id:
                raise HTTPException(status_code=400, detail="ID in path must match ID in body")
            
            item.updated_at = datetime.now().isoformat()
            self._data_store[item_id] = item.dict()
            self._save_data()
            return {"message": "Data item updated", "data": item}
        
        @app.delete("/data/{item_id}")
        async def delete_data(item_id: str):
            if item_id not in self._data_store:
                raise HTTPException(status_code=404, detail="Data item not found")
            
            del self._data_store[item_id]
            self._save_data()
            return {"message": "Data item deleted"}
        
        @app.post("/data/query")
        async def query_data(query: DataQuery):
            results = []
            
            for item in self._data_store.values():
                match = True
                
                # Apply filters
                for key, value in query.filters.items():
                    # Handle nested keys with dot notation
                    if '.' in key:
                        parts = key.split('.')
                        current = item
                        for part in parts[:-1]:
                            if part not in current:
                                match = False
                                break
                            current = current[part]
                        
                        if match and (parts[-1] not in current or current[parts[-1]] != value):
                            match = False
                    elif key not in item or item[key] != value:
                        match = False
                
                if match:
                    results.append(item)
            
            # Apply pagination
            paginated = results[query.offset:query.offset + query.limit]
            
            return {"data": paginated, "total": len(results)}
        
        self._app = app

    def _load_data(self):
        """Load data from disk"""
        data_file = self._data_dir / "data_store.json"
        
        if data_file.exists():
            try:
                with open(data_file, 'r') as f:
                    self._data_store = json.load(f)
                logger.info(f"Loaded {len(self._data_store)} data items from disk")
            except Exception as e:
                logger.error(f"Error loading data from disk: {str(e)}")
                self._data_store = {}

    def _save_data(self):
        """Save data to disk"""
        data_file = self._data_dir / "data_store.json"
        
        try:
            with open(data_file, 'w') as f:
                json.dump(self._data_store, f, indent=2)
            logger.info(f"Saved {len(self._data_store)} data items to disk")
        except Exception as e:
            logger.error(f"Error saving data to disk: {str(e)}")

    def start(self, host: str = None, port: int = None):
        """Start the MCP server"""
        if self._running:
            logger.warning("MCP server is already running")
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
        logger.info(f"MCP server started at http://{self._host}:{self._port}")

    def stop(self):
        """Stop the MCP server"""
        if not self._running:
            logger.warning("MCP server is not running")
            return
        
        # Save data before stopping
        self._save_data()
        
        # There's no clean way to stop uvicorn in a thread, so we'll just set the flag
        self._running = False
        logger.info("MCP server stopped")

    def is_running(self):
        """Check if the MCP server is running"""
        return self._running

    def get_url(self):
        """Get the URL of the MCP server"""
        if not self._running:
            return None
        
        return f"http://{self._host}:{self._port}"

    def add_data(self, item_id: str, content: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Add a data item to the store"""
        if not metadata:
            metadata = {}
        
        timestamp = datetime.now().isoformat()
        
        data_item = {
            "id": item_id,
            "content": content,
            "metadata": metadata,
            "created_at": timestamp,
            "updated_at": timestamp
        }
        
        self._data_store[item_id] = data_item
        self._save_data()
        
        return data_item

    def get_data(self, item_id: str):
        """Get a data item from the store"""
        return self._data_store.get(item_id)

    def update_data(self, item_id: str, content: Dict[str, Any] = None, metadata: Dict[str, Any] = None):
        """Update a data item in the store"""
        if item_id not in self._data_store:
            return None
        
        data_item = self._data_store[item_id]
        
        if content is not None:
            data_item["content"] = content
        
        if metadata is not None:
            data_item["metadata"] = metadata
        
        data_item["updated_at"] = datetime.now().isoformat()
        
        self._save_data()
        
        return data_item

    def delete_data(self, item_id: str):
        """Delete a data item from the store"""
        if item_id not in self._data_store:
            return False
        
        del self._data_store[item_id]
        self._save_data()
        
        return True

    def query_data(self, filters: Dict[str, Any] = None, limit: int = 10, offset: int = 0):
        """Query data items from the store"""
        if not filters:
            filters = {}
        
        results = []
        
        for item in self._data_store.values():
            match = True
            
            for key, value in filters.items():
                # Handle nested keys with dot notation
                if '.' in key:
                    parts = key.split('.')
                    current = item
                    for part in parts[:-1]:
                        if part not in current:
                            match = False
                            break
                        current = current[part]
                    
                    if match and (parts[-1] not in current or current[parts[-1]] != value):
                        match = False
                elif key not in item or item[key] != value:
                    match = False
            
            if match:
                results.append(item)
        
        # Apply pagination
        paginated = results[offset:offset + limit]
        
        return paginated, len(results)


class MCPServerTool(BaseTool):
    """Tool for interacting with the MCP server"""
    name: str = "mcp_server"
    description: str = """Master Control Program (MCP) Server for data management.
    
    This tool provides a persistent data storage and retrieval system with the following features:
    * State is persistent across command calls and discussions with the user
    * Data is stored in a structured format with metadata
    * Server provides RESTful API endpoints for data access
    * Data can be queried with filters and pagination
    * All data is automatically saved to disk
    
    The MCP server can be started, stopped, and interacted with through this tool.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The command to execute. Available commands: start, stop, status, add_data, get_data, update_data, delete_data, query_data",
                "enum": ["start", "stop", "status", "add_data", "get_data", "update_data", "delete_data", "query_data"],
                "type": "string"
            },
            "host": {
                "description": "Host address for the server (only used with start command)",
                "type": "string"
            },
            "port": {
                "description": "Port number for the server (only used with start command)",
                "type": "integer"
            },
            "item_id": {
                "description": "ID of the data item (required for add_data, get_data, update_data, delete_data)",
                "type": "string"
            },
            "content": {
                "description": "Content of the data item (required for add_data, optional for update_data)",
                "type": "object"
            },
            "metadata": {
                "description": "Metadata for the data item (optional for add_data, update_data)",
                "type": "object"
            },
            "filters": {
                "description": "Filters for querying data (used with query_data)",
                "type": "object"
            },
            "limit": {
                "description": "Maximum number of items to return (used with query_data)",
                "type": "integer"
            },
            "offset": {
                "description": "Offset for pagination (used with query_data)",
                "type": "integer"
            }
        },
        "required": ["command"]
    }
    
    def __init__(self):
        super().__init__()
        self.server = MCPServer()
    
    async def execute(
        self,
        *,
        command: str,
        host: str = None,
        port: int = None,
        item_id: str = None,
        content: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
        filters: Dict[str, Any] = None,
        limit: int = 10,
        offset: int = 0,
        **kwargs
    ) -> str:
        """Execute the MCP server tool with the given parameters"""
        
        if command == "start":
            if self.server.is_running():
                return ToolResult(output=f"MCP server is already running at {self.server.get_url()}")
            
            self.server.start(host=host, port=port)
            return ToolResult(output=f"MCP server started at {self.server.get_url()}")
        
        elif command == "stop":
            if not self.server.is_running():
                return ToolResult(output="MCP server is not running")
            
            self.server.stop()
            return ToolResult(output="MCP server stopped")
        
        elif command == "status":
            if self.server.is_running():
                return ToolResult(output=f"MCP server is running at {self.server.get_url()}")
            else:
                return ToolResult(output="MCP server is not running")
        
        elif command == "add_data":
            if not item_id:
                return ToolResult(error="item_id is required for add_data command")
            
            if not content:
                return ToolResult(error="content is required for add_data command")
            
            data_item = self.server.add_data(item_id, content, metadata)
            return ToolResult(output=f"Data item added: {json.dumps(data_item, indent=2)}")
        
        elif command == "get_data":
            if not item_id:
                return ToolResult(error="item_id is required for get_data command")
            
            data_item = self.server.get_data(item_id)
            
            if not data_item:
                return ToolResult(error=f"Data item with ID '{item_id}' not found")
            
            return ToolResult(output=f"Data item: {json.dumps(data_item, indent=2)}")
        
        elif command == "update_data":
            if not item_id:
                return ToolResult(error="item_id is required for update_data command")
            
            data_item = self.server.update_data(item_id, content, metadata)
            
            if not data_item:
                return ToolResult(error=f"Data item with ID '{item_id}' not found")
            
            return ToolResult(output=f"Data item updated: {json.dumps(data_item, indent=2)}")
        
        elif command == "delete_data":
            if not item_id:
                return ToolResult(error="item_id is required for delete_data command")
            
            success = self.server.delete_data(item_id)
            
            if not success:
                return ToolResult(error=f"Data item with ID '{item_id}' not found")
            
            return ToolResult(output=f"Data item with ID '{item_id}' deleted")
        
        elif command == "query_data":
            data_items, total = self.server.query_data(filters, limit, offset)
            
            return ToolResult(
                output=f"Query returned {len(data_items)} of {total} total items:\n{json.dumps(data_items, indent=2)}"
            )
        
        else:
            return ToolResult(error=f"Unknown command: {command}")