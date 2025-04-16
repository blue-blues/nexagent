"""OpenRouter API client for NexAgent.

This module provides a custom client for OpenRouter's API that integrates with
the NexAgent LLM interface. It allows using various AI models through OpenRouter's
API gateway while maintaining compatibility with the existing LLM interface.
"""

from typing import Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk


class OpenRouterClient:
    """A client for OpenRouter's API that mimics the OpenAI client interface."""

    def __init__(self, api_key: str, base_url: str, model: str, site_url: Optional[str] = None, site_name: Optional[str] = None):
        """Initialize the OpenRouter client.

        Args:
            api_key: The OpenRouter API key
            base_url: The OpenRouter API base URL
            model: The model to use
            site_url: Optional site URL for rankings on openrouter.ai
            site_name: Optional site name for rankings on openrouter.ai
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.site_url = site_url
        self.site_name = site_name
        
        # Create the OpenAI client with OpenRouter base URL
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        # Create a structure similar to OpenAI client with chat.completions
        self.chat = self.client.chat

    def _get_extra_headers(self) -> Dict[str, str]:
        """Get extra headers for OpenRouter API requests.

        Returns:
            Dict[str, str]: The extra headers
        """
        headers = {}
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.site_name:
            headers["X-Title"] = self.site_name
        return headers

    async def create_completion(self, **kwargs) -> ChatCompletion:
        """Create a chat completion using OpenRouter API.

        Args:
            **kwargs: The completion parameters

        Returns:
            ChatCompletion: The completion response
        """
        # Add extra headers and body for OpenRouter
        extra_headers = self._get_extra_headers()
        
        # Create the completion
        return await self.client.chat.completions.create(
            extra_headers=extra_headers,
            extra_body={},  # Can be extended with additional parameters if needed
            **kwargs
        )

    async def create_completion_stream(self, **kwargs) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Create a streaming chat completion using OpenRouter API.

        Args:
            **kwargs: The completion parameters

        Returns:
            AsyncGenerator[ChatCompletionChunk, None]: The streaming completion response
        """
        # Add extra headers and body for OpenRouter
        extra_headers = self._get_extra_headers()
        
        # Create the streaming completion
        return await self.client.chat.completions.create(
            extra_headers=extra_headers,
            extra_body={},  # Can be extended with additional parameters if needed
            **kwargs
        )