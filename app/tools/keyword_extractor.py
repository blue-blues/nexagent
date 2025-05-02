"""
Keyword Extractor Tool for extracting contextual keywords from user input and project context.

This tool analyzes user input and project context to extract critical keywords
that can be used for web searches, code generation, and other tasks.
"""

import json
import os
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import Counter
import math
from pydantic import Field

from app.tools.base import BaseTool, ToolResult
from app.logger import logger


class KeywordExtractor(BaseTool):
    """
    Tool for extracting contextual keywords from user input and project context.
    
    This tool uses domain-specific keyword lists, TF-IDF, and other algorithms
    to extract the most relevant keywords from user input and project context.
    """
    
    name: str = "keyword_extractor"
    description: str = """
    Extract contextual keywords from user input and project context.
    This tool helps identify the most relevant terms for web searches,
    code generation, and other tasks.
    """
    
    # Path to domain keywords file
    domain_keywords_path: str = os.path.join("app", "data", "domain_keywords.json")
    
    # Domain keywords cache
    _domain_keywords: Optional[Dict[str, Dict[str, List[str]]]] = None
    
    # Common programming terms for fallback
    common_programming_terms: List[str] = [
        "API", "REST", "GraphQL", "database", "authentication", "frontend",
        "backend", "full-stack", "mobile", "web", "cloud", "serverless",
        "microservices", "container", "docker", "kubernetes", "CI/CD",
        "testing", "deployment", "security", "performance", "scalability",
        "Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "Go",
        "React", "Angular", "Vue", "Node.js", "Django", "Flask", "Spring",
        "Express", "ASP.NET", "Laravel", "Ruby on Rails", "SQL", "NoSQL",
        "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "AWS",
        "Azure", "GCP", "Heroku", "Netlify", "Vercel", "Git", "GitHub",
        "GitLab", "Bitbucket", "Agile", "Scrum", "Kanban", "DevOps", "SRE"
    ]
    
    # Stop words for filtering
    stop_words: Set[str] = {
        "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
        "up", "down", "in", "out", "on", "off", "over", "under", "again",
        "further", "then", "once", "here", "there", "when", "where", "why",
        "how", "all", "any", "both", "each", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "s", "t", "can", "will", "just", "don",
        "should", "now", "d", "ll", "m", "o", "re", "ve", "y", "ain", "aren",
        "couldn", "didn", "doesn", "hadn", "hasn", "haven", "isn", "ma",
        "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren", "won",
        "wouldn", "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
        "you", "your", "yours", "yourself", "yourselves", "he", "him", "his",
        "himself", "she", "her", "hers", "herself", "it", "its", "itself",
        "they", "them", "their", "theirs", "themselves", "what", "which",
        "who", "whom", "this", "that", "these", "those", "am", "is", "are",
        "was", "were", "be", "been", "being", "have", "has", "had", "having",
        "do", "does", "did", "doing", "would", "should", "could", "ought",
        "i'm", "you're", "he's", "she's", "it's", "we're", "they're", "i've",
        "you've", "we've", "they've", "i'd", "you'd", "he'd", "she'd", "we'd",
        "they'd", "i'll", "you'll", "he'll", "she'll", "we'll", "they'll",
        "isn't", "aren't", "wasn't", "weren't", "hasn't", "haven't", "hadn't",
        "doesn't", "don't", "didn't", "won't", "wouldn't", "shan't", "shouldn't",
        "can't", "cannot", "couldn't", "mustn't", "let's", "that's", "who's",
        "what's", "here's", "there's", "when's", "where's", "why's", "how's",
        "want", "need", "would", "like", "make", "create", "build", "develop",
        "implement", "design", "get", "use", "using", "with", "without", "from",
        "about", "for", "by", "as", "to", "of", "at", "by"
    }
    
    async def execute(self, command: str, text: str, project_context: Optional[str] = None,
                     domain: Optional[str] = None, extraction_method: str = "auto",
                     max_keywords: int = 10, min_relevance: float = 0.1) -> ToolResult:
        """
        Execute the keyword extractor tool.
        
        Args:
            command: The command to execute (extract, validate, analyze)
            text: The user input text to extract keywords from
            project_context: Optional project context for additional keyword extraction
            domain: Optional domain to focus extraction on
            extraction_method: Method for extraction (auto, domain_specific, tf_idf, frequency)
            max_keywords: Maximum number of keywords to extract
            min_relevance: Minimum relevance score for keywords (0.0-1.0)
            
        Returns:
            ToolResult containing the extracted keywords
        """
        try:
            if command == "extract":
                keywords = await self._extract_keywords(
                    text, project_context, domain, extraction_method, max_keywords, min_relevance
                )
                return ToolResult(output=json.dumps({"keywords": keywords}, indent=2))
                
            elif command == "validate":
                validation_result = self._validate_keywords(
                    text, json.loads(project_context) if project_context else None
                )
                return ToolResult(output=json.dumps(validation_result, indent=2))
                
            elif command == "analyze":
                analysis = self._analyze_keyword_relevance(
                    text, project_context, domain, max_keywords
                )
                return ToolResult(output=json.dumps(analysis, indent=2))
                
            else:
                return ToolResult(error=f"Unknown command: {command}")
                
        except Exception as e:
            logger.error(f"Error in KeywordExtractor: {str(e)}")
            return ToolResult(error=f"Failed to extract keywords: {str(e)}")
    
    async def _extract_keywords(self, text: str, project_context: Optional[str] = None,
                              domain: Optional[str] = None, extraction_method: str = "auto",
                              max_keywords: int = 10, min_relevance: float = 0.1) -> List[Dict[str, Any]]:
        """
        Extract keywords from text and project context.
        
        Args:
            text: The user input text to extract keywords from
            project_context: Optional project context for additional keyword extraction
            domain: Optional domain to focus extraction on
            extraction_method: Method for extraction
            max_keywords: Maximum number of keywords to extract
            min_relevance: Minimum relevance score for keywords
            
        Returns:
            List of extracted keywords with relevance scores
        """
        # Load domain keywords if not already loaded
        if self._domain_keywords is None:
            await self._load_domain_keywords()
        
        # Detect domain if not provided
        if domain is None and extraction_method in ["auto", "domain_specific"]:
            domain = self._detect_domain(text)
        
        # Combine text and project context
        combined_text = text
        if project_context:
            combined_text = f"{text}\n\n{project_context}"
        
        # Extract keywords using the specified method
        if extraction_method == "auto":
            # Try domain-specific first, then fall back to other methods
            keywords = []
            if domain:
                keywords = self._extract_domain_specific(combined_text, domain)
            
            # If not enough keywords, use TF-IDF
            if len(keywords) < max_keywords:
                tf_idf_keywords = self._extract_tf_idf(combined_text, max_keywords)
                
                # Merge keywords, avoiding duplicates
                existing_terms = {k["keyword"].lower() for k in keywords}
                for keyword in tf_idf_keywords:
                    if keyword["keyword"].lower() not in existing_terms:
                        keywords.append(keyword)
                        existing_terms.add(keyword["keyword"].lower())
                        
                        if len(keywords) >= max_keywords:
                            break
            
            # If still not enough keywords, use frequency-based extraction
            if len(keywords) < max_keywords:
                freq_keywords = self._extract_frequency_based(combined_text, max_keywords)
                
                # Merge keywords, avoiding duplicates
                existing_terms = {k["keyword"].lower() for k in keywords}
                for keyword in freq_keywords:
                    if keyword["keyword"].lower() not in existing_terms:
                        keywords.append(keyword)
                        existing_terms.add(keyword["keyword"].lower())
                        
                        if len(keywords) >= max_keywords:
                            break
        
        elif extraction_method == "domain_specific":
            keywords = self._extract_domain_specific(combined_text, domain)
            
        elif extraction_method == "tf_idf":
            keywords = self._extract_tf_idf(combined_text, max_keywords)
            
        elif extraction_method == "frequency":
            keywords = self._extract_frequency_based(combined_text, max_keywords)
            
        else:
            raise ValueError(f"Unknown extraction method: {extraction_method}")
        
        # Filter by minimum relevance and limit to max_keywords
        keywords = [k for k in keywords if k["relevance"] >= min_relevance]
        keywords = sorted(keywords, key=lambda k: k["relevance"], reverse=True)[:max_keywords]
        
        return keywords
    
    async def _load_domain_keywords(self) -> None:
        """Load domain keywords from the JSON file."""
        try:
            if os.path.exists(self.domain_keywords_path):
                with open(self.domain_keywords_path, 'r', encoding='utf-8') as f:
                    self._domain_keywords = json.load(f)
            else:
                logger.warning(f"Domain keywords file not found at {self.domain_keywords_path}")
                self._domain_keywords = {}
        except Exception as e:
            logger.error(f"Error loading domain keywords: {str(e)}")
            self._domain_keywords = {}
    
    def _detect_domain(self, text: str) -> Optional[str]:
        """Detect the domain of the text based on keyword frequency."""
        if not self._domain_keywords:
            return None
        
        # Count occurrences of domain keywords
        domain_scores = {domain: 0 for domain in self._domain_keywords}
        
        for domain, subdomains in self._domain_keywords.items():
            for subdomain, keywords in subdomains.items():
                for keyword in keywords:
                    if re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE):
                        domain_scores[domain] += 1
        
        # Return the domain with the highest score, if any
        max_domain = max(domain_scores.items(), key=lambda x: x[1])
        return max_domain[0] if max_domain[1] > 0 else None
    
    def _extract_domain_specific(self, text: str, domain: str) -> List[Dict[str, Any]]:
        """Extract domain-specific keywords from text."""
        if not self._domain_keywords or domain not in self._domain_keywords:
            return []
        
        keywords = []
        domain_data = self._domain_keywords[domain]
        
        # Collect all keywords from the domain
        all_domain_keywords = []
        for subdomain, kw_list in domain_data.items():
            all_domain_keywords.extend([(kw, subdomain) for kw in kw_list])
        
        # Check for keyword occurrences in the text
        for keyword, subdomain in all_domain_keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE):
                # Calculate relevance based on frequency and position
                relevance = self._calculate_keyword_relevance(text, keyword)
                
                keywords.append({
                    "keyword": keyword,
                    "relevance": relevance,
                    "domain": domain,
                    "subdomain": subdomain
                })
        
        # Sort by relevance and return
        return sorted(keywords, key=lambda k: k["relevance"], reverse=True)
    
    def _extract_tf_idf(self, text: str, max_keywords: int) -> List[Dict[str, Any]]:
        """Extract keywords using TF-IDF algorithm."""
        # Tokenize the text
        tokens = self._tokenize(text)
        
        # Calculate term frequency
        tf = Counter(tokens)
        
        # We don't have a corpus for IDF, so we'll use a simplified approach
        # where we consider the "document" to be each sentence
        sentences = re.split(r'[.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Calculate document frequency
        df = {}
        for term in tf:
            df[term] = sum(1 for sentence in sentences if term.lower() in self._tokenize(sentence))
        
        # Calculate TF-IDF
        tf_idf = {}
        num_docs = len(sentences)
        for term, freq in tf.items():
            if term.lower() not in self.stop_words and len(term) > 1:
                tf_term = freq / len(tokens)
                idf_term = math.log(num_docs / (1 + df[term]))
                tf_idf[term] = tf_term * idf_term
        
        # Sort by TF-IDF score and convert to the required format
        sorted_terms = sorted(tf_idf.items(), key=lambda x: x[1], reverse=True)
        
        # Normalize relevance scores to 0-1 range
        max_score = sorted_terms[0][1] if sorted_terms else 1.0
        
        keywords = []
        for term, score in sorted_terms[:max_keywords]:
            normalized_score = score / max_score
            keywords.append({
                "keyword": term,
                "relevance": normalized_score,
                "method": "tf_idf"
            })
        
        return keywords
    
    def _extract_frequency_based(self, text: str, max_keywords: int) -> List[Dict[str, Any]]:
        """Extract keywords based on frequency and position."""
        # Tokenize the text
        tokens = self._tokenize(text)
        
        # Count term frequency
        term_freq = Counter(tokens)
        
        # Filter out stop words and single characters
        filtered_terms = {term: freq for term, freq in term_freq.items() 
                         if term.lower() not in self.stop_words and len(term) > 1}
        
        # Calculate position importance (terms appearing earlier are more important)
        position_importance = {}
        for i, token in enumerate(tokens):
            if token in filtered_terms and token not in position_importance:
                # Normalize position (0 = start, 1 = end)
                normalized_pos = i / len(tokens)
                # Earlier positions get higher scores (1 - normalized_pos)
                position_importance[token] = 1 - normalized_pos
        
        # Combine frequency and position
        term_scores = {}
        for term, freq in filtered_terms.items():
            # Normalize frequency
            norm_freq = freq / len(tokens)
            # Position score (default to 0.5 if not found)
            pos_score = position_importance.get(term, 0.5)
            # Combined score (70% frequency, 30% position)
            term_scores[term] = (0.7 * norm_freq) + (0.3 * pos_score)
        
        # Sort by score and convert to the required format
        sorted_terms = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Normalize relevance scores to 0-1 range
        max_score = sorted_terms[0][1] if sorted_terms else 1.0
        
        keywords = []
        for term, score in sorted_terms[:max_keywords]:
            normalized_score = score / max_score
            keywords.append({
                "keyword": term,
                "relevance": normalized_score,
                "method": "frequency"
            })
        
        return keywords
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words, removing punctuation and converting to lowercase."""
        # Replace non-alphanumeric characters with spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        # Split on whitespace
        tokens = text.split()
        # Filter out stop words and single characters
        return [token for token in tokens if token.lower() not in self.stop_words and len(token) > 1]
    
    def _calculate_keyword_relevance(self, text: str, keyword: str) -> float:
        """Calculate the relevance of a keyword in the text."""
        # Count occurrences
        pattern = rf"\b{re.escape(keyword)}\b"
        occurrences = len(re.findall(pattern, text, re.IGNORECASE))
        
        if occurrences == 0:
            return 0.0
        
        # Calculate normalized frequency
        tokens = self._tokenize(text)
        normalized_freq = occurrences / len(tokens) if tokens else 0
        
        # Find first occurrence position
        match = re.search(pattern, text, re.IGNORECASE)
        first_pos = match.start() if match else len(text)
        normalized_pos = 1 - (first_pos / len(text)) if len(text) > 0 else 0
        
        # Combine metrics (frequency and position)
        relevance = (0.7 * normalized_freq) + (0.3 * normalized_pos)
        
        return min(1.0, relevance)
    
    def _validate_keywords(self, text: str, expected_keywords: Optional[List[str]]) -> Dict[str, Any]:
        """Validate extracted keywords against expected keywords."""
        # Extract keywords using the default method
        extracted = self._extract_frequency_based(text, max_keywords=20)
        extracted_terms = {k["keyword"].lower() for k in extracted}
        
        validation_result = {
            "extracted_keywords": [k["keyword"] for k in extracted],
            "validation": {}
        }
        
        # If expected keywords are provided, validate against them
        if expected_keywords:
            expected_lower = {k.lower() for k in expected_keywords}
            
            # Calculate precision, recall, and F1 score
            true_positives = len(extracted_terms.intersection(expected_lower))
            false_positives = len(extracted_terms - expected_lower)
            false_negatives = len(expected_lower - extracted_terms)
            
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            validation_result["validation"] = {
                "expected_keywords": expected_keywords,
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "missing_keywords": list(expected_lower - extracted_terms),
                "extra_keywords": list(extracted_terms - expected_lower)
            }
        
        return validation_result
    
    def _analyze_keyword_relevance(self, text: str, project_context: Optional[str] = None,
                                 domain: Optional[str] = None, max_keywords: int = 10) -> Dict[str, Any]:
        """Analyze keyword relevance in detail."""
        # Combine text and project context
        combined_text = text
        if project_context:
            combined_text = f"{text}\n\n{project_context}"
        
        # Tokenize the text
        tokens = self._tokenize(combined_text)
        
        # Count term frequency
        term_freq = Counter(tokens)
        
        # Filter out stop words and single characters
        filtered_terms = {term: freq for term, freq in term_freq.items() 
                         if term.lower() not in self.stop_words and len(term) > 1}
        
        # Sort by frequency
        sorted_terms = sorted(filtered_terms.items(), key=lambda x: x[1], reverse=True)
        
        # Get domain-specific keywords if domain is provided
        domain_keywords = []
        if domain and self._domain_keywords and domain in self._domain_keywords:
            domain_data = self._domain_keywords[domain]
            for subdomain, keywords in domain_data.items():
                for keyword in keywords:
                    if re.search(rf"\b{re.escape(keyword)}\b", combined_text, re.IGNORECASE):
                        relevance = self._calculate_keyword_relevance(combined_text, keyword)
                        domain_keywords.append({
                            "keyword": keyword,
                            "relevance": relevance,
                            "domain": domain,
                            "subdomain": subdomain
                        })
            
            domain_keywords = sorted(domain_keywords, key=lambda k: k["relevance"], reverse=True)
        
        # Prepare the analysis result
        analysis = {
            "top_keywords_by_frequency": [{"keyword": term, "frequency": freq} for term, freq in sorted_terms[:max_keywords]],
            "domain_specific_keywords": domain_keywords[:max_keywords] if domain_keywords else [],
            "text_statistics": {
                "total_tokens": len(tokens),
                "unique_tokens": len(set(tokens)),
                "detected_domain": domain
            }
        }
        
        return analysis


async def main():
    # Test the keyword extractor
    extractor = KeywordExtractor()
    
    # Sample text
    text = """
    Build a REST API for a weather application that fetches data from OpenWeatherMap API.
    The API should have endpoints for current weather, forecasts, and historical data.
    It should be implemented in Python using Flask or FastAPI, with proper authentication
    and rate limiting. The data should be cached to minimize external API calls.
    """
    
    # Extract keywords
    result = await extractor.execute(
        command="extract",
        text=text,
        max_keywords=15
    )
    
    print(result.output)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
