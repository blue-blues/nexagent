"""
Enhanced Planning Flow for Nexagent.

This module provides an advanced planning flow that coordinates the planning process
with validation, execution tracking, and progress reporting.
"""

import json
import time
from typing import Dict, Optional, Any
import asyncio

from pydantic import Field

from app.agent.enhanced_planning_agent import EnhancedPlanningAgent
from app.flow.planning import PlanningFlow
from app.logger import logger


class EnhancedPlanningFlow(PlanningFlow):
    """
    An enhanced flow for planning and executing complex tasks.

    This flow extends the base PlanningFlow with advanced capabilities:
    - Plan validation with user confirmation
    - Detailed progress tracking and reporting
    - Improved error handling and recovery
    """

    # Track validation and confirmation status
    plan_validated: bool = False
    plan_confirmed: bool = False

    # Track execution metrics
    execution_start_time: Optional[float] = None
    execution_metrics: Dict[str, Any] = Field(default_factory=dict)

    # Progress reporting settings
    progress_report_interval: int = 60  # seconds
    last_progress_report: float = 0

    async def execute(self, request: str) -> str:
        """
        Execute the enhanced planning flow.

        Args:
            request: The user's request to be planned and executed

        Returns:
            The execution result
        """
        try:
            # Initialize the planning agent if not already done
            if not self.primary_agent_key or self.primary_agent_key not in self.agents:
                logger.error("No primary planning agent configured")
                return "Error: No planning agent configured"

            planning_agent = self.agents[self.primary_agent_key]

            # Ensure the planning agent is an EnhancedPlanningAgent
            if not isinstance(planning_agent, EnhancedPlanningAgent):
                logger.error("Primary agent is not an EnhancedPlanningAgent")
                return "Error: Incompatible planning agent type"

            # Create the initial plan
            logger.info(f"Creating initial plan for request: {request[:50]}...")
            await planning_agent.create_initial_plan(request)

            # Validate the plan
            logger.info("Validating plan...")
            validation_result = await planning_agent.validate_plan()
            self.plan_validated = validation_result["overall"] == "PASS"

            # If validation failed, try to fix the plan
            if not self.plan_validated:
                logger.warning(f"Plan validation failed: {json.dumps(validation_result, indent=2)}")

                # Request plan improvement
                improvement_prompt = f"The plan validation failed. Please address these issues:\n{json.dumps(validation_result, indent=2)}"
                await planning_agent.run(improvement_prompt)

                # Re-validate the plan
                logger.info("Re-validating improved plan...")
                validation_result = await planning_agent.validate_plan()
                self.plan_validated = validation_result["overall"] == "PASS"

                if not self.plan_validated:
                    logger.error("Plan validation failed after improvement attempt")
                    return f"Error: Unable to create a valid plan. Issues: {json.dumps(validation_result, indent=2)}"

            # Plan is validated, start execution
            logger.info("Plan validated successfully, starting execution")
            self.execution_start_time = time.time()

            # Execute the plan
            result = await self._execute_plan(planning_agent)

            # Calculate execution metrics
            execution_time = time.time() - self.execution_start_time
            status = await planning_agent.get_execution_status()

            self.execution_metrics = {
                "total_execution_time": execution_time,
                "execution_status": status
            }

            # Include execution summary in the result
            summary = self._generate_execution_summary()
            return f"{result}\n\n{summary}"

        except Exception as e:
            logger.error(f"Error in EnhancedPlanningFlow: {str(e)}")
            return f"Execution failed: {str(e)}"

    async def _execute_plan(self, planning_agent: EnhancedPlanningAgent) -> str:
        """
        Execute the validated plan.

        Args:
            planning_agent: The planning agent with the validated plan

        Returns:
            The execution result
        """
        # Start progress reporting task
        progress_reporting_task = asyncio.create_task(self._report_progress(planning_agent))

        try:
            # Execute the plan with the planning agent
            result = await planning_agent.run()

            # Cancel progress reporting
            progress_reporting_task.cancel()

            return result
        except Exception as e:
            # Cancel progress reporting
            progress_reporting_task.cancel()

            logger.error(f"Error executing plan: {str(e)}")
            return f"Plan execution failed: {str(e)}"



    async def _finalize_plan(self, planning_agent: EnhancedPlanningAgent) -> str:
        """
        Finalize the plan execution.

        Args:
            planning_agent: The planning agent with the completed plan

        Returns:
            Finalization message
        """
        # Get execution status
        status = await planning_agent.get_execution_status()

        # Calculate execution metrics
        if self.execution_start_time:
            execution_time = time.time() - self.execution_start_time

            self.execution_metrics = {
                "total_execution_time": execution_time,
                "execution_status": status
            }

        return "Plan execution completed successfully."

    async def _report_progress(self, planning_agent: EnhancedPlanningAgent) -> None:
        """
        Periodically report execution progress.

        Args:
            planning_agent: The planning agent with the active plan
        """
        try:
            while True:
                # Wait for the reporting interval
                await asyncio.sleep(self.progress_report_interval)

                # Get current execution status
                status = await planning_agent.get_execution_status()

                # Log progress
                if "error" not in status:
                    progress = status.get("progress_percentage", 0)
                    completed = status.get("completed_steps", 0)
                    total = status.get("total_steps", 0)

                    logger.info(f"Plan execution progress: {progress:.1f}% ({completed}/{total} steps completed)")

                    # Update last report time
                    self.last_progress_report = time.time()
                else:
                    logger.warning(f"Failed to get execution status: {status.get('error')}")

        except asyncio.CancelledError:
            # Task was cancelled, exit gracefully
            pass
        except Exception as e:
            logger.error(f"Error in progress reporting: {str(e)}")

    def _generate_execution_summary(self) -> str:
        """
        Generate a summary of the plan execution.

        Returns:
            Formatted execution summary
        """
        if not self.execution_metrics:
            return "No execution metrics available."

        # Extract metrics
        execution_time = self.execution_metrics.get("total_execution_time", 0)
        status = self.execution_metrics.get("execution_status", {})

        # Format the summary
        summary = "EXECUTION SUMMARY:\n"
        summary += f"- Total execution time: {execution_time:.2f} seconds\n"

        if "error" not in status:
            progress = status.get("progress_percentage", 0)
            completed = status.get("completed_steps", 0)
            total = status.get("total_steps", 0)

            summary += f"- Steps completed: {completed}/{total} ({progress:.1f}%)\n"

            # Add validation information
            validation_result = status.get("validation_result", {})
            if validation_result:
                overall = validation_result.get("overall", "UNKNOWN")
                summary += f"- Plan validation: {overall}\n"
        else:
            summary += f"- Error: {status.get('error')}\n"

        return summary




async def main():
    # Create an enhanced planning agent
    planning_agent = EnhancedPlanningAgent()

    # Create the enhanced planning flow
    flow = EnhancedPlanningFlow(
        agents={"planning": planning_agent},
        primary_agent_key="planning"
    )

    # Execute the flow
    result = await flow.execute("Build a REST API for a weather app that fetches data from OpenWeatherMap API")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
