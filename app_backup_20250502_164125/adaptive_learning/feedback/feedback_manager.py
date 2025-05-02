"""
Feedback Manager for the Adaptive Learning System.

This module contains the FeedbackManager class that coordinates the collection,
validation, storage, and processing of user feedback.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from app.adaptive_learning.core.config import AdaptiveLearningConfig
from app.adaptive_learning.core.exceptions import FeedbackProcessingError
from app.adaptive_learning.feedback.feedback_processor import FeedbackProcessor
from app.adaptive_learning.feedback.feedback_schema import FeedbackSchema

logger = logging.getLogger(__name__)


class FeedbackManager:
    """
    Manages the collection and processing of user feedback.
    
    This class coordinates all aspects of feedback handling, including validation,
    storage, analysis, and integration with other components of the adaptive
    learning system.
    
    Attributes:
        config (AdaptiveLearningConfig): Configuration for feedback processing
        processor (FeedbackProcessor): Processor for analyzing feedback content
        feedback_store (Dict): In-memory store for feedback (would use a database in production)
    """
    
    def __init__(self, config: AdaptiveLearningConfig):
        """
        Initialize the FeedbackManager.
        
        Args:
            config: Configuration for the feedback manager
        """
        self.config = config
        self.processor = FeedbackProcessor(config)
        self.feedback_store = {}  # In-memory store (would use a database in production)
        logger.info("FeedbackManager initialized")
    
    async def process_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user feedback for an interaction.
        
        Args:
            feedback_data: User feedback data including ratings, comments, and context
            
        Returns:
            Dict containing feedback processing results and impact assessment
            
        Raises:
            FeedbackProcessingError: If feedback processing fails
        """
        try:
            logger.debug(f"Processing feedback for interaction {feedback_data.get('interaction_id')}")
            
            # Validate feedback data
            self._validate_feedback(feedback_data)
            
            # Generate a unique ID for this feedback
            feedback_id = str(uuid.uuid4())
            feedback_data['feedback_id'] = feedback_id
            feedback_data['timestamp'] = datetime.now().isoformat()
            
            # Process and analyze the feedback
            analysis_result = await self.processor.analyze_feedback(feedback_data)
            
            # Store the feedback with its analysis
            stored_feedback = {
                **feedback_data,
                'analysis': analysis_result,
            }
            self.feedback_store[feedback_id] = stored_feedback
            
            # Prepare the result
            result = {
                'feedback_id': feedback_id,
                'interaction_id': feedback_data.get('interaction_id'),
                'timestamp': feedback_data['timestamp'],
                'quality_score': analysis_result.get('quality_score', 0),
                'impact_assessment': analysis_result.get('impact_assessment', {}),
                'actionable_insights': analysis_result.get('actionable_insights', []),
            }
            
            logger.info(f"Feedback {feedback_id} processed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error processing feedback: {str(e)}")
            raise FeedbackProcessingError(f"Failed to process feedback: {str(e)}")
    
    def _validate_feedback(self, feedback_data: Dict[str, Any]) -> None:
        """
        Validate feedback data against the schema.
        
        Args:
            feedback_data: Feedback data to validate
            
        Raises:
            FeedbackProcessingError: If validation fails
        """
        # Check required fields
        required_fields = ['interaction_id', 'user_id']
        for field in required_fields:
            if field not in feedback_data:
                raise FeedbackProcessingError(f"Missing required field: {field}")
        
        # Check that at least one feedback type is provided
        feedback_types = self.config.feedback.feedback_types
        has_feedback = False
        for feedback_type in feedback_types:
            if feedback_type in feedback_data and feedback_data[feedback_type]:
                has_feedback = True
                break
        
        if not has_feedback:
            raise FeedbackProcessingError(
                f"Feedback must include at least one of: {', '.join(feedback_types)}"
            )
    
    async def get_feedback(self, feedback_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific feedback item.
        
        Args:
            feedback_id: ID of the feedback to retrieve
            
        Returns:
            The feedback data or None if not found
        """
        return self.feedback_store.get(feedback_id)
    
    async def get_interaction_feedback(self, interaction_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all feedback for a specific interaction.
        
        Args:
            interaction_id: ID of the interaction
            
        Returns:
            List of feedback items for the interaction
        """
        return [
            feedback for feedback in self.feedback_store.values()
            if feedback.get('interaction_id') == interaction_id
        ]
    
    async def generate_report(self, time_period: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a report on feedback collection and processing.
        
        Args:
            time_period: Optional time period to cover in the report
            
        Returns:
            Dict containing the feedback report data
        """
        # Implementation would generate statistics and insights from feedback data
        return {
            "total_feedback": len(self.feedback_store),
            "average_quality": self._calculate_average_quality(),
            "feedback_distribution": self._calculate_feedback_distribution(),
            "top_insights": self._extract_top_insights(),
            "trend_analysis": self._analyze_feedback_trends(time_period),
        }
    
    def _calculate_average_quality(self) -> float:
        """Calculate the average quality score of all feedback."""
        if not self.feedback_store:
            return 0.0
        
        total_quality = sum(
            feedback.get('analysis', {}).get('quality_score', 0)
            for feedback in self.feedback_store.values()
        )
        return total_quality / len(self.feedback_store)
    
    def _calculate_feedback_distribution(self) -> Dict[str, Any]:
        """Calculate the distribution of feedback across different categories."""
        # Implementation would analyze feedback distribution
        return {
            "by_rating": {
                "positive": 0.65,  # Example values
                "neutral": 0.25,
                "negative": 0.1,
            },
            "by_type": {
                "rating": 0.8,  # Example values
                "text_comment": 0.6,
                "specific_aspect": 0.4,
                "improvement_suggestion": 0.3,
            },
        }
    
    def _extract_top_insights(self) -> List[str]:
        """Extract the top insights from feedback analysis."""
        # Implementation would extract key insights
        return [
            "Users consistently request more detailed explanations in code generation",
            "Positive feedback correlates with step-by-step reasoning in complex tasks",
            "Error handling improvements have led to increased satisfaction ratings",
        ]
    
    def _analyze_feedback_trends(self, time_period: Optional[str]) -> Dict[str, Any]:
        """Analyze trends in feedback over time."""
        # Implementation would analyze trends
        return {
            "satisfaction_trend": "increasing",
            "common_issues": ["response time", "code quality", "explanation clarity"],
            "improvement_areas": ["error recovery", "multi-step planning", "code optimization"],
        }
