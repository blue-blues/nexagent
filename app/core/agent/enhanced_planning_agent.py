"""
Enhanced Planning Agent for Nexagent.

This module provides an advanced planning agent that creates detailed, structured plans
with validation steps and incorporates few-shot examples for consistent output formatting.
"""

import json
import time
from typing import Dict, Optional, Any
import uuid

from pydantic import Field, model_validator

from app.agent.planning import PlanningAgent
from app.prompt.enhanced_planning import (
    ENHANCED_PLANNING_SYSTEM_PROMPT,
    ENHANCED_PLANNING_NEXT_STEP_PROMPT,
    PLAN_CREATION_EXAMPLES,
    PLAN_VALIDATION_PROMPT
)
from app.schema import Message, ToolChoice
from app.tool import ToolCollection
from app.tool.planning import PlanningTool
from app.tool.terminate import Terminate
from app.tool.input_parser import InputParser
from app.logger import logger


class EnhancedPlanningAgent(PlanningAgent):
    """
    An advanced agent that creates and manages detailed, structured plans.

    This agent extends the base PlanningAgent with enhanced capabilities:
    - Structured plan generation with validation steps
    - Few-shot example integration for consistent output
    - Plan validation with user confirmation
    - Detailed metadata and step typing
    """

    name: str = "enhanced_planning"
    description: str = "An advanced agent that creates and manages detailed, structured plans"

    system_prompt: str = ENHANCED_PLANNING_SYSTEM_PROMPT
    next_step_prompt: str = ENHANCED_PLANNING_NEXT_STEP_PROMPT

    # Track the original request for validation
    original_request: Optional[str] = None

    # Track plan validation status
    plan_validated: bool = False
    validation_result: Optional[Dict[str, Any]] = None

    # Track plan execution progress
    current_step_index: Optional[int] = None
    execution_status: Dict[str, Any] = Field(default_factory=dict)

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PlanningTool(),
            InputParser(),
            Terminate()
        )
    )

    @model_validator(mode="after")
    def initialize_plan_and_verify_tools(self) -> "EnhancedPlanningAgent":
        """Initialize the agent with a default plan ID and validate required tools."""
        self.active_plan_id = f"plan_{uuid.uuid4().hex[:8]}_{int(time.time())}"

        # Ensure required tools are available
        if "planning" not in self.available_tools.tool_map:
            self.available_tools.add_tool(PlanningTool())

        if "input_parser" not in self.available_tools.tool_map:
            self.available_tools.add_tool(InputParser())

        return self

    async def think(self) -> bool:
        """Decide the next action based on plan status and validation."""
        # Include few-shot examples in the system prompt for the first thinking step
        if self.current_step == 1 and self.original_request:
            enhanced_system_prompt = f"{self.system_prompt}\n\nFEW-SHOT EXAMPLES:\n{PLAN_CREATION_EXAMPLES}"
            self.messages.append(Message.system_message(enhanced_system_prompt))

        # Include plan validation results if available
        validation_info = ""
        if self.validation_result:
            validation_info = f"\nPLAN VALIDATION RESULTS:\n{json.dumps(self.validation_result, indent=2)}\n"

        # Get current plan status
        plan_status = await self.get_plan()

        # Construct the thinking prompt
        prompt = f"CURRENT PLAN STATUS:\n{plan_status}\n{validation_info}\n{self.next_step_prompt}"
        self.messages.append(Message.user_message(prompt))

        # Get the current step index before thinking
        self.current_step_index = await self._get_current_step_index()

        # Call the parent think method
        result = await super().think()
        return result

    async def create_initial_plan(self, request: str) -> None:
        """Create an initial plan based on the request with enhanced parsing."""
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")
        self.original_request = request

        # First, parse the request to extract structured information
        parse_result = await self.available_tools.execute(
            name="input_parser",
            tool_input={"command": "parse", "text": request}
        )

        parsed_info = {}
        if hasattr(parse_result, "output"):
            try:
                parsed_info = json.loads(parse_result.output)
                logger.info(f"Parsed request information: {json.dumps(parsed_info, indent=2)}")
            except json.JSONDecodeError:
                logger.error("Failed to parse input parser output as JSON")

        # Construct a more detailed prompt with the parsed information
        parsed_info_str = json.dumps(parsed_info, indent=2) if parsed_info else "No structured information extracted"

        plan_prompt = f"""
        Analyze the following request and create a detailed plan with ID {self.active_plan_id}:

        ORIGINAL REQUEST:
        {request}

        PARSED INFORMATION:
        {parsed_info_str}

        Create a comprehensive plan that addresses all requirements and constraints.
        """

        messages = [Message.user_message(plan_prompt)]
        self.memory.add_messages(messages)

        # Include few-shot examples in the system prompt
        system_prompt = f"{self.system_prompt}\n\nFEW-SHOT EXAMPLES:\n{PLAN_CREATION_EXAMPLES}"

        response = await self.llm.ask_tool(
            messages=messages,
            system_msgs=[Message.system_message(system_prompt)],
            tools=self.available_tools.to_params(),
            tool_choice=ToolChoice.AUTO,
        )
        assistant_msg = Message.from_tool_calls(
            content=response.content, tool_calls=response.tool_calls
        )

        self.memory.add_message(assistant_msg)

        plan_created = False
        for tool_call in response.tool_calls:
            if tool_call.function.name == "planning":
                result = await self.execute_tool(tool_call)
                logger.info(
                    f"Executed tool {tool_call.function.name} with result: {result}"
                )

                # Add tool response to memory
                tool_msg = Message.tool_message(
                    content=result,
                    tool_call_id=tool_call.id,
                    name=tool_call.function.name,
                )
                self.memory.add_message(tool_msg)
                plan_created = True
                break

        if not plan_created:
            logger.warning("No plan created from initial request")
            tool_msg = Message.assistant_message(
                "Error: Failed to create plan from the request"
            )
            self.memory.add_message(tool_msg)

    async def validate_plan(self) -> Dict[str, Any]:
        """Validate the current plan against the original request."""
        if not self.original_request:
            return {"error": "No original request available for validation"}

        plan = await self.get_plan()

        # Construct validation prompt
        validation_prompt = PLAN_VALIDATION_PROMPT.format(
            request=self.original_request,
            plan=plan
        )

        # Use LLM to validate the plan
        messages = [Message.user_message(validation_prompt)]
        response = await self.llm.create_chat_completion(messages=messages)

        # Parse validation results
        validation_text = response.content

        # Extract validation results
        validation_result = {
            "overall": "FAIL",  # Default to fail
            "categories": {},
            "suggestions": []
        }

        # Parse the validation results
        if "VALIDATION RESULTS:" in validation_text:
            results_section = validation_text.split("VALIDATION RESULTS:")[1].split("Suggested Improvements:")[0]

            # Extract category results
            categories = ["Completeness", "Logical Flow", "Actionability", "Feasibility", "Clarity"]
            for category in categories:
                if f"{category}:" in results_section:
                    category_line = [line for line in results_section.split("\n") if f"{category}:" in line][0]
                    if "PASS" in category_line:
                        validation_result["categories"][category.lower()] = "PASS"
                    else:
                        validation_result["categories"][category.lower()] = "FAIL"

            # Extract overall result
            if "Overall:" in validation_text:
                overall_line = validation_text.split("Overall:")[1].split("\n")[0].strip()
                validation_result["overall"] = "PASS" if "PASS" in overall_line else "FAIL"

            # Extract suggestions
            if "Suggested Improvements:" in validation_text:
                suggestions_section = validation_text.split("Suggested Improvements:")[1]
                suggestions = []
                for line in suggestions_section.split("\n"):
                    if line.strip() and line.strip()[0].isdigit() and "." in line:
                        suggestion = line.split(".", 1)[1].strip()
                        suggestions.append(suggestion)
                validation_result["suggestions"] = suggestions

        # Store validation result
        self.validation_result = validation_result
        self.plan_validated = validation_result["overall"] == "PASS"

        return validation_result

    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with an optional initial request."""
        if request:
            self.original_request = request
            await self.create_initial_plan(request)

            # Validate the plan after creation
            validation_result = await self.validate_plan()

            # If plan validation failed, log the issues
            if validation_result["overall"] == "FAIL":
                logger.warning(f"Plan validation failed: {json.dumps(validation_result, indent=2)}")

                # Add validation result to memory
                validation_msg = Message.user_message(
                    f"Plan validation failed. Please address these issues:\n{json.dumps(validation_result, indent=2)}"
                )
                self.memory.add_message(validation_msg)

        return await super().run()

    async def get_execution_status(self) -> Dict[str, Any]:
        """Get the current execution status of the plan."""
        if not self.active_plan_id:
            return {"error": "No active plan"}

        plan_result = await self.available_tools.execute(
            name="planning",
            tool_input={"command": "get", "plan_id": self.active_plan_id},
        )

        if hasattr(plan_result, "error"):
            return {"error": plan_result.error}

        try:
            plan_data = json.loads(plan_result.output)

            # Calculate progress statistics
            total_steps = len(plan_data.get("steps", []))
            completed_steps = sum(1 for step in plan_data.get("steps", [])
                               if step.get("status") == "completed")
            in_progress_steps = sum(1 for step in plan_data.get("steps", [])
                                 if step.get("status") == "in_progress")

            progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0

            status = {
                "plan_id": self.active_plan_id,
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "in_progress_steps": in_progress_steps,
                "pending_steps": total_steps - completed_steps - in_progress_steps,
                "progress_percentage": progress_percentage,
                "current_step_index": self.current_step_index,
                "plan_validated": self.plan_validated,
                "validation_result": self.validation_result
            }

            return status

        except (json.JSONDecodeError, AttributeError) as e:
            return {"error": f"Failed to parse plan data: {str(e)}"}




async def main():
    # Configure and run the agent
    agent = EnhancedPlanningAgent()
    result = await agent.run("Build a REST API for a weather app that fetches data from OpenWeatherMap API")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
