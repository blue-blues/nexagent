"""Google Generative AI client implementation for Gemini models."""

import json
from typing import List, Optional, Dict, Any, AsyncGenerator

import aiohttp

from app.logger import logger


class GoogleGenerativeAIClient:
    """A custom client for Google's Generative AI API that mimics the OpenAI client interface"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        # Create a structure similar to OpenAI client with chat.completions
        self.chat = type('ChatObject', (), {'completions': GoogleChatCompletions(api_key, base_url, model)})()
        


class GoogleChatCompletions:
    """Mimics the OpenAI chat completions interface for Google's Generative AI API"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
    
    async def create(self, **kwargs) -> Any:
        """Create a chat completion using Google's Generative AI API"""
        model = kwargs.get("model", self.model)
        messages = kwargs.get("messages", [])
        max_tokens = kwargs.get("max_tokens", 1024)
        temperature = kwargs.get("temperature", 0.0)
        stream = kwargs.get("stream", False)
        tools = kwargs.get("tools", None)
        tool_choice = kwargs.get("tool_choice", None)
        
        # Convert OpenAI message format to Google's format
        google_messages = self._convert_messages(messages)
        
        # Build the request URL
        url = f"{self.base_url}/models/{model}:generateContent"
        
        # Build the request payload
        payload = {
            "contents": google_messages,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            }
        }
        
        # Add tools if provided and not empty
        if tools:
            payload["tools"] = self._convert_tools(tools)
        
        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        if stream:
            return self._stream_response(url, payload, headers)
        else:
            return await self._send_request(url, payload, headers)
    
    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI message format to Google's format"""
        google_messages = []
        
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            
            if role == "system":
                # For system messages, add as a user message with a special prefix
                google_messages.append({
                    "role": "user",
                    "parts": [{"text": f"System: {content}"}]
                })
                # Add a model response to maintain conversation flow
                google_messages.append({
                    "role": "model",
                    "parts": [{"text": "I'll follow those instructions."}]
                })
            elif role == "user":
                # Ensure content is not empty to avoid INVALID_ARGUMENT errors
                safe_content = content if content else " "  # Use a space if content is empty
                google_messages.append({
                    "role": "user",
                    "parts": [{"text": safe_content}]
                })
            elif role == "assistant":
                # Ensure content is not empty to avoid INVALID_ARGUMENT errors
                safe_content = content if content else " "  # Use a space if content is empty
                google_messages.append({
                    "role": "model",
                    "parts": [{"text": safe_content}]
                })
            # Skip function/tool messages for now as they're handled differently
        
        return google_messages
    
    def _convert_tools(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert OpenAI tools format to Google's format"""
        # This is a simplified implementation
        google_tools = {
            "functionDeclarations": []
        }
        
        # Check if tools is None or empty
        if not tools:
            return google_tools
        
        for tool in tools:
            if tool.get("type") == "function":
                function = tool.get("function", {})
                parameters = function.get("parameters", {})
                
                # Process parameters to remove 'default' fields that Google API doesn't support
                if parameters and "properties" in parameters:
                    for prop_name, prop_value in parameters["properties"].items():
                        if "default" in prop_value:
                            del prop_value["default"]
                
                # Ensure name and description are not empty to avoid INVALID_ARGUMENT errors
                name = function.get("name", "")
                description = function.get("description", "")
                
                # Use default values if empty
                name = name if name else "unnamed_function"
                description = description if description else "No description provided"
                
                google_tools["functionDeclarations"].append({
                    "name": name,
                    "description": description,
                    "parameters": parameters
                })
        
        return google_tools
    
    async def _send_request(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Any:
        """Send a request to the Google Generative AI API"""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Google API error: {error_text}")
                
                data = await response.json()
                
                # Convert Google's response format to OpenAI's format
                return self._convert_response(data)
    
    async def _stream_response(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> AsyncGenerator[Any, None]:
        """Stream a response from the Google Generative AI API"""
        # Add streaming parameter to URL
        stream_url = f"{url}?alt=sse"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(stream_url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Google API error: {error_text}")
                
                # Create a generator that yields chunks in OpenAI format
                async for chunk in response.content.iter_any():
                    if chunk:
                        try:
                            # Parse the SSE data
                            lines = chunk.decode('utf-8').strip().split('\n')
                            for line in lines:
                                if line.startswith('data: '):
                                    data_str = line[6:]
                                    if data_str == "[DONE]":
                                        break
                                    
                                    data = json.loads(data_str)
                                    yield self._convert_stream_chunk(data)
                        except Exception as e:
                            logger.error(f"Error parsing stream chunk: {e}")
    
    def _convert_response(self, data: Dict[str, Any]) -> Any:
        """Convert Google's response format to OpenAI's format"""
        try:
            # Extract the response content
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in response")
            
            content = ""
            for candidate in candidates:
                content_parts = candidate.get("content", {}).get("parts", [])
                for part in content_parts:
                    if "text" in part:
                        content += part["text"]
            
            # Create an OpenAI-like response object with all required attributes
            class OpenAIResponse:
                def __init__(self, choices, usage):
                    self.choices = choices
                    self.usage = usage
                    self.id = "gemini-response-id"
                    self.model = self.model if hasattr(self, 'model') else "gemini-model"
                    self.object = "chat.completion"
                    self.created = 0
            
            class Choice:
                def __init__(self, message):
                    self.message = message
                    self.index = 0
                    self.finish_reason = "stop"
                    self.logprobs = None
            
            class Message:
                def __init__(self, content):
                    self.content = content
                    self.role = "assistant"
                    self.function_call = None
                    self.tool_calls = None
            
            class Usage:
                def __init__(self, prompt_tokens):
                    self.prompt_tokens = prompt_tokens
                    self.completion_tokens = len(content.split())
                    self.total_tokens = self.prompt_tokens + self.completion_tokens
            
            # Estimate token count (this is approximate)
            prompt_tokens = 100  # Default estimate
            
            return OpenAIResponse(
                choices=[Choice(Message(content))],
                usage=Usage(prompt_tokens)
            )
        except Exception as e:
            logger.error(f"Error converting Google response: {e}")
            raise
    

    
    def _convert_stream_chunk(self, data: Dict[str, Any]) -> Any:
        """Convert a Google stream chunk to OpenAI format"""
        try:
            # Define the classes inside the method to ensure they're available
            class Delta:
                def __init__(self, content):
                    self.content = content
                    self.role = None
                    self.function_call = None
                    self.tool_calls = None
            
            class Choice:
                def __init__(self, delta):
                    self.delta = delta
                    self.index = 0
                    self.finish_reason = None
            
            class OpenAIChunk:
                def __init__(self, choices):
                    self.choices = choices
                    self.id = "gemini-chunk-id"
                    self.model = "gemini-model"
                    self.object = "chat.completion.chunk"
                    self.created = 0
            
            # Extract content from the chunk
            candidates = data.get("candidates", [])
            if not candidates:
                # Create an empty chunk with all required attributes
                return OpenAIChunk(choices=[Choice(Delta(""))])
            
            content = ""
            for candidate in candidates:
                content_parts = candidate.get("content", {}).get("parts", [])
                for part in content_parts:
                    if "text" in part:
                        content += part["text"]
            
            return OpenAIChunk(choices=[Choice(Delta(content))])
        except Exception as e:
            logger.error(f"Error converting Google stream chunk: {e}")
            # Define the classes again in case they weren't defined in the exception path
            class Delta:
                def __init__(self, content):
                    self.content = content
                    self.role = None
                    self.function_call = None
                    self.tool_calls = None
            
            class Choice:
                def __init__(self, delta):
                    self.delta = delta
                    self.index = 0
                    self.finish_reason = None
            
            class OpenAIChunk:
                def __init__(self, choices):
                    self.choices = choices
                    self.id = "gemini-chunk-id"
                    self.model = "gemini-model"
                    self.object = "chat.completion.chunk"
                    self.created = 0
            
            # Return a properly structured empty chunk
            return OpenAIChunk(choices=[Choice(Delta(""))])