"""
Feedback Integration Loop for Nexagent.

This module provides functionality for incorporating explicit and implicit
user feedback to guide learning.
"""

import json
import time
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field

from app.logger import logger
from app.learning.memory_store import MemoryStore, InteractionRecord, default_memory_store
from app.learning.analytics import PerformanceAnalytics, default_performance_analytics
from app.learning.strategy_adaptation import StrategyAdaptation, default_strategy_adaptation
from app.learning.knowledge_distillation import KnowledgeDistillation, default_knowledge_distillation


class FeedbackType(str, Enum):
    """Types of feedback."""
    
    EXPLICIT_POSITIVE = "explicit_positive"
    EXPLICIT_NEGATIVE = "explicit_negative"
    EXPLICIT_NEUTRAL = "explicit_neutral"
    IMPLICIT_CORRECTION = "implicit_correction"
    IMPLICIT_REPETITION = "implicit_repetition"
    IMPLICIT_ABANDONMENT = "implicit_abandonment"
    IMPLICIT_CONTINUATION = "implicit_continuation"


class FeedbackRecord(BaseModel):
    """
    Represents a feedback record.
    
    A feedback record contains:
    1. The type of feedback
    2. The interaction ID the feedback is for
    3. The feedback content
    4. Metadata about the feedback
    """
    
    id: str = Field(default_factory=lambda: f"feedback_{int(time.time())}_{id(object())}")
    interaction_id: str
    feedback_type: FeedbackType
    content: str
    rating: Optional[int] = None
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FeedbackIntegration:
    """
    Incorporates explicit and implicit user feedback to guide learning.
    
    This class provides functionality for:
    1. Collecting and storing user feedback
    2. Analyzing feedback patterns
    3. Prioritizing improvements based on feedback
    4. Adjusting learning based on feedback importance
    """
    
    def __init__(
        self,
        memory_store: Optional[MemoryStore] = None,
        analytics: Optional[PerformanceAnalytics] = None,
        strategy_adaptation: Optional[StrategyAdaptation] = None,
        knowledge_distillation: Optional[KnowledgeDistillation] = None
    ):
        """
        Initialize the feedback integration loop.
        
        Args:
            memory_store: Optional memory store to use. If None, the default is used.
            analytics: Optional performance analytics to use. If None, the default is used.
            strategy_adaptation: Optional strategy adaptation to use. If None, the default is used.
            knowledge_distillation: Optional knowledge distillation to use. If None, the default is used.
        """
        self.memory_store = memory_store or default_memory_store
        self.analytics = analytics or default_performance_analytics
        self.strategy_adaptation = strategy_adaptation or default_strategy_adaptation
        self.knowledge_distillation = knowledge_distillation or default_knowledge_distillation
        
        # Feedback storage
        self.feedback_records: Dict[str, FeedbackRecord] = {}
        
        # Feedback statistics
        self.feedback_stats: Dict[str, Any] = {
            "total_count": 0,
            "by_type": {},
            "by_task_type": {},
            "by_tool": {},
            "average_rating": 0.0
        }
    
    def record_explicit_feedback(
        self,
        interaction_id: str,
        content: str,
        rating: Optional[int] = None,
        positive: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FeedbackRecord:
        """
        Record explicit feedback from a user.
        
        Args:
            interaction_id: ID of the interaction the feedback is for
            content: Feedback content
            rating: Optional numerical rating (e.g., 1-5)
            positive: Optional boolean indicating if the feedback is positive
            metadata: Optional metadata about the feedback
            
        Returns:
            The created feedback record
        """
        # Determine feedback type
        if positive is not None:
            feedback_type = FeedbackType.EXPLICIT_POSITIVE if positive else FeedbackType.EXPLICIT_NEGATIVE
        elif rating is not None:
            if rating > 3:  # Assuming a 1-5 scale
                feedback_type = FeedbackType.EXPLICIT_POSITIVE
            elif rating < 3:
                feedback_type = FeedbackType.EXPLICIT_NEGATIVE
            else:
                feedback_type = FeedbackType.EXPLICIT_NEUTRAL
        else:
            # Analyze sentiment in content
            # This is a placeholder. In a real implementation, this would use
            # sentiment analysis to determine if the feedback is positive or negative.
            feedback_type = FeedbackType.EXPLICIT_NEUTRAL
        
        # Create the feedback record
        feedback = FeedbackRecord(
            interaction_id=interaction_id,
            feedback_type=feedback_type,
            content=content,
            rating=rating,
            metadata=metadata or {}
        )
        
        # Store the feedback
        self.feedback_records[feedback.id] = feedback
        
        # Update feedback statistics
        self._update_feedback_stats(feedback)
        
        # Process the feedback
        self._process_feedback(feedback)
        
        return feedback
    
    def infer_implicit_feedback(
        self,
        current_interaction_id: str,
        previous_interaction_id: Optional[str] = None,
        user_action: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[FeedbackRecord]:
        """
        Infer implicit feedback from user actions.
        
        Args:
            current_interaction_id: ID of the current interaction
            previous_interaction_id: Optional ID of the previous interaction
            user_action: Description of the user's action
            metadata: Optional metadata about the feedback
            
        Returns:
            The created feedback record, or None if no feedback could be inferred
        """
        # Get the current interaction
        current_interaction = self.memory_store.get_interaction(current_interaction_id)
        if not current_interaction:
            return None
        
        # Get the previous interaction if provided
        previous_interaction = None
        if previous_interaction_id:
            previous_interaction = self.memory_store.get_interaction(previous_interaction_id)
        
        # Determine feedback type based on user action
        feedback_type = None
        content = ""
        
        if "correction" in user_action.lower() or "fix" in user_action.lower():
            feedback_type = FeedbackType.IMPLICIT_CORRECTION
            content = "User corrected the previous response"
        elif "repeat" in user_action.lower() or "again" in user_action.lower():
            feedback_type = FeedbackType.IMPLICIT_REPETITION
            content = "User repeated the request"
        elif "abandon" in user_action.lower() or "cancel" in user_action.lower():
            feedback_type = FeedbackType.IMPLICIT_ABANDONMENT
            content = "User abandoned the task"
        elif "continue" in user_action.lower() or "next" in user_action.lower():
            feedback_type = FeedbackType.IMPLICIT_CONTINUATION
            content = "User continued with the task"
        
        # If no feedback type could be determined, try to infer from the interaction content
        if not feedback_type and previous_interaction:
            # Check if the current prompt is similar to the previous one
            if self._is_similar_prompt(current_interaction.user_prompt, previous_interaction.user_prompt):
                feedback_type = FeedbackType.IMPLICIT_REPETITION
                content = "User repeated a similar request"
            
            # Check if the current prompt contains corrections
            elif self._contains_correction(current_interaction.user_prompt, previous_interaction.bot_response):
                feedback_type = FeedbackType.IMPLICIT_CORRECTION
                content = "User's prompt contains corrections to the previous response"
        
        # If still no feedback type, return None
        if not feedback_type:
            return None
        
        # Create the feedback record
        feedback = FeedbackRecord(
            interaction_id=current_interaction_id,
            feedback_type=feedback_type,
            content=content,
            metadata=metadata or {}
        )
        
        # Store the feedback
        self.feedback_records[feedback.id] = feedback
        
        # Update feedback statistics
        self._update_feedback_stats(feedback)
        
        # Process the feedback
        self._process_feedback(feedback)
        
        return feedback
    
    def _is_similar_prompt(self, prompt1: str, prompt2: str) -> bool:
        """
        Check if two prompts are similar.
        
        Args:
            prompt1: The first prompt
            prompt2: The second prompt
            
        Returns:
            True if the prompts are similar, False otherwise
        """
        # This is a placeholder. In a real implementation, this would use
        # more sophisticated similarity measures.
        
        # Convert to lowercase and split into words
        words1 = set(prompt1.lower().split())
        words2 = set(prompt2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        
        # Consider prompts similar if similarity is above a threshold
        return similarity > 0.7
    
    def _contains_correction(self, prompt: str, previous_response: str) -> bool:
        """
        Check if a prompt contains corrections to a previous response.
        
        Args:
            prompt: The prompt to check
            previous_response: The previous response
            
        Returns:
            True if the prompt contains corrections, False otherwise
        """
        # This is a placeholder. In a real implementation, this would use
        # more sophisticated NLP techniques.
        
        # Check for common correction phrases
        correction_phrases = [
            "that's not what I meant",
            "that's incorrect",
            "you misunderstood",
            "I meant",
            "actually",
            "instead",
            "correction",
            "wrong",
            "not right"
        ]
        
        for phrase in correction_phrases:
            if phrase in prompt.lower():
                return True
        
        return False
    
    def _update_feedback_stats(self, feedback: FeedbackRecord) -> None:
        """
        Update feedback statistics with a new feedback record.
        
        Args:
            feedback: The feedback record to update statistics with
        """
        # Update total count
        self.feedback_stats["total_count"] += 1
        
        # Update by type
        feedback_type = feedback.feedback_type.value
        self.feedback_stats["by_type"][feedback_type] = self.feedback_stats["by_type"].get(feedback_type, 0) + 1
        
        # Update average rating
        if feedback.rating is not None:
            total_ratings = sum(1 for f in self.feedback_records.values() if f.rating is not None)
            total_rating_value = sum(f.rating for f in self.feedback_records.values() if f.rating is not None)
            self.feedback_stats["average_rating"] = total_rating_value / total_ratings if total_ratings > 0 else 0
        
        # Update by task type and tool
        interaction = self.memory_store.get_interaction(feedback.interaction_id)
        if interaction:
            # Update by task type
            if interaction.task_type:
                task_type = interaction.task_type
                if task_type not in self.feedback_stats["by_task_type"]:
                    self.feedback_stats["by_task_type"][task_type] = {
                        "total": 0,
                        "positive": 0,
                        "negative": 0,
                        "neutral": 0
                    }
                
                self.feedback_stats["by_task_type"][task_type]["total"] += 1
                
                if feedback.feedback_type == FeedbackType.EXPLICIT_POSITIVE or feedback.feedback_type == FeedbackType.IMPLICIT_CONTINUATION:
                    self.feedback_stats["by_task_type"][task_type]["positive"] += 1
                elif feedback.feedback_type == FeedbackType.EXPLICIT_NEGATIVE or feedback.feedback_type == FeedbackType.IMPLICIT_CORRECTION or feedback.feedback_type == FeedbackType.IMPLICIT_REPETITION or feedback.feedback_type == FeedbackType.IMPLICIT_ABANDONMENT:
                    self.feedback_stats["by_task_type"][task_type]["negative"] += 1
                else:
                    self.feedback_stats["by_task_type"][task_type]["neutral"] += 1
            
            # Update by tool
            for tool in interaction.tools_used:
                if tool not in self.feedback_stats["by_tool"]:
                    self.feedback_stats["by_tool"][tool] = {
                        "total": 0,
                        "positive": 0,
                        "negative": 0,
                        "neutral": 0
                    }
                
                self.feedback_stats["by_tool"][tool]["total"] += 1
                
                if feedback.feedback_type == FeedbackType.EXPLICIT_POSITIVE or feedback.feedback_type == FeedbackType.IMPLICIT_CONTINUATION:
                    self.feedback_stats["by_tool"][tool]["positive"] += 1
                elif feedback.feedback_type == FeedbackType.EXPLICIT_NEGATIVE or feedback.feedback_type == FeedbackType.IMPLICIT_CORRECTION or feedback.feedback_type == FeedbackType.IMPLICIT_REPETITION or feedback.feedback_type == FeedbackType.IMPLICIT_ABANDONMENT:
                    self.feedback_stats["by_tool"][tool]["negative"] += 1
                else:
                    self.feedback_stats["by_tool"][tool]["neutral"] += 1
    
    def _process_feedback(self, feedback: FeedbackRecord) -> None:
        """
        Process a feedback record to guide learning.
        
        Args:
            feedback: The feedback record to process
        """
        # Get the interaction
        interaction = self.memory_store.get_interaction(feedback.interaction_id)
        if not interaction:
            return
        
        # Determine if the feedback is positive or negative
        is_positive = feedback.feedback_type == FeedbackType.EXPLICIT_POSITIVE or feedback.feedback_type == FeedbackType.IMPLICIT_CONTINUATION
        is_negative = feedback.feedback_type == FeedbackType.EXPLICIT_NEGATIVE or feedback.feedback_type == FeedbackType.IMPLICIT_CORRECTION or feedback.feedback_type == FeedbackType.IMPLICIT_REPETITION or feedback.feedback_type == FeedbackType.IMPLICIT_ABANDONMENT
        
        # Update the interaction's success flag based on feedback
        if is_positive:
            interaction.success = True
        elif is_negative:
            interaction.success = False
        
        # If the interaction has a task type, update strategy performance
        if interaction.task_type:
            # This is a placeholder. In a real implementation, this would
            # update the strategy that was used for this interaction.
            pass
        
        # If the feedback is negative, prioritize improvements
        if is_negative:
            self._prioritize_improvements(interaction, feedback)
    
    def _prioritize_improvements(
        self,
        interaction: InteractionRecord,
        feedback: FeedbackRecord
    ) -> None:
        """
        Prioritize improvements based on negative feedback.
        
        Args:
            interaction: The interaction that received negative feedback
            feedback: The negative feedback
        """
        # This is a placeholder. In a real implementation, this would
        # analyze the feedback and interaction to prioritize specific improvements.
        
        # For now, just log the negative feedback
        logger.info(f"Negative feedback received for interaction {interaction.id}: {feedback.content}")
        
        # If the interaction has a task type, prioritize improvements for that task type
        if interaction.task_type:
            # Check if this task type has a high rate of negative feedback
            task_type = interaction.task_type
            task_stats = self.feedback_stats["by_task_type"].get(task_type, {})
            
            negative_rate = task_stats.get("negative", 0) / task_stats.get("total", 1) if task_stats.get("total", 0) > 0 else 0
            
            if negative_rate > 0.3:  # If more than 30% of feedback is negative
                logger.info(f"High negative feedback rate ({negative_rate:.1%}) for task type {task_type}. Prioritizing improvements.")
                
                # This is where you would trigger specific improvement actions
                # For example, creating new strategy variants or extracting more knowledge
    
    def get_feedback_for_interaction(self, interaction_id: str) -> List[FeedbackRecord]:
        """
        Get all feedback for a specific interaction.
        
        Args:
            interaction_id: The ID of the interaction to get feedback for
            
        Returns:
            List of feedback records for the interaction
        """
        return [f for f in self.feedback_records.values() if f.interaction_id == interaction_id]
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get feedback statistics.
        
        Returns:
            Dictionary with feedback statistics
        """
        return self.feedback_stats
    
    def get_improvement_priorities(self) -> Dict[str, Any]:
        """
        Get improvement priorities based on feedback.
        
        Returns:
            Dictionary with improvement priorities
        """
        priorities = {
            "task_types": [],
            "tools": []
        }
        
        # Prioritize task types with high negative feedback rates
        for task_type, stats in self.feedback_stats["by_task_type"].items():
            negative_rate = stats.get("negative", 0) / stats.get("total", 1) if stats.get("total", 0) > 0 else 0
            
            if negative_rate > 0.3 and stats.get("total", 0) >= 5:  # At least 5 feedback records
                priorities["task_types"].append({
                    "task_type": task_type,
                    "negative_rate": negative_rate,
                    "total_feedback": stats.get("total", 0),
                    "priority": "high" if negative_rate > 0.5 else "medium"
                })
        
        # Prioritize tools with high negative feedback rates
        for tool, stats in self.feedback_stats["by_tool"].items():
            negative_rate = stats.get("negative", 0) / stats.get("total", 1) if stats.get("total", 0) > 0 else 0
            
            if negative_rate > 0.3 and stats.get("total", 0) >= 5:  # At least 5 feedback records
                priorities["tools"].append({
                    "tool": tool,
                    "negative_rate": negative_rate,
                    "total_feedback": stats.get("total", 0),
                    "priority": "high" if negative_rate > 0.5 else "medium"
                })
        
        # Sort by negative rate (descending)
        priorities["task_types"].sort(key=lambda x: x["negative_rate"], reverse=True)
        priorities["tools"].sort(key=lambda x: x["negative_rate"], reverse=True)
        
        return priorities
    
    def generate_feedback_report(self) -> str:
        """
        Generate a comprehensive feedback report.
        
        Returns:
            Formatted report as a string
        """
        # Get feedback statistics
        stats = self.get_feedback_stats()
        
        # Get improvement priorities
        priorities = self.get_improvement_priorities()
        
        # Format the report
        report = "# Nexagent Feedback Report\n\n"
        
        # Overall statistics
        report += "## Overall Statistics\n\n"
        report += f"- Total feedback: {stats.get('total_count', 0)}\n"
        report += f"- Average rating: {stats.get('average_rating', 0):.1f}\n\n"
        
        # Feedback by type
        report += "## Feedback by Type\n\n"
        for feedback_type, count in stats.get("by_type", {}).items():
            report += f"- {feedback_type}: {count}\n"
        
        # Improvement priorities
        report += "\n## Improvement Priorities\n\n"
        
        report += "### Task Types\n\n"
        for task_type in priorities.get("task_types", []):
            report += f"- {task_type['task_type']}: {task_type['negative_rate']:.1%} negative feedback ({task_type['total_feedback']} total) - {task_type['priority']} priority\n"
        
        report += "\n### Tools\n\n"
        for tool in priorities.get("tools", []):
            report += f"- {tool['tool']}: {tool['negative_rate']:.1%} negative feedback ({tool['total_feedback']} total) - {tool['priority']} priority\n"
        
        # Recent feedback
        report += "\n## Recent Feedback\n\n"
        recent_feedback = sorted(
            self.feedback_records.values(),
            key=lambda f: f.timestamp,
            reverse=True
        )[:10]
        
        for feedback in recent_feedback:
            timestamp = datetime.fromtimestamp(feedback.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            report += f"### {feedback.feedback_type.value} ({timestamp})\n\n"
            report += f"{feedback.content}\n\n"
            if feedback.rating is not None:
                report += f"Rating: {feedback.rating}\n\n"
        
        return report
    
    def save_feedback(self, file_path: str) -> None:
        """
        Save feedback records to a file.
        
        Args:
            file_path: Path to save the feedback records to
        """
        try:
            feedback_data = {
                "records": [feedback.dict() for feedback in self.feedback_records.values()],
                "stats": self.feedback_stats
            }
            
            with open(file_path, "w") as f:
                json.dump(feedback_data, f, indent=2)
            
            logger.info(f"Saved feedback records to {file_path}")
        
        except Exception as e:
            logger.error(f"Error saving feedback records: {str(e)}")
    
    def load_feedback(self, file_path: str) -> None:
        """
        Load feedback records from a file.
        
        Args:
            file_path: Path to load the feedback records from
        """
        try:
            with open(file_path, "r") as f:
                feedback_data = json.load(f)
            
            # Load feedback records
            self.feedback_records = {}
            for record_data in feedback_data.get("records", []):
                feedback = FeedbackRecord(**record_data)
                self.feedback_records[feedback.id] = feedback
            
            # Load feedback statistics
            if "stats" in feedback_data:
                self.feedback_stats = feedback_data["stats"]
            
            logger.info(f"Loaded feedback records from {file_path}")
        
        except Exception as e:
            logger.error(f"Error loading feedback records: {str(e)}")


# Create a default feedback integration instance
default_feedback_integration = FeedbackIntegration()
