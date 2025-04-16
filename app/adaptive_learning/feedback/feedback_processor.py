"""
Feedback Processor for the Adaptive Learning System.

This module contains the FeedbackProcessor class that analyzes and extracts
insights from user feedback to drive system improvements.
"""

import logging
from typing import Dict, List, Optional, Any, Union

from app.adaptive_learning.core.config import AdaptiveLearningConfig
from app.adaptive_learning.core.exceptions import FeedbackProcessingError

logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """
    Processes and analyzes user feedback to extract actionable insights.
    
    This class is responsible for analyzing the content of user feedback,
    extracting meaningful patterns and insights, and assessing the impact
    of feedback on system improvement.
    
    Attributes:
        config (AdaptiveLearningConfig): Configuration for feedback processing
    """
    
    def __init__(self, config: AdaptiveLearningConfig):
        """
        Initialize the FeedbackProcessor.
        
        Args:
            config: Configuration for feedback processing
        """
        self.config = config
        logger.info("FeedbackProcessor initialized")
    
    async def analyze_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze feedback to extract insights and assess impact.
        
        Args:
            feedback_data: User feedback data including ratings, comments, and context
            
        Returns:
            Dict containing analysis results, quality score, and impact assessment
        """
        logger.debug(f"Analyzing feedback for interaction {feedback_data.get('interaction_id')}")
        
        # Calculate quality score for the feedback
        quality_score = self._calculate_quality_score(feedback_data)
        
        # Extract sentiment from feedback
        sentiment = self._analyze_sentiment(feedback_data)
        
        # Extract specific aspects mentioned in feedback
        mentioned_aspects = self._extract_mentioned_aspects(feedback_data)
        
        # Extract actionable insights
        actionable_insights = self._extract_actionable_insights(feedback_data)
        
        # Assess potential impact of the feedback
        impact_assessment = self._assess_impact(
            feedback_data, quality_score, sentiment, mentioned_aspects
        )
        
        # Prepare analysis result
        analysis_result = {
            "quality_score": quality_score,
            "sentiment": sentiment,
            "mentioned_aspects": mentioned_aspects,
            "actionable_insights": actionable_insights,
            "impact_assessment": impact_assessment,
        }
        
        logger.debug(f"Feedback analysis completed with quality score {quality_score}")
        return analysis_result
    
    def _calculate_quality_score(self, feedback_data: Dict[str, Any]) -> float:
        """
        Calculate a quality score for the feedback based on completeness and specificity.
        
        Args:
            feedback_data: The feedback data to evaluate
            
        Returns:
            Quality score between 0 and 1
        """
        score = 0.0
        max_score = 0.0
        
        # Check each feedback type and calculate weighted score
        for feedback_type, weight in self.config.feedback.feedback_type_weights.items():
            max_score += weight
            
            if feedback_type in feedback_data and feedback_data[feedback_type]:
                # Basic presence check
                type_score = 0.5 * weight
                
                # Check for specificity/detail
                if feedback_type == "rating" and isinstance(feedback_data[feedback_type], (int, float)):
                    type_score = weight  # Full score for numerical rating
                elif feedback_type == "text_comment" and isinstance(feedback_data[feedback_type], str):
                    # More detailed comments get higher scores
                    length = len(feedback_data[feedback_type])
                    if length > 100:
                        type_score = weight
                    elif length > 20:
                        type_score = 0.8 * weight
                elif feedback_type == "specific_aspect" and isinstance(feedback_data[feedback_type], dict):
                    # More aspects with ratings get higher scores
                    aspects = feedback_data[feedback_type]
                    if len(aspects) > 2:
                        type_score = weight
                    elif len(aspects) > 0:
                        type_score = 0.7 * weight
                elif feedback_type == "improvement_suggestion" and isinstance(feedback_data[feedback_type], str):
                    # More detailed suggestions get higher scores
                    length = len(feedback_data[feedback_type])
                    if length > 50:
                        type_score = weight
                    elif length > 10:
                        type_score = 0.6 * weight
                
                score += type_score
        
        # Normalize score
        if max_score > 0:
            normalized_score = score / max_score
        else:
            normalized_score = 0.0
        
        return normalized_score
    
    def _analyze_sentiment(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the sentiment expressed in the feedback.
        
        Args:
            feedback_data: The feedback data to analyze
            
        Returns:
            Dict containing sentiment analysis results
        """
        # In a real implementation, this would use NLP to analyze sentiment
        # Here we'll use a simple heuristic based on rating
        
        sentiment = {
            "overall": "neutral",
            "score": 0.5,  # Neutral by default
            "confidence": 0.6,
        }
        
        # Check for rating
        if "rating" in feedback_data and isinstance(feedback_data["rating"], (int, float)):
            rating = feedback_data["rating"]
            
            # Assuming rating is on a 1-5 scale
            if rating >= 4:
                sentiment["overall"] = "positive"
                sentiment["score"] = 0.8
            elif rating <= 2:
                sentiment["overall"] = "negative"
                sentiment["score"] = 0.2
            
            sentiment["confidence"] = 0.8  # Higher confidence with explicit rating
        
        # Check for text sentiment
        if "text_comment" in feedback_data and isinstance(feedback_data["text_comment"], str):
            # Simple keyword-based sentiment analysis
            # In a real implementation, this would use a proper NLP model
            text = feedback_data["text_comment"].lower()
            
            positive_keywords = ["great", "excellent", "good", "helpful", "amazing", "love", "like"]
            negative_keywords = ["bad", "poor", "unhelpful", "confusing", "wrong", "hate", "dislike"]
            
            positive_count = sum(1 for word in positive_keywords if word in text)
            negative_count = sum(1 for word in negative_keywords if word in text)
            
            if positive_count > negative_count:
                sentiment["text_sentiment"] = "positive"
                sentiment["text_score"] = 0.7
            elif negative_count > positive_count:
                sentiment["text_sentiment"] = "negative"
                sentiment["text_score"] = 0.3
            else:
                sentiment["text_sentiment"] = "neutral"
                sentiment["text_score"] = 0.5
        
        return sentiment
    
    def _extract_mentioned_aspects(self, feedback_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract specific aspects mentioned in the feedback.
        
        Args:
            feedback_data: The feedback data to analyze
            
        Returns:
            List of mentioned aspects with their sentiment and importance
        """
        mentioned_aspects = []
        
        # Extract from specific_aspect feedback type
        if "specific_aspect" in feedback_data and isinstance(feedback_data["specific_aspect"], dict):
            for aspect, rating in feedback_data["specific_aspect"].items():
                sentiment = "positive" if rating >= 4 else "negative" if rating <= 2 else "neutral"
                mentioned_aspects.append({
                    "aspect": aspect,
                    "rating": rating,
                    "sentiment": sentiment,
                    "source": "explicit_rating",
                    "importance": 0.8,  # High importance for explicitly rated aspects
                })
        
        # Extract from text_comment using keyword matching
        # In a real implementation, this would use NLP for aspect extraction
        if "text_comment" in feedback_data and isinstance(feedback_data["text_comment"], str):
            text = feedback_data["text_comment"].lower()
            
            # Define aspects to look for
            aspects_keywords = {
                "response_time": ["speed", "fast", "slow", "time", "quick", "wait"],
                "accuracy": ["accurate", "correct", "wrong", "mistake", "error", "accuracy"],
                "clarity": ["clear", "unclear", "confusing", "understand", "explanation", "clarity"],
                "code_quality": ["code", "implementation", "solution", "algorithm", "function"],
                "helpfulness": ["helpful", "useful", "useless", "value", "benefit"],
            }
            
            for aspect, keywords in aspects_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        # Check for sentiment context
                        context_start = max(0, text.find(keyword) - 20)
                        context_end = min(len(text), text.find(keyword) + 20)
                        context = text[context_start:context_end]
                        
                        positive_keywords = ["good", "great", "excellent", "helpful", "like"]
                        negative_keywords = ["bad", "poor", "not", "isn't", "doesn't", "dislike"]
                        
                        sentiment = "neutral"
                        for pos in positive_keywords:
                            if pos in context:
                                sentiment = "positive"
                                break
                        for neg in negative_keywords:
                            if neg in context:
                                sentiment = "negative"
                                break
                        
                        # Add to mentioned aspects if not already present
                        if not any(a["aspect"] == aspect for a in mentioned_aspects):
                            mentioned_aspects.append({
                                "aspect": aspect,
                                "sentiment": sentiment,
                                "source": "text_analysis",
                                "importance": 0.6,  # Medium importance for implicitly mentioned aspects
                                "context": context,
                            })
                        break
        
        return mentioned_aspects
    
    def _extract_actionable_insights(self, feedback_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract actionable insights from the feedback.
        
        Args:
            feedback_data: The feedback data to analyze
            
        Returns:
            List of actionable insights with their priority and source
        """
        actionable_insights = []
        
        # Extract from improvement_suggestion
        if "improvement_suggestion" in feedback_data and isinstance(feedback_data["improvement_suggestion"], str):
            suggestion = feedback_data["improvement_suggestion"]
            if len(suggestion) > 10:  # Basic check for meaningful content
                actionable_insights.append({
                    "insight": suggestion,
                    "source": "explicit_suggestion",
                    "priority": "high",
                    "confidence": 0.9,
                })
        
        # Extract from text_comment
        if "text_comment" in feedback_data and isinstance(feedback_data["text_comment"], str):
            text = feedback_data["text_comment"]
            
            # Look for suggestion patterns
            suggestion_starters = [
                "should ", "could ", "would be better if", "improve", "enhance",
                "add", "include", "consider", "try", "need to", "missing", "lacks",
            ]
            
            for starter in suggestion_starters:
                if starter in text.lower():
                    # Extract the sentence containing the suggestion
                    sentences = text.split(". ")
                    for sentence in sentences:
                        if starter in sentence.lower():
                            actionable_insights.append({
                                "insight": sentence.strip(),
                                "source": "implicit_suggestion",
                                "priority": "medium",
                                "confidence": 0.7,
                            })
        
        # Extract from specific aspects with negative sentiment
        for aspect in self._extract_mentioned_aspects(feedback_data):
            if aspect["sentiment"] == "negative":
                insight = f"Improve {aspect['aspect']}"
                if "context" in aspect:
                    insight += f" based on feedback: '{aspect['context']}'"
                
                actionable_insights.append({
                    "insight": insight,
                    "source": "negative_aspect",
                    "priority": "medium" if aspect["importance"] >= 0.7 else "low",
                    "confidence": aspect["importance"],
                    "related_aspect": aspect["aspect"],
                })
        
        return actionable_insights
    
    def _assess_impact(
        self,
        feedback_data: Dict[str, Any],
        quality_score: float,
        sentiment: Dict[str, Any],
        mentioned_aspects: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Assess the potential impact of the feedback on system improvement.
        
        Args:
            feedback_data: The original feedback data
            quality_score: The calculated quality score
            sentiment: The sentiment analysis results
            mentioned_aspects: The extracted mentioned aspects
            
        Returns:
            Dict containing impact assessment results
        """
        # Calculate overall impact score
        impact_score = quality_score * 0.4  # Quality contributes 40%
        
        # Sentiment contributes 20%
        sentiment_factor = 0.5  # Neutral by default
        if sentiment["overall"] == "positive":
            sentiment_factor = 0.7
        elif sentiment["overall"] == "negative":
            sentiment_factor = 0.8  # Negative feedback often has higher impact
        
        impact_score += sentiment_factor * 0.2
        
        # Mentioned aspects contribute 40%
        aspect_impact = 0.0
        if mentioned_aspects:
            # More aspects and higher importance increase impact
            aspect_count_factor = min(1.0, len(mentioned_aspects) / 5)  # Cap at 5 aspects
            avg_importance = sum(a["importance"] for a in mentioned_aspects) / len(mentioned_aspects)
            
            aspect_impact = (aspect_count_factor * 0.5 + avg_importance * 0.5) * 0.4
        
        impact_score += aspect_impact
        
        # Determine impact areas
        impact_areas = []
        for aspect in mentioned_aspects:
            if aspect["sentiment"] == "negative":
                impact_areas.append({
                    "area": aspect["aspect"],
                    "importance": aspect["importance"],
                    "confidence": 0.7,
                })
        
        # Determine recommended actions based on impact
        recommended_actions = []
        if impact_score > 0.7:
            recommended_actions.append("Prioritize addressing the feedback immediately")
        elif impact_score > 0.5:
            recommended_actions.append("Consider addressing the feedback in the next update cycle")
        else:
            recommended_actions.append("Monitor for similar feedback to determine if action is needed")
        
        # Add specific actions based on mentioned aspects
        for aspect in mentioned_aspects:
            if aspect["sentiment"] == "negative" and aspect["importance"] > 0.6:
                recommended_actions.append(f"Review and improve {aspect['aspect']}")
        
        return {
            "impact_score": impact_score,
            "impact_level": "high" if impact_score > 0.7 else "medium" if impact_score > 0.4 else "low",
            "impact_areas": impact_areas,
            "recommended_actions": recommended_actions,
        }
