"""
Context-Aware LLM Module

This module provides a language model implementation that is aware of context.
It extends the base LLM with context management capabilities.
"""

from typing import Any, Dict, List, Optional, Union
import json
from datetime import datetime

from app.core.context import (
    ContextEntry,
    ContextProtocol,
    VersionedContextProtocol,
    ContextManager,
    extract_context_for_llm
)


class ContextAwareLLM:
    """
    A language model that is aware of context.
    This class can be used to extend any LLM with context management capabilities.
    """
    
    def __init__(
        self,
        llm,
        context: Optional[ContextProtocol] = None,
        context_type: str = "memory",
        context_path: Optional[str] = None,
        versioned: bool = True,
        max_context_entries: int = 1000,
        max_context_versions: int = 50,
        auto_save: bool = True,
        context_window_tokens: int = 4000
    ):
        """
        Initialize a context-aware LLM.
        
        Args:
            llm: The language model to extend
            context: An existing context to use
            context_type: Type of context to use ('memory' or 'file')
            context_path: Path to store context (for file context)
            versioned: Whether to use versioned context
            max_context_entries: Maximum number of context entries
            max_context_versions: Maximum number of context versions
            auto_save: Whether to automatically save context
            context_window_tokens: Maximum number of tokens to include in context
        """
        self.llm = llm
        self.versioned = versioned
        self.context_window_tokens = context_window_tokens
        
        # Use provided context or create a new one
        if context:
            self.context = context
        else:
            # Create context
            if versioned:
                if context_type == "file" and context_path:
                    self.context = ContextManager.create_versioned_context(
                        context_type,
                        file_path=context_path,
                        max_entries=max_context_entries,
                        max_versions=max_context_versions,
                        auto_save=auto_save
                    )
                else:
                    self.context = ContextManager.create_versioned_context(
                        "memory",
                        max_entries=max_context_entries,
                        max_versions=max_context_versions
                    )
            else:
                if context_type == "file" and context_path:
                    self.context = ContextManager.create_context(
                        context_type,
                        file_path=context_path,
                        max_entries=max_context_entries,
                        auto_save=auto_save
                    )
                else:
                    self.context = ContextManager.create_context(
                        "memory",
                        max_entries=max_context_entries
                    )
    
    def add_to_context(
        self,
        content: str,
        source: str,
        entry_type: str,
        importance: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add an entry to the context.
        
        Args:
            content: The content of the entry
            source: The source of the entry
            entry_type: The type of entry
            importance: The importance of the entry
            metadata: Additional metadata
            
        Returns:
            The ID of the added entry
        """
        entry = ContextEntry(
            content=content,
            source=source,
            entry_type=entry_type,
            importance=importance,
            metadata=metadata
        )
        
        return self.context.add_entry(entry)
    
    def create_context_version(self, description: Optional[str] = None) -> Optional[str]:
        """
        Create a version of the current context.
        
        Args:
            description: Description of the version
            
        Returns:
            The ID of the created version, or None if versioning is not enabled
        """
        if not self.versioned or not isinstance(self.context, VersionedContextProtocol):
            return None
        
        return self.context.create_version(description)
    
    def get_context_for_prompt(
        self,
        include_types: Optional[List[str]] = None,
        exclude_types: Optional[List[str]] = None,
        include_sources: Optional[List[str]] = None,
        exclude_sources: Optional[List[str]] = None,
        min_importance: float = 0.0,
        format_template: Optional[str] = None
    ) -> str:
        """
        Get formatted context for use in a prompt.
        
        Args:
            include_types: Only include entries of these types
            exclude_types: Exclude entries of these types
            include_sources: Only include entries from these sources
            exclude_sources: Exclude entries from these sources
            min_importance: Only include entries with importance >= this value
            format_template: Template for formatting entries
            
        Returns:
            Formatted context string
        """
        return extract_context_for_llm(
            context=self.context,
            max_tokens=self.context_window_tokens,
            include_types=include_types,
            exclude_types=exclude_types,
            include_sources=include_sources,
            exclude_sources=exclude_sources,
            min_importance=min_importance,
            format_template=format_template
        )
    
    def generate(
        self,
        prompt: str,
        include_context: bool = True,
        context_prefix: str = "Context:\n",
        context_suffix: str = "\n\n",
        **kwargs
    ) -> str:
        """
        Generate text from a prompt, optionally including context.
        
        Args:
            prompt: The prompt to generate from
            include_context: Whether to include context
            context_prefix: Prefix to add before context
            context_suffix: Suffix to add after context
            **kwargs: Additional arguments to pass to the LLM
            
        Returns:
            Generated text
        """
        if include_context:
            # Get context
            context_str = self.get_context_for_prompt()
            
            # Add context to prompt if there is any
            if context_str:
                prompt = f"{context_prefix}{context_str}{context_suffix}{prompt}"
        
        # Generate text
        response = self.llm.generate(prompt, **kwargs)
        
        # Add the prompt and response to context
        self.add_to_context(
            content=prompt,
            source="user",
            entry_type="prompt"
        )
        
        self.add_to_context(
            content=response,
            source="llm",
            entry_type="response"
        )
        
        # Create a context version if versioning is enabled
        if self.versioned and isinstance(self.context, VersionedContextProtocol):
            self.create_context_version(f"After generating response to: {prompt[:50]}...")
        
        return response
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        include_context: bool = True,
        context_message_type: str = "system",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a chat response, optionally including context.
        
        Args:
            messages: The chat messages
            include_context: Whether to include context
            context_message_type: The type of message to use for context
            **kwargs: Additional arguments to pass to the LLM
            
        Returns:
            Chat response
        """
        if include_context:
            # Get context
            context_str = self.get_context_for_prompt()
            
            # Add context as a system message if there is any
            if context_str:
                context_message = {
                    "role": context_message_type,
                    "content": context_str
                }
                messages = [context_message] + messages
        
        # Generate response
        response = self.llm.chat(messages, **kwargs)
        
        # Add the messages and response to context
        for message in messages:
            self.add_to_context(
                content=message.get("content", ""),
                source=message.get("role", "user"),
                entry_type="message"
            )
        
        self.add_to_context(
            content=response.get("content", ""),
            source="llm",
            entry_type="message"
        )
        
        # Create a context version if versioning is enabled
        if self.versioned and isinstance(self.context, VersionedContextProtocol):
            self.create_context_version(f"After chat response to: {messages[-1].get('content', '')[:50]}...")
        
        return response
