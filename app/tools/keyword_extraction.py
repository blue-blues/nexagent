"""
Keyword Extraction Tool for Nexagent.

This module provides functionality for extracting and validating keywords
from user inputs and project contexts.
"""

import json
import re
from typing import Dict, List, Optional, Any, Set, Union
from collections import Counter

from pydantic import Field

from app.tools.base import BaseTool, ToolResult
from app.logger import logger

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class KeywordExtractionTool(BaseTool):
    """
    A tool for extracting and validating keywords from user inputs and project contexts.
    
    This tool provides multiple extraction methods:
    1. Rule-based extraction using regex patterns
    2. TF-IDF based extraction (if scikit-learn is available)
    3. Semantic extraction using Sentence-BERT (if sentence-transformers is available)
    
    It also includes validation mechanisms to ensure extracted keywords are relevant
    to the project context.
    """
    
    name: str = "keyword_extraction"
    description: str = """
    Extracts and validates keywords from user inputs and project contexts.
    Supports multiple extraction methods and validation mechanisms.
    """
    
    # Domain-specific keyword lists
    programming_keywords: Set[str] = Field(
        default_factory=lambda: {
            "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
            "api", "rest", "graphql", "database", "sql", "nosql", "mongodb", "postgresql",
            "frontend", "backend", "fullstack", "web", "mobile", "desktop", "cloud",
            "aws", "azure", "gcp", "docker", "kubernetes", "microservices", "serverless",
            "authentication", "authorization", "security", "testing", "ci/cd", "devops"
        }
    )
    
    # Extraction parameters
    min_keyword_length: int = Field(default=3)
    max_keywords: int = Field(default=10)
    
    # Cached models
    _tfidf_vectorizer: Optional[Any] = None
    _sentence_transformer: Optional[Any] = None
    
    async def execute(
        self,
        *,
        command: str,
        text: str,
        project_context: Optional[str] = None,
        extraction_method: str = "auto",
        domain: Optional[str] = None,
        max_keywords: Optional[int] = None,
        **kwargs
    ) -> ToolResult:
        """
        Execute the keyword extraction tool.
        
        Args:
            command: The operation to perform (extract, validate)
            text: The text to extract keywords from
            project_context: Optional project context for validation
            extraction_method: Method to use for extraction (rule, tfidf, semantic, auto)
            domain: Optional domain for domain-specific keywords
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            ToolResult with extracted keywords
        """
        try:
            if command == "extract":
                keywords = await self._extract_keywords(
                    text=text,
                    extraction_method=extraction_method,
                    domain=domain,
                    max_keywords=max_keywords or self.max_keywords
                )
                
                return ToolResult(output=json.dumps({
                    "keywords": keywords,
                    "method_used": extraction_method
                }))
                
            elif command == "validate":
                if not project_context:
                    return ToolResult(error="Project context is required for validation")
                
                keywords = await self._extract_keywords(
                    text=text,
                    extraction_method=extraction_method,
                    domain=domain,
                    max_keywords=max_keywords or self.max_keywords
                )
                
                validation_result = await self._validate_keywords(
                    keywords=keywords,
                    project_context=project_context
                )
                
                return ToolResult(output=json.dumps({
                    "keywords": keywords,
                    "validation": validation_result,
                    "method_used": extraction_method
                }))
                
            else:
                return ToolResult(error=f"Unknown command: {command}. Supported commands: extract, validate")
                
        except Exception as e:
            logger.error(f"Error in KeywordExtractionTool: {str(e)}")
            return ToolResult(error=f"Error executing keyword extraction: {str(e)}")
    
    async def _extract_keywords(
        self,
        text: str,
        extraction_method: str = "auto",
        domain: Optional[str] = None,
        max_keywords: int = 10
    ) -> List[str]:
        """
        Extract keywords from text using the specified method.
        
        Args:
            text: The text to extract keywords from
            extraction_method: Method to use for extraction
            domain: Optional domain for domain-specific keywords
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of extracted keywords
        """
        # Determine the best extraction method if auto is specified
        if extraction_method == "auto":
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                extraction_method = "semantic"
            elif SKLEARN_AVAILABLE:
                extraction_method = "tfidf"
            else:
                extraction_method = "rule"
        
        # Extract keywords using the specified method
        if extraction_method == "rule":
            keywords = self._rule_based_extraction(text, max_keywords)
        elif extraction_method == "tfidf":
            if not SKLEARN_AVAILABLE:
                logger.warning("scikit-learn not available, falling back to rule-based extraction")
                keywords = self._rule_based_extraction(text, max_keywords)
            else:
                keywords = self._tfidf_extraction(text, max_keywords)
        elif extraction_method == "semantic":
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.warning("sentence-transformers not available, falling back to rule-based extraction")
                keywords = self._rule_based_extraction(text, max_keywords)
            else:
                keywords = self._semantic_extraction(text, max_keywords)
        else:
            raise ValueError(f"Unknown extraction method: {extraction_method}")
        
        # Apply domain-specific filtering if a domain is specified
        if domain:
            domain_keywords = self._get_domain_keywords(domain)
            keywords = [k for k in keywords if k.lower() in domain_keywords]
        
        return keywords[:max_keywords]
    
    def _rule_based_extraction(self, text: str, max_keywords: int) -> List[str]:
        """
        Extract keywords using rule-based methods.
        
        Args:
            text: The text to extract keywords from
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of extracted keywords
        """
        # Remove special characters and convert to lowercase
        cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into words and filter out short words
        words = [word for word in cleaned_text.split() if len(word) >= self.min_keyword_length]
        
        # Count word frequencies
        word_counts = Counter(words)
        
        # Filter out common stop words
        stop_words = {"the", "and", "is", "in", "to", "a", "of", "for", "with", "on", "at", "from", "by"}
        for word in stop_words:
            if word in word_counts:
                del word_counts[word]
        
        # Get the most common words
        keywords = [word for word, _ in word_counts.most_common(max_keywords)]
        
        return keywords
    
    def _tfidf_extraction(self, text: str, max_keywords: int) -> List[str]:
        """
        Extract keywords using TF-IDF.
        
        Args:
            text: The text to extract keywords from
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of extracted keywords
        """
        # Initialize the TF-IDF vectorizer if not already initialized
        if self._tfidf_vectorizer is None:
            self._tfidf_vectorizer = TfidfVectorizer(
                min_df=1,
                stop_words='english',
                lowercase=True,
                ngram_range=(1, 2)
            )
        
        # Split the text into sentences
        sentences = re.split(r'[.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # If there are no sentences, return an empty list
        if not sentences:
            return []
        
        # Compute TF-IDF
        try:
            tfidf_matrix = self._tfidf_vectorizer.fit_transform(sentences)
            feature_names = self._tfidf_vectorizer.get_feature_names_out()
            
            # Sum TF-IDF scores across all sentences
            tfidf_sums = np.array(tfidf_matrix.sum(axis=0)).flatten()
            
            # Get the indices of the top keywords
            top_indices = tfidf_sums.argsort()[-max_keywords:][::-1]
            
            # Get the keywords
            keywords = [feature_names[i] for i in top_indices]
            
            return keywords
        except Exception as e:
            logger.error(f"Error in TF-IDF extraction: {str(e)}")
            return self._rule_based_extraction(text, max_keywords)
    
    def _semantic_extraction(self, text: str, max_keywords: int) -> List[str]:
        """
        Extract keywords using semantic similarity with Sentence-BERT.
        
        Args:
            text: The text to extract keywords from
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of extracted keywords
        """
        # Initialize the Sentence Transformer if not already initialized
        if self._sentence_transformer is None:
            try:
                self._sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                logger.error(f"Error initializing Sentence Transformer: {str(e)}")
                return self._rule_based_extraction(text, max_keywords)
        
        # Split the text into sentences and words
        sentences = re.split(r'[.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # If there are no sentences, return an empty list
        if not sentences:
            return []
        
        # Extract candidate keywords (noun phrases, named entities, etc.)
        words = []
        for sentence in sentences:
            # Simple word extraction (can be enhanced with NLP techniques)
            sentence_words = re.findall(r'\b\w+\b', sentence.lower())
            words.extend([w for w in sentence_words if len(w) >= self.min_keyword_length])
        
        # Remove duplicates
        unique_words = list(set(words))
        
        # If there are no words, return an empty list
        if not unique_words:
            return []
        
        try:
            # Encode the text and candidate keywords
            text_embedding = self._sentence_transformer.encode([text])[0]
            word_embeddings = self._sentence_transformer.encode(unique_words)
            
            # Compute similarity between the text and each word
            similarities = cosine_similarity([text_embedding], word_embeddings)[0]
            
            # Get the indices of the top keywords
            top_indices = similarities.argsort()[-max_keywords:][::-1]
            
            # Get the keywords
            keywords = [unique_words[i] for i in top_indices]
            
            return keywords
        except Exception as e:
            logger.error(f"Error in semantic extraction: {str(e)}")
            return self._rule_based_extraction(text, max_keywords)
    
    async def _validate_keywords(
        self,
        keywords: List[str],
        project_context: str
    ) -> Dict[str, Any]:
        """
        Validate extracted keywords against the project context.
        
        Args:
            keywords: List of keywords to validate
            project_context: Project context for validation
            
        Returns:
            Dictionary with validation results
        """
        # Initialize validation result
        validation_result = {
            "valid_keywords": [],
            "invalid_keywords": [],
            "suggested_additions": [],
            "confidence_scores": {}
        }
        
        # Extract keywords from the project context
        context_keywords = await self._extract_keywords(
            text=project_context,
            extraction_method="auto",
            max_keywords=30  # Extract more keywords from context
        )
        
        # Validate each keyword
        for keyword in keywords:
            # Check if the keyword is in the context keywords
            if keyword.lower() in [k.lower() for k in context_keywords]:
                validation_result["valid_keywords"].append(keyword)
                validation_result["confidence_scores"][keyword] = 1.0
            else:
                # Compute similarity to context keywords if semantic extraction is available
                if SENTENCE_TRANSFORMERS_AVAILABLE and self._sentence_transformer is not None:
                    try:
                        keyword_embedding = self._sentence_transformer.encode([keyword])[0]
                        context_embeddings = self._sentence_transformer.encode(context_keywords)
                        similarities = cosine_similarity([keyword_embedding], context_embeddings)[0]
                        max_similarity = similarities.max()
                        
                        # If the similarity is above a threshold, consider it valid
                        if max_similarity > 0.7:
                            validation_result["valid_keywords"].append(keyword)
                            validation_result["confidence_scores"][keyword] = float(max_similarity)
                        else:
                            validation_result["invalid_keywords"].append(keyword)
                            validation_result["confidence_scores"][keyword] = float(max_similarity)
                    except Exception as e:
                        logger.error(f"Error in keyword validation: {str(e)}")
                        validation_result["invalid_keywords"].append(keyword)
                        validation_result["confidence_scores"][keyword] = 0.0
                else:
                    validation_result["invalid_keywords"].append(keyword)
                    validation_result["confidence_scores"][keyword] = 0.0
        
        # Suggest additional keywords from the context that are not in the extracted keywords
        for keyword in context_keywords:
            if keyword.lower() not in [k.lower() for k in keywords]:
                validation_result["suggested_additions"].append(keyword)
        
        return validation_result
    
    def _get_domain_keywords(self, domain: str) -> Set[str]:
        """
        Get domain-specific keywords.
        
        Args:
            domain: Domain for which to get keywords
            
        Returns:
            Set of domain-specific keywords
        """
        if domain == "programming":
            return self.programming_keywords
        else:
            return set()
