"""
Context Module

This module provides context management for Nexagent.
It defines protocols and implementations for storing, retrieving, and
manipulating context information that is passed to language models.
"""

from app.core.context.protocol import (
    ContextEntry,
    ContextProtocol,
    ContextVersion,
    VersionedContextProtocol,
    ContextManager
)
from app.core.context.memory import MemoryContext
from app.core.context.file import FileContext
from app.core.context.versioned_memory import VersionedMemoryContext
from app.core.context.versioned_file import VersionedFileContext
from app.core.context.utils import (
    extract_context_for_llm,
    merge_contexts,
    create_context_snapshot,
    filter_context_by_date,
    create_entry_from_message
)

__all__ = [
    'ContextEntry',
    'ContextProtocol',
    'ContextVersion',
    'VersionedContextProtocol',
    'ContextManager',
    'MemoryContext',
    'FileContext',
    'VersionedMemoryContext',
    'VersionedFileContext',
    'extract_context_for_llm',
    'merge_contexts',
    'create_context_snapshot',
    'filter_context_by_date',
    'create_entry_from_message'
]
