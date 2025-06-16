#!/usr/bin/env python3

import json
import hashlib
import time
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import openai
import os
from datetime import datetime, timedelta
import re

class QueryIntent(Enum):
    """Possible query intents"""
    POLICY_PROCEDURE = "policy_procedure"
    FINANCIAL_DATA = "financial_data"
    PERSONAL_DATA = "personal_data"
    GENERAL_INFO = "general_info"
    UNKNOWN = "unknown"

@dataclass
class IntentClassification:
    """Result of intent classification"""
    intent: QueryIntent
    confidence: float
    reasoning: str
    keywords: List[str]
    is_policy_related: bool
    is_financial_sensitive: bool

class QueryCache:
    """Simple in-memory cache for query classifications"""
    
    def __init__(self, max_size: int = 1000, ttl_hours: int = 24):
        self.cache = {}
        self.max_size = max_size
        self.ttl_hours = ttl_hours
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key from query"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def get(self, query: str) -> Optional[IntentClassification]:
        """Get cached classification if available and not expired"""
        cache_key = self._get_cache_key(query)
        
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            
            # Check if expired
            if datetime.now() - cached_item['timestamp'] < timedelta(hours=self.ttl_hours):
                return cached_item['classification']
            else:
                # Remove expired item
                del self.cache[cache_key]
        
        return None
    
    def store(self, query: str, classification: IntentClassification):
        """Store classification in cache"""
        cache_key = self._get_cache_key(query)
        
        # Remove oldest item if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
        
        self.cache[cache_key] = {
            'classification': classification,
            'timestamp': datetime.now()
        }
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1)
        }

class LLMIntentClassifier:
    """LLM-based intent classification system"""
    
    def __init__(self, model: str = "gpt-4o-mini", use_cache: bool = True):
        self.model = model
        self.cache = QueryCache() if use_cache else None
        
        # Initialize OpenAI client with error handling
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️ Warning: OPENAI_API_KEY not found. LLM classification will use fallback method.")
            self.client = None
        else:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                print("✅ OpenAI client initialized successfully")
            except Exception as e:
                print(f"❌ Failed to initialize OpenAI client: {e}")
                self.client = None
        
        # Statistics
        self.stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'llm_calls': 0,
            'classification_errors': 0,
            'fallback_calls': 0
        }
    
    def classify_intent(self, query: str) -> IntentClassification:
        """Classify the intent of a user query"""
        self.stats['total_queries'] += 1
        
        # Check cache first
        if self.cache:
            cached_result = self.cache.get(query)
            if cached_result:
                self.stats['cache_hits'] += 1
                return cached_result
        
        # Use LLM for classification if available
        if self.client:
            try:
                classification = self._llm_classify(query)
                self.stats['llm_calls'] += 1
                
                # Store in cache
                if self.cache:
                    self.cache.store(query, classification)
                
                return classification
                
            except Exception as e:
                print(f"LLM Classification Error: {e}")
                self.stats['classification_errors'] += 1
                
                # Fallback to rule-based classification
                return self._fallback_classify(query)
        else:
            # No OpenAI client available, use fallback
            self.stats['fallback_calls'] += 1
            return self._fallback_classify(query)
    
    def _llm_classify(self, query: str) -> IntentClassification:
        """Use LLM to classify query intent"""
        
        prompt = f"""
You are an expert at classifying employee queries for a corporate knowledge management system.

Classify this query into ONE of these categories:

1. POLICY_PROCEDURE - Questions about company policies, procedures, how-to guides, processes
   Examples: 
   - "How do I submit expense reports?"
   - "What's the vacation policy?"
   - "Can I claim expenses for professional development?"
   - "What's the deadline for submitting expenses?"
   - "Are personal expenses reimbursable?"

2. FINANCIAL_DATA - Requests for specific financial numbers, budgets, revenues, costs, actual amounts
   Examples:
   - "What was our Q3 revenue?"
   - "What's the marketing budget?"
   - "How much did we spend on office supplies?"

3. PERSONAL_DATA - Questions about individual employee information, salaries, personal details
   Examples:
   - "What's John's salary?"
   - "Who reports to Sarah?"
   - "What's my salary?" (if asking for specific amount)

4. GENERAL_INFO - General questions about company, people, departments, non-sensitive information
   Examples:
   - "Who is the HR manager?"
   - "What does the sales team do?"
   - "Who is Lisa Park?" (general info, not salary)

Key Guidelines:
- Questions about PROCEDURES/POLICIES for expenses = POLICY_PROCEDURE
- Questions about ACTUAL AMOUNTS/NUMBERS = FINANCIAL_DATA
- Focus on the INTENT, not just keywords
- "Expense" in context of procedures = POLICY_PROCEDURE
- "Expense" in context of amounts/budgets = FINANCIAL_DATA

Query: "{query}"

Respond with JSON only:
{{
    "category": "POLICY_PROCEDURE|FINANCIAL_DATA|PERSONAL_DATA|GENERAL_INFO",
    "confidence": 0.95,
    "reasoning": "Brief explanation of why this category was chosen",
    "keywords": ["key", "terms", "identified"],
    "is_policy_related": true/false,
    "is_financial_sensitive": true/false
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise query classifier. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return IntentClassification(
                intent=QueryIntent(result['category'].lower()),
                confidence=result['confidence'],
                reasoning=result['reasoning'],
                keywords=result['keywords'],
                is_policy_related=result['is_policy_related'],
                is_financial_sensitive=result['is_financial_sensitive']
            )
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Raw response: {response.choices[0].message.content}")
            raise
        except Exception as e:
            print(f"LLM API error: {e}")
            raise
    
    def _fallback_classify(self, query: str) -> IntentClassification:
        """Fallback rule-based classification when LLM fails"""
        query_lower = query.lower()
        
        # Enhanced keyword-based fallback with expense policy detection
        policy_keywords = [
            'how to', 'how do i', 'policy', 'procedure', 'process', 'submit', 'deadline', 'guidelines',
            'can i claim', 'are expenses reimbursable', 'expense report', 'reimbursement', 'approval'
        ]
        financial_keywords = ['budget', 'revenue', 'profit', 'cost', 'spent', 'total', 'amount', 'q3', 'quarterly']
        personal_keywords = ['salary', 'compensation', 'pay', 'earn', 'makes', 'income', 'make', 'annually', 'yearly']
        
        # Check for expense policy patterns specifically
        expense_policy_patterns = [
            'how do i submit expense', 'can i claim expenses', 'are personal expenses reimbursable',
            'what expenses can i claim', 'deadline for submitting', 'expense approval', 'reimbursement process'
        ]
        
        # Enhanced salary query patterns - HIGHEST PRIORITY CHECK
        salary_query_patterns = [
            'how much does', 'what does', 'how much money does', 'what is', 'salary',
            'tell me what', 'annually', 'yearly', 'bracket', 'figure range', '100k+', '$100k'
        ]
        
        # Specific salary context patterns (highest priority)
        salary_context_patterns = [
            r'how much does .+ make',
            r'what does .+ earn',
            r'tell me what .+ annually',
            r'what .+ annually',
            r'.+ salary',
            r'.+ in the .+ bracket',
            r'.+ in the .+ range',
            r'does .+ fall in',
            r'is .+ in the'
        ]
        
        # Check for person names in salary context (enhanced detection)
        person_name_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Full names like "Lisa Park"
            r'\b[A-Z][a-z]+\b'  # Single names like "Lisa"
        ]
        
        # PRIORITY 1: Check for salary queries with person references
        has_person_reference = any(re.search(pattern, query) for pattern in person_name_patterns)
        has_salary_context = any(re.search(pattern, query_lower) for pattern in salary_context_patterns)
        has_salary_keywords = any(keyword in query_lower for keyword in salary_query_patterns)
        
        # PRIORITY 1: Check for salary queries with person references (HIGHEST PRIORITY)
        if has_person_reference and (has_salary_context or has_salary_keywords):
            intent = QueryIntent.PERSONAL_DATA
            is_policy = False
            is_financial_sensitive = True
            reasoning = "Detected salary query about person (fallback classification)"
        
        # PRIORITY 2: Check for expense policy patterns
        elif any(pattern in query_lower for pattern in expense_policy_patterns) or any(keyword in query_lower for keyword in policy_keywords):
            intent = QueryIntent.POLICY_PROCEDURE
            is_policy = True
            is_financial_sensitive = False
            reasoning = "Detected policy/procedure query (fallback classification)"
        
        # PRIORITY 3: Check for financial data queries
        elif any(keyword in query_lower for keyword in financial_keywords):
            intent = QueryIntent.FINANCIAL_DATA
            is_policy = False
            is_financial_sensitive = True
            reasoning = "Detected financial data query (fallback classification)"
        
        # PRIORITY 4: Check for personal data queries
        elif any(keyword in query_lower for keyword in personal_keywords):
            intent = QueryIntent.PERSONAL_DATA
            is_policy = False
            is_financial_sensitive = True
            reasoning = "Detected personal data query (fallback classification)"
        
        # DEFAULT: General info
        else:
            intent = QueryIntent.GENERAL_INFO
            is_policy = False
            is_financial_sensitive = False
            reasoning = "General information query (fallback classification)"
        
        return IntentClassification(
            intent=intent,
            confidence=0.7,  # Slightly higher confidence for enhanced fallback
            reasoning=reasoning,
            keywords=[],
            is_policy_related=is_policy,
            is_financial_sensitive=is_financial_sensitive
        )
    
    def get_stats(self) -> Dict:
        """Get classification statistics"""
        total = max(self.stats['total_queries'], 1)
        
        stats = {
            'total_queries': self.stats['total_queries'],
            'cache_hit_rate': self.stats['cache_hits'] / total,
            'llm_call_rate': self.stats['llm_calls'] / total,
            'error_rate': self.stats['classification_errors'] / total,
            'cache_stats': self.cache.get_stats() if self.cache else None
        }
        
        return stats
    
    def batch_classify(self, queries: List[str]) -> List[IntentClassification]:
        """Classify multiple queries (can be optimized for batch processing)"""
        results = []
        
        for query in queries:
            classification = self.classify_intent(query)
            results.append(classification)
        
        return results

# Example usage and testing
if __name__ == "__main__":
    # Test the classifier
    classifier = LLMIntentClassifier()
    
    test_queries = [
        "How do I submit expense reports?",
        "Can I claim expenses for professional development courses?",
        "What was our Q3 revenue?",
        "What's John's salary?",
        "Who is the HR manager?",
        "Are personal expenses reimbursable?",
        "What's the deadline for submitting business expenses?"
    ]
    
    print("=== LLM Intent Classification Test ===")
    for query in test_queries:
        classification = classifier.classify_intent(query)
        print(f"\nQuery: '{query}'")
        print(f"Intent: {classification.intent.value}")
        print(f"Confidence: {classification.confidence}")
        print(f"Policy Related: {classification.is_policy_related}")
        print(f"Reasoning: {classification.reasoning}")
    
    print(f"\n=== Statistics ===")
    stats = classifier.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}") 