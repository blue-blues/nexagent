"""
Context-Aware Planning Module

This module provides planning capabilities that are aware of context.
It extends the base planning module with context management.
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


class ContextAwarePlanner:
    """
    A planner that is aware of context.
    This class can be used to extend any planner with context management capabilities.
    """
    
    def __init__(
        self,
        planner,
        context: Optional[ContextProtocol] = None,
        context_type: str = "memory",
        context_path: Optional[str] = None,
        versioned: bool = True,
        max_context_entries: int = 1000,
        max_context_versions: int = 50,
        auto_save: bool = True
    ):
        """
        Initialize a context-aware planner.
        
        Args:
            planner: The planner to extend
            context: An existing context to use
            context_type: Type of context to use ('memory' or 'file')
            context_path: Path to store context (for file context)
            versioned: Whether to use versioned context
            max_context_entries: Maximum number of context entries
            max_context_versions: Maximum number of context versions
            auto_save: Whether to automatically save context
        """
        self.planner = planner
        self.versioned = versioned
        
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
    
    def get_context_for_planning(
        self,
        max_tokens: Optional[int] = None,
        include_types: Optional[List[str]] = None,
        exclude_types: Optional[List[str]] = None,
        include_sources: Optional[List[str]] = None,
        exclude_sources: Optional[List[str]] = None,
        min_importance: float = 0.0,
        format_template: Optional[str] = None
    ) -> str:
        """
        Get formatted context for use in planning.
        
        Args:
            max_tokens: Maximum number of tokens to include
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
            max_tokens=max_tokens,
            include_types=include_types,
            exclude_types=exclude_types,
            include_sources=include_sources,
            exclude_sources=exclude_sources,
            min_importance=min_importance,
            format_template=format_template
        )
    
    def create_plan(
        self,
        goal: str,
        include_context: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a plan for a goal, optionally including context.
        
        Args:
            goal: The goal to plan for
            include_context: Whether to include context
            **kwargs: Additional arguments to pass to the planner
            
        Returns:
            The created plan
        """
        if include_context:
            # Get context
            context_str = self.get_context_for_planning(
                include_types=["plan", "task", "goal", "message"],
                min_importance=0.5
            )
            
            # Add context to kwargs
            kwargs["context"] = context_str
        
        # Create plan
        plan = self.planner.create_plan(goal, **kwargs)
        
        # Add the plan to context
        self.add_to_context(
            content=json.dumps(plan, indent=2),
            source="planner",
            entry_type="plan",
            importance=1.5,
            metadata={"goal": goal}
        )
        
        # Create a context version if versioning is enabled
        if self.versioned and isinstance(self.context, VersionedContextProtocol):
            self.create_context_version(f"After creating plan for: {goal[:50]}...")
        
        return plan
    
    def update_plan(
        self,
        plan_id: str,
        updates: Dict[str, Any],
        include_context: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a plan, optionally including context.
        
        Args:
            plan_id: The ID of the plan to update
            updates: The updates to apply
            include_context: Whether to include context
            **kwargs: Additional arguments to pass to the planner
            
        Returns:
            The updated plan
        """
        if include_context:
            # Get context
            context_str = self.get_context_for_planning(
                include_types=["plan", "task", "goal", "message"],
                min_importance=0.5
            )
            
            # Add context to kwargs
            kwargs["context"] = context_str
        
        # Update plan
        updated_plan = self.planner.update_plan(plan_id, updates, **kwargs)
        
        # Add the updated plan to context
        self.add_to_context(
            content=json.dumps(updated_plan, indent=2),
            source="planner",
            entry_type="plan",
            importance=1.5,
            metadata={"plan_id": plan_id, "update_type": "update"}
        )
        
        # Create a context version if versioning is enabled
        if self.versioned and isinstance(self.context, VersionedContextProtocol):
            self.create_context_version(f"After updating plan: {plan_id}")
        
        return updated_plan
    
    def execute_plan(
        self,
        plan_id: str,
        include_context: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a plan, optionally including context.
        
        Args:
            plan_id: The ID of the plan to execute
            include_context: Whether to include context
            **kwargs: Additional arguments to pass to the planner
            
        Returns:
            The execution results
        """
        if include_context:
            # Get context
            context_str = self.get_context_for_planning(
                include_types=["plan", "task", "goal", "message", "result"],
                min_importance=0.5
            )
            
            # Add context to kwargs
            kwargs["context"] = context_str
        
        # Execute plan
        results = self.planner.execute_plan(plan_id, **kwargs)
        
        # Add the execution results to context
        self.add_to_context(
            content=json.dumps(results, indent=2),
            source="planner",
            entry_type="result",
            importance=1.5,
            metadata={"plan_id": plan_id}
        )
        
        # Create a context version if versioning is enabled
        if self.versioned and isinstance(self.context, VersionedContextProtocol):
            self.create_context_version(f"After executing plan: {plan_id}")
        
        return results
    
    def get_plan_history(self, plan_id: str) -> List[Dict[str, Any]]:
        """
        Get the history of a plan from context.
        
        Args:
            plan_id: The ID of the plan
            
        Returns:
            The plan history
        """
        # Get all plan entries
        plan_entries = self.context.get_entries_by_type("plan")
        
        # Filter by plan ID
        plan_history = [
            {
                "entry_id": entry.entry_id,
                "timestamp": entry.timestamp.isoformat(),
                "content": json.loads(entry.content) if entry.content else {},
                "metadata": entry.metadata
            }
            for entry in plan_entries
            if entry.metadata.get("plan_id") == plan_id
        ]
        
        # Sort by timestamp
        plan_history.sort(key=lambda entry: entry["timestamp"])
        
        return plan_history
