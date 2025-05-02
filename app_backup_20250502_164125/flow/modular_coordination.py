"""
Modular Coordination Flow for Nexagent.

This module provides a flow for coordinating multiple specialized agents
to solve complex tasks.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union, Set

from pydantic import Field, BaseModel

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow
from app.logger import logger
from app.timeline.timeline import Timeline
from app.timeline.events import create_system_event


class AgentRole(BaseModel):
    """
    Defines a role that an agent can play in the modular coordination flow.
    """
    
    name: str
    description: str
    required_capabilities: List[str] = Field(default_factory=list)
    optional_capabilities: List[str] = Field(default_factory=list)


class ModularCoordinationFlow(BaseFlow):
    """
    A flow for coordinating multiple specialized agents to solve complex tasks.
    
    This flow:
    1. Breaks down tasks into subtasks
    2. Assigns subtasks to specialized agents
    3. Coordinates communication between agents
    4. Aggregates results from multiple agents
    5. Handles dependencies between subtasks
    """
    
    # Roles that agents can play
    roles: Dict[str, AgentRole] = Field(default_factory=dict)
    
    # Agent assignments to roles
    role_assignments: Dict[str, str] = Field(default_factory=dict)
    
    # Task state
    tasks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    task_dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Communication channels between agents
    channels: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    
    # Execution state
    is_running: bool = Field(default=False)
    
    def __init__(self, agents: Dict[str, BaseAgent], **kwargs):
        """
        Initialize the modular coordination flow.
        
        Args:
            agents: Dictionary of agents to coordinate
            **kwargs: Additional keyword arguments
        """
        super().__init__(agents=agents, **kwargs)
        self._initialize_roles()
        self._assign_roles()
    
    def _initialize_roles(self):
        """Initialize the default roles for the flow."""
        self.roles = {
            "coordinator": AgentRole(
                name="coordinator",
                description="Coordinates the overall task execution and communication between agents",
                required_capabilities=["planning", "coordination"]
            ),
            "planner": AgentRole(
                name="planner",
                description="Creates and manages plans for solving complex tasks",
                required_capabilities=["planning"]
            ),
            "researcher": AgentRole(
                name="researcher",
                description="Gathers information from various sources",
                required_capabilities=["web_browsing", "information_extraction"]
            ),
            "coder": AgentRole(
                name="coder",
                description="Generates and reviews code",
                required_capabilities=["code_generation", "code_review"]
            ),
            "tester": AgentRole(
                name="tester",
                description="Tests code and verifies functionality",
                required_capabilities=["code_execution", "testing"]
            ),
            "documenter": AgentRole(
                name="documenter",
                description="Creates documentation for code and processes",
                required_capabilities=["documentation", "summarization"]
            )
        }
    
    def _assign_roles(self):
        """
        Assign agents to roles based on their capabilities.
        
        This method analyzes each agent's capabilities and assigns them to
        appropriate roles. If multiple agents can fill a role, the most
        specialized agent is chosen.
        """
        # Reset role assignments
        self.role_assignments = {}
        
        # Track agent capabilities
        agent_capabilities: Dict[str, Set[str]] = {}
        
        # Extract capabilities from agent descriptions and tools
        for agent_id, agent in self.agents.items():
            capabilities = set()
            
            # Extract capabilities from description
            if hasattr(agent, "description") and agent.description:
                description = agent.description.lower()
                
                # Check for common capabilities in the description
                capability_keywords = {
                    "planning": ["planning", "planner", "plan", "organize"],
                    "coordination": ["coordination", "coordinate", "orchestrate"],
                    "web_browsing": ["web", "browser", "internet", "search"],
                    "information_extraction": ["extract", "information", "data", "research"],
                    "code_generation": ["code", "generate", "programming", "development"],
                    "code_review": ["review", "analyze", "code", "quality"],
                    "code_execution": ["execute", "run", "test", "code"],
                    "testing": ["test", "verify", "validate", "quality"],
                    "documentation": ["document", "documentation", "explain"],
                    "summarization": ["summarize", "summary", "condense"]
                }
                
                for capability, keywords in capability_keywords.items():
                    if any(keyword in description for keyword in keywords):
                        capabilities.add(capability)
            
            # Extract capabilities from available tools
            if hasattr(agent, "available_tools") and agent.available_tools:
                tool_capability_map = {
                    "web_search": "web_browsing",
                    "enhanced_browser": "web_browsing",
                    "keyword_extraction": "information_extraction",
                    "code_generation": "code_generation",
                    "code_analyzer": "code_review",
                    "python_execute": "code_execution",
                    "planning": "planning"
                }
                
                for tool_name in agent.available_tools.tool_map.keys():
                    if tool_name in tool_capability_map:
                        capabilities.add(tool_capability_map[tool_name])
            
            agent_capabilities[agent_id] = capabilities
        
        # Assign agents to roles
        for role_id, role in self.roles.items():
            # Find agents that have all required capabilities
            qualified_agents = []
            
            for agent_id, capabilities in agent_capabilities.items():
                if all(cap in capabilities for cap in role.required_capabilities):
                    # Calculate how specialized the agent is for this role
                    specialization_score = sum(1 for cap in capabilities if cap in role.required_capabilities or cap in role.optional_capabilities)
                    qualified_agents.append((agent_id, specialization_score))
            
            # Sort by specialization score (descending)
            qualified_agents.sort(key=lambda x: x[1], reverse=True)
            
            # Assign the most specialized agent to the role
            if qualified_agents:
                self.role_assignments[role_id] = qualified_agents[0][0]
    
    async def execute(self, prompt: str, timeline: Optional[Timeline] = None) -> str:
        """
        Execute the modular coordination flow.
        
        Args:
            prompt: The user's input prompt
            timeline: Optional timeline for tracking events
            
        Returns:
            The result of the flow execution
        """
        # Create a timeline if not provided
        if timeline is None:
            timeline = Timeline()
        
        # Create a system event for the flow execution
        flow_event = create_system_event(
            timeline,
            "Modular Coordination Flow",
            f"Executing modular coordination flow for prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
        )
        
        try:
            # Mark the flow as running
            self.is_running = True
            
            # Break down the task
            task_breakdown_event = create_system_event(
                timeline,
                "Task Breakdown",
                "Breaking down the task into subtasks"
            )
            
            subtasks = await self._break_down_task(prompt, timeline)
            
            task_breakdown_event.mark_success({
                "subtasks": [task["title"] for task in subtasks]
            })
            
            # Create tasks from the breakdown
            for subtask in subtasks:
                task_id = f"task_{int(time.time())}_{len(self.tasks)}"
                self.tasks[task_id] = {
                    "id": task_id,
                    "title": subtask["title"],
                    "description": subtask["description"],
                    "role": subtask["role"],
                    "status": "pending",
                    "result": None,
                    "created_at": time.time()
                }
                
                # Add dependencies if specified
                if "dependencies" in subtask:
                    self.task_dependencies[task_id] = subtask["dependencies"]
            
            # Execute tasks in dependency order
            execution_event = create_system_event(
                timeline,
                "Task Execution",
                "Executing tasks in dependency order"
            )
            
            results = await self._execute_tasks(timeline)
            
            execution_event.mark_success({
                "completed_tasks": len(results)
            })
            
            # Aggregate results
            aggregation_event = create_system_event(
                timeline,
                "Result Aggregation",
                "Aggregating results from all tasks"
            )
            
            final_result = await self._aggregate_results(results, prompt, timeline)
            
            aggregation_event.mark_success({
                "result_length": len(final_result)
            })
            
            # Mark the flow as completed
            self.is_running = False
            flow_event.mark_success({
                "success": True,
                "task_count": len(self.tasks)
            })
            
            return final_result
        
        except Exception as e:
            logger.error(f"Error in ModularCoordinationFlow.execute: {str(e)}")
            
            # Mark the flow as not running
            self.is_running = False
            
            # Mark the flow event as failed
            flow_event.mark_error({
                "error": str(e)
            })
            
            return f"Error executing modular coordination flow: {str(e)}"
    
    async def _break_down_task(self, prompt: str, timeline: Timeline) -> List[Dict[str, Any]]:
        """
        Break down a task into subtasks.
        
        Args:
            prompt: The user's input prompt
            timeline: Timeline for tracking events
            
        Returns:
            List of subtasks
        """
        # Get the coordinator agent
        coordinator_id = self.role_assignments.get("coordinator")
        if not coordinator_id:
            coordinator_id = self.role_assignments.get("planner")
        
        if not coordinator_id:
            # If no coordinator or planner is assigned, use the first agent
            coordinator_id = next(iter(self.agents.keys()))
        
        coordinator = self.agents[coordinator_id]
        
        # Create a breakdown prompt
        breakdown_prompt = f"""
        Break down the following task into subtasks:
        
        {prompt}
        
        For each subtask, provide:
        1. A title
        2. A detailed description
        3. The role that should handle it (one of: {', '.join(self.roles.keys())})
        4. Dependencies on other subtasks (if any)
        
        Format your response as a JSON array of subtask objects.
        """
        
        # Add the prompt to the coordinator's memory
        coordinator.update_memory("user", breakdown_prompt)
        
        # Get the breakdown from the coordinator
        response = await coordinator.llm.ask(
            messages=coordinator.memory.get_messages(),
            system_msgs=[{"role": "system", "content": coordinator.system_prompt}]
        )
        
        # Extract the JSON array from the response
        try:
            # Look for JSON array in the response
            json_start = response.content.find("[")
            json_end = response.content.rfind("]") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response.content[json_start:json_end]
                subtasks = json.loads(json_str)
            else:
                # If no JSON array is found, try to parse the entire response
                subtasks = json.loads(response.content)
            
            # Validate the subtasks
            validated_subtasks = []
            for subtask in subtasks:
                if "title" in subtask and "description" in subtask and "role" in subtask:
                    # Ensure the role is valid
                    if subtask["role"] in self.roles:
                        validated_subtasks.append(subtask)
            
            return validated_subtasks
        
        except Exception as e:
            logger.error(f"Error parsing subtasks: {str(e)}")
            
            # Create a default subtask if parsing fails
            return [
                {
                    "title": "Execute the task",
                    "description": prompt,
                    "role": "coordinator"
                }
            ]
    
    async def _execute_tasks(self, timeline: Timeline) -> List[Dict[str, Any]]:
        """
        Execute tasks in dependency order.
        
        Args:
            timeline: Timeline for tracking events
            
        Returns:
            List of task results
        """
        # Build dependency graph
        dependency_graph = {}
        for task_id, task in self.tasks.items():
            dependency_graph[task_id] = self.task_dependencies.get(task_id, [])
        
        # Find tasks with no dependencies
        no_dependencies = [task_id for task_id, deps in dependency_graph.items() if not deps]
        
        # Execute tasks in dependency order
        results = []
        executed_tasks = set()
        
        while no_dependencies:
            # Execute tasks with no dependencies in parallel
            tasks_to_execute = []
            
            for task_id in no_dependencies:
                if task_id not in executed_tasks:
                    tasks_to_execute.append(self._execute_task(task_id, timeline))
                    executed_tasks.add(task_id)
            
            # Wait for all tasks to complete
            task_results = await asyncio.gather(*tasks_to_execute)
            results.extend(task_results)
            
            # Update no_dependencies list
            no_dependencies = []
            for task_id, deps in dependency_graph.items():
                if task_id not in executed_tasks and all(dep in executed_tasks for dep in deps):
                    no_dependencies.append(task_id)
        
        return results
    
    async def _execute_task(self, task_id: str, timeline: Timeline) -> Dict[str, Any]:
        """
        Execute a single task.
        
        Args:
            task_id: ID of the task to execute
            timeline: Timeline for tracking events
            
        Returns:
            Task result
        """
        task = self.tasks[task_id]
        
        # Create a task event
        task_event = create_system_event(
            timeline,
            f"Task: {task['title']}",
            f"Executing task: {task['title']}"
        )
        
        try:
            # Update task status
            task["status"] = "in_progress"
            task["started_at"] = time.time()
            
            # Get the agent for the task's role
            agent_id = self.role_assignments.get(task["role"])
            if not agent_id:
                # If no agent is assigned to the role, use the coordinator
                agent_id = self.role_assignments.get("coordinator")
                if not agent_id:
                    # If no coordinator is assigned, use the first agent
                    agent_id = next(iter(self.agents.keys()))
            
            agent = self.agents[agent_id]
            
            # Create a task prompt
            task_prompt = f"""
            Execute the following task:
            
            Title: {task['title']}
            Description: {task['description']}
            
            Your role: {task['role']}
            
            Please provide a detailed response that completes this task.
            """
            
            # Add the prompt to the agent's memory
            agent.update_memory("user", task_prompt)
            
            # Get dependencies if any
            dependencies = self.task_dependencies.get(task_id, [])
            if dependencies:
                dependency_info = "This task depends on the following tasks:\n\n"
                
                for dep_id in dependencies:
                    if dep_id in self.tasks:
                        dep_task = self.tasks[dep_id]
                        dependency_info += f"- {dep_task['title']}: {dep_task['result']}\n\n"
                
                agent.update_memory("system", dependency_info)
            
            # Execute the task
            response = await agent.llm.ask(
                messages=agent.memory.get_messages(),
                system_msgs=[{"role": "system", "content": agent.system_prompt}]
            )
            
            # Update task status and result
            task["status"] = "completed"
            task["completed_at"] = time.time()
            task["result"] = response.content
            
            # Mark the task event as successful
            task_event.mark_success({
                "agent": agent_id,
                "role": task["role"],
                "execution_time": task["completed_at"] - task["started_at"]
            })
            
            return {
                "task_id": task_id,
                "title": task["title"],
                "role": task["role"],
                "result": task["result"]
            }
        
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {str(e)}")
            
            # Update task status
            task["status"] = "failed"
            task["error"] = str(e)
            
            # Mark the task event as failed
            task_event.mark_error({
                "error": str(e)
            })
            
            return {
                "task_id": task_id,
                "title": task["title"],
                "role": task["role"],
                "result": f"Error: {str(e)}",
                "error": str(e)
            }
    
    async def _aggregate_results(self, results: List[Dict[str, Any]], original_prompt: str, timeline: Timeline) -> str:
        """
        Aggregate results from multiple tasks.
        
        Args:
            results: List of task results
            original_prompt: The original user prompt
            timeline: Timeline for tracking events
            
        Returns:
            Aggregated result
        """
        # Get the coordinator agent
        coordinator_id = self.role_assignments.get("coordinator")
        if not coordinator_id:
            coordinator_id = self.role_assignments.get("planner")
        
        if not coordinator_id:
            # If no coordinator or planner is assigned, use the first agent
            coordinator_id = next(iter(self.agents.keys()))
        
        coordinator = self.agents[coordinator_id]
        
        # Create an aggregation prompt
        aggregation_prompt = f"""
        Aggregate the results from the following tasks to provide a comprehensive response to the original prompt:
        
        Original Prompt: {original_prompt}
        
        Task Results:
        """
        
        for result in results:
            aggregation_prompt += f"\n\n## {result['title']} (Role: {result['role']})\n{result['result']}"
        
        # Add the prompt to the coordinator's memory
        coordinator.update_memory("user", aggregation_prompt)
        
        # Get the aggregated result from the coordinator
        response = await coordinator.llm.ask(
            messages=coordinator.memory.get_messages(),
            system_msgs=[{"role": "system", "content": coordinator.system_prompt}]
        )
        
        return response.content
    
    def get_agent_for_role(self, role: str) -> Optional[BaseAgent]:
        """
        Get the agent assigned to a specific role.
        
        Args:
            role: The role to get the agent for
            
        Returns:
            The agent assigned to the role, or None if no agent is assigned
        """
        agent_id = self.role_assignments.get(role)
        if agent_id:
            return self.agents.get(agent_id)
        return None
    
    def get_role_for_agent(self, agent_id: str) -> Optional[str]:
        """
        Get the role assigned to a specific agent.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            The role assigned to the agent, or None if the agent is not assigned to any role
        """
        for role, assigned_agent_id in self.role_assignments.items():
            if assigned_agent_id == agent_id:
                return role
        return None
