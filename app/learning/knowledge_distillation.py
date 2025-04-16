"""
Knowledge Distillation System for Nexagent.

This module provides functionality for extracting generalizable knowledge
from specific experiences.
"""

import json
import time
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from collections import defaultdict

from pydantic import BaseModel, Field

from app.logger import logger
from app.learning.memory_store import MemoryStore, InteractionRecord, default_memory_store
from app.learning.analytics import PerformanceAnalytics, default_performance_analytics


class KnowledgeNode(BaseModel):
    """
    Represents a node in the knowledge graph.
    
    A knowledge node contains:
    1. A concept or entity
    2. Properties of the concept
    3. Relationships to other nodes
    """
    
    id: str
    type: str
    name: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class KnowledgeRelation(BaseModel):
    """
    Represents a relation between two nodes in the knowledge graph.
    
    A knowledge relation contains:
    1. The source node ID
    2. The target node ID
    3. The type of relation
    4. Properties of the relation
    """
    
    source_id: str
    target_id: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class KnowledgeTemplate(BaseModel):
    """
    Represents a reusable template extracted from successful interactions.
    
    A knowledge template contains:
    1. A pattern for matching similar tasks
    2. A solution template for solving the task
    3. Variables that can be substituted in the template
    4. Conditions for applying the template
    """
    
    id: str
    name: str
    description: str
    task_type: str
    pattern: str
    solution_template: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    conditions: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    success_count: int = 0
    usage_count: int = 0


class KnowledgeRule(BaseModel):
    """
    Represents a rule extracted from patterns in interactions.
    
    A knowledge rule contains:
    1. A condition for applying the rule
    2. An action to take when the condition is met
    3. A confidence score for the rule
    4. Examples of the rule in action
    """
    
    id: str
    name: str
    description: str
    condition: str
    action: str
    confidence: float = 0.0
    examples: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    success_count: int = 0
    usage_count: int = 0


class KnowledgeDistillation:
    """
    Extracts generalizable knowledge from specific experiences.
    
    This class provides functionality for:
    1. Building and maintaining a knowledge graph
    2. Extracting reusable templates from successful interactions
    3. Identifying patterns and rules from concrete examples
    4. Applying extracted knowledge to new situations
    """
    
    def __init__(
        self,
        memory_store: Optional[MemoryStore] = None,
        analytics: Optional[PerformanceAnalytics] = None
    ):
        """
        Initialize the knowledge distillation system.
        
        Args:
            memory_store: Optional memory store to use. If None, the default is used.
            analytics: Optional performance analytics to use. If None, the default is used.
        """
        self.memory_store = memory_store or default_memory_store
        self.analytics = analytics or default_performance_analytics
        
        # Knowledge graph
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.relations: List[KnowledgeRelation] = []
        
        # Templates and rules
        self.templates: Dict[str, KnowledgeTemplate] = {}
        self.rules: Dict[str, KnowledgeRule] = {}
    
    def extract_knowledge_from_interactions(
        self,
        task_type: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Extract knowledge from past interactions.
        
        Args:
            task_type: Optional task type to filter by
            limit: Maximum number of interactions to analyze
            
        Returns:
            Dictionary with extraction results
        """
        # Get successful interactions
        records = self.memory_store.search_interactions(
            task_type=task_type,
            success=True,
            limit=limit
        )
        
        if not records:
            return {
                "error": "No successful interactions found",
                "nodes_created": 0,
                "relations_created": 0,
                "templates_created": 0,
                "rules_created": 0
            }
        
        # Extract knowledge
        nodes_created = self._extract_nodes(records)
        relations_created = self._extract_relations(records)
        templates_created = self._extract_templates(records)
        rules_created = self._extract_rules(records)
        
        return {
            "interactions_analyzed": len(records),
            "nodes_created": nodes_created,
            "relations_created": relations_created,
            "templates_created": templates_created,
            "rules_created": rules_created
        }
    
    def _extract_nodes(self, records: List[InteractionRecord]) -> int:
        """
        Extract nodes from interaction records.
        
        Args:
            records: List of interaction records to analyze
            
        Returns:
            Number of nodes created
        """
        nodes_created = 0
        
        # Extract task types
        for record in records:
            if record.task_type:
                node_id = f"task_type:{record.task_type}"
                
                if node_id not in self.nodes:
                    self.nodes[node_id] = KnowledgeNode(
                        id=node_id,
                        type="task_type",
                        name=record.task_type,
                        properties={
                            "success_count": 1,
                            "first_seen": record.timestamp
                        }
                    )
                    nodes_created += 1
                else:
                    # Update existing node
                    node = self.nodes[node_id]
                    node.properties["success_count"] = node.properties.get("success_count", 0) + 1
                    node.updated_at = time.time()
        
        # Extract tools
        for record in records:
            for tool in record.tools_used:
                node_id = f"tool:{tool}"
                
                if node_id not in self.nodes:
                    self.nodes[node_id] = KnowledgeNode(
                        id=node_id,
                        type="tool",
                        name=tool,
                        properties={
                            "usage_count": 1,
                            "first_seen": record.timestamp
                        }
                    )
                    nodes_created += 1
                else:
                    # Update existing node
                    node = self.nodes[node_id]
                    node.properties["usage_count"] = node.properties.get("usage_count", 0) + 1
                    node.updated_at = time.time()
        
        # Extract keywords from prompts
        # This is a placeholder. In a real implementation, this would use
        # NLP techniques to extract keywords and entities.
        
        return nodes_created
    
    def _extract_relations(self, records: List[InteractionRecord]) -> int:
        """
        Extract relations from interaction records.
        
        Args:
            records: List of interaction records to analyze
            
        Returns:
            Number of relations created
        """
        relations_created = 0
        
        # Create relations between task types and tools
        task_type_tool_relations = set()
        
        for record in records:
            if record.task_type:
                for tool in record.tools_used:
                    relation_key = (f"task_type:{record.task_type}", f"tool:{tool}")
                    
                    if relation_key not in task_type_tool_relations:
                        self.relations.append(KnowledgeRelation(
                            source_id=relation_key[0],
                            target_id=relation_key[1],
                            type="uses",
                            properties={
                                "count": 1,
                                "first_seen": record.timestamp
                            }
                        ))
                        task_type_tool_relations.add(relation_key)
                        relations_created += 1
                    else:
                        # Update existing relation
                        for relation in self.relations:
                            if relation.source_id == relation_key[0] and relation.target_id == relation_key[1]:
                                relation.properties["count"] = relation.properties.get("count", 0) + 1
                                relation.updated_at = time.time()
                                break
        
        return relations_created
    
    def _extract_templates(self, records: List[InteractionRecord]) -> int:
        """
        Extract templates from interaction records.
        
        Args:
            records: List of interaction records to analyze
            
        Returns:
            Number of templates created
        """
        templates_created = 0
        
        # Group records by task type
        task_type_records = defaultdict(list)
        for record in records:
            if record.task_type:
                task_type_records[record.task_type].append(record)
        
        # Extract templates for each task type
        for task_type, task_records in task_type_records.items():
            # Skip if there are too few records
            if len(task_records) < 3:
                continue
            
            # Find common patterns in prompts
            # This is a placeholder. In a real implementation, this would use
            # more sophisticated NLP techniques to identify patterns.
            
            # For now, just create a simple template based on the most recent successful interaction
            recent_record = max(task_records, key=lambda r: r.timestamp)
            
            template_id = f"template:{task_type}_{int(time.time())}"
            
            if template_id not in self.templates:
                self.templates[template_id] = KnowledgeTemplate(
                    id=template_id,
                    name=f"Template for {task_type}",
                    description=f"Automatically generated template for {task_type} tasks",
                    task_type=task_type,
                    pattern=recent_record.user_prompt,
                    solution_template=recent_record.bot_response,
                    variables={},
                    conditions={
                        "task_type": task_type
                    },
                    success_count=1,
                    usage_count=1
                )
                templates_created += 1
        
        return templates_created
    
    def _extract_rules(self, records: List[InteractionRecord]) -> int:
        """
        Extract rules from interaction records.
        
        Args:
            records: List of interaction records to analyze
            
        Returns:
            Number of rules created
        """
        rules_created = 0
        
        # Extract tool usage patterns
        tool_patterns = defaultdict(int)
        
        for record in records:
            # Skip if no tools were used
            if not record.tools_used:
                continue
            
            # Create a pattern string from the tools used
            tools_str = ",".join(sorted(record.tools_used))
            tool_patterns[tools_str] += 1
        
        # Create rules for common tool patterns
        for pattern, count in tool_patterns.items():
            # Skip if the pattern is not common enough
            if count < 3:
                continue
            
            tools = pattern.split(",")
            
            rule_id = f"rule:tool_pattern_{pattern.replace(',', '_')}_{int(time.time())}"
            
            if rule_id not in self.rules:
                self.rules[rule_id] = KnowledgeRule(
                    id=rule_id,
                    name=f"Tool pattern: {pattern}",
                    description=f"When these tools are used together: {pattern}",
                    condition=f"task requires {' and '.join(tools)}",
                    action=f"Use tools in this order: {pattern}",
                    confidence=min(0.5 + (count / 10), 0.9),  # Confidence increases with count, max 0.9
                    examples=[],
                    success_count=count,
                    usage_count=count
                )
                rules_created += 1
        
        return rules_created
    
    def find_applicable_templates(
        self,
        prompt: str,
        task_type: Optional[str] = None
    ) -> List[KnowledgeTemplate]:
        """
        Find templates that are applicable to a given prompt.
        
        Args:
            prompt: The user prompt to find templates for
            task_type: Optional task type to filter by
            
        Returns:
            List of applicable templates
        """
        applicable_templates = []
        
        for template in self.templates.values():
            # Filter by task type if provided
            if task_type and template.task_type != task_type:
                continue
            
            # Check if the template is applicable
            # This is a placeholder. In a real implementation, this would use
            # more sophisticated matching techniques.
            if self._is_template_applicable(template, prompt):
                applicable_templates.append(template)
        
        # Sort by success rate (descending)
        applicable_templates.sort(
            key=lambda t: t.success_count / t.usage_count if t.usage_count > 0 else 0,
            reverse=True
        )
        
        return applicable_templates
    
    def _is_template_applicable(self, template: KnowledgeTemplate, prompt: str) -> bool:
        """
        Check if a template is applicable to a given prompt.
        
        Args:
            template: The template to check
            prompt: The user prompt to check against
            
        Returns:
            True if the template is applicable, False otherwise
        """
        # This is a placeholder. In a real implementation, this would use
        # more sophisticated matching techniques.
        
        # For now, just check if there are common words
        template_words = set(template.pattern.lower().split())
        prompt_words = set(prompt.lower().split())
        
        common_words = template_words.intersection(prompt_words)
        
        # If there are at least 3 common words, consider it applicable
        return len(common_words) >= 3
    
    def apply_template(
        self,
        template: KnowledgeTemplate,
        prompt: str
    ) -> str:
        """
        Apply a template to a given prompt.
        
        Args:
            template: The template to apply
            prompt: The user prompt to apply the template to
            
        Returns:
            The result of applying the template
        """
        # This is a placeholder. In a real implementation, this would use
        # more sophisticated template application techniques.
        
        # For now, just return the template's solution
        return template.solution_template
    
    def update_template_performance(
        self,
        template_id: str,
        success: bool
    ) -> None:
        """
        Update a template's performance metrics.
        
        Args:
            template_id: The ID of the template to update
            success: Whether the template was successful
        """
        if template_id in self.templates:
            template = self.templates[template_id]
            template.usage_count += 1
            if success:
                template.success_count += 1
            template.updated_at = time.time()
    
    def find_applicable_rules(
        self,
        task_type: Optional[str] = None,
        tools_used: Optional[List[str]] = None
    ) -> List[KnowledgeRule]:
        """
        Find rules that are applicable to a given context.
        
        Args:
            task_type: Optional task type to filter by
            tools_used: Optional list of tools used
            
        Returns:
            List of applicable rules
        """
        applicable_rules = []
        
        for rule in self.rules.values():
            # Check if the rule is applicable
            if self._is_rule_applicable(rule, task_type, tools_used):
                applicable_rules.append(rule)
        
        # Sort by confidence (descending)
        applicable_rules.sort(key=lambda r: r.confidence, reverse=True)
        
        return applicable_rules
    
    def _is_rule_applicable(
        self,
        rule: KnowledgeRule,
        task_type: Optional[str] = None,
        tools_used: Optional[List[str]] = None
    ) -> bool:
        """
        Check if a rule is applicable to a given context.
        
        Args:
            rule: The rule to check
            task_type: Optional task type to filter by
            tools_used: Optional list of tools used
            
        Returns:
            True if the rule is applicable, False otherwise
        """
        # This is a placeholder. In a real implementation, this would use
        # more sophisticated matching techniques.
        
        # For now, just check if the rule mentions the task type or tools
        if task_type and task_type.lower() in rule.condition.lower():
            return True
        
        if tools_used:
            for tool in tools_used:
                if tool.lower() in rule.condition.lower():
                    return True
        
        return False
    
    def update_rule_performance(
        self,
        rule_id: str,
        success: bool
    ) -> None:
        """
        Update a rule's performance metrics.
        
        Args:
            rule_id: The ID of the rule to update
            success: Whether the rule was successful
        """
        if rule_id in self.rules:
            rule = self.rules[rule_id]
            rule.usage_count += 1
            if success:
                rule.success_count += 1
            
            # Update confidence based on success rate
            if rule.usage_count > 0:
                rule.confidence = 0.5 + (0.5 * (rule.success_count / rule.usage_count))
            
            rule.updated_at = time.time()
    
    def get_knowledge_graph(self) -> Dict[str, Any]:
        """
        Get the knowledge graph.
        
        Returns:
            Dictionary with the knowledge graph
        """
        return {
            "nodes": [node.dict() for node in self.nodes.values()],
            "relations": [relation.dict() for relation in self.relations]
        }
    
    def get_templates(self) -> Dict[str, Any]:
        """
        Get all templates.
        
        Returns:
            Dictionary with templates
        """
        return {
            "templates": [template.dict() for template in self.templates.values()]
        }
    
    def get_rules(self) -> Dict[str, Any]:
        """
        Get all rules.
        
        Returns:
            Dictionary with rules
        """
        return {
            "rules": [rule.dict() for rule in self.rules.values()]
        }
    
    def save_knowledge(self, file_path: str) -> None:
        """
        Save knowledge to a file.
        
        Args:
            file_path: Path to save the knowledge to
        """
        try:
            knowledge = {
                "nodes": [node.dict() for node in self.nodes.values()],
                "relations": [relation.dict() for relation in self.relations],
                "templates": [template.dict() for template in self.templates.values()],
                "rules": [rule.dict() for rule in self.rules.values()]
            }
            
            with open(file_path, "w") as f:
                json.dump(knowledge, f, indent=2)
            
            logger.info(f"Saved knowledge to {file_path}")
        
        except Exception as e:
            logger.error(f"Error saving knowledge: {str(e)}")
    
    def load_knowledge(self, file_path: str) -> None:
        """
        Load knowledge from a file.
        
        Args:
            file_path: Path to load the knowledge from
        """
        try:
            with open(file_path, "r") as f:
                knowledge = json.load(f)
            
            # Load nodes
            self.nodes = {}
            for node_data in knowledge.get("nodes", []):
                node = KnowledgeNode(**node_data)
                self.nodes[node.id] = node
            
            # Load relations
            self.relations = []
            for relation_data in knowledge.get("relations", []):
                relation = KnowledgeRelation(**relation_data)
                self.relations.append(relation)
            
            # Load templates
            self.templates = {}
            for template_data in knowledge.get("templates", []):
                template = KnowledgeTemplate(**template_data)
                self.templates[template.id] = template
            
            # Load rules
            self.rules = {}
            for rule_data in knowledge.get("rules", []):
                rule = KnowledgeRule(**rule_data)
                self.rules[rule.id] = rule
            
            logger.info(f"Loaded knowledge from {file_path}")
        
        except Exception as e:
            logger.error(f"Error loading knowledge: {str(e)}")


# Create a default knowledge distillation instance
default_knowledge_distillation = KnowledgeDistillation()
