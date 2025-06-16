#!/usr/bin/env python3
"""
Unified LLM Analyzer - Combines Intent Classification and Guardrails Analysis
for improved performance and reduced API calls.
"""

import os
import json
import openai
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List
import re
from datetime import datetime

class QueryIntent(Enum):
    """Possible query intents"""
    POLICY_PROCEDURE = "policy_procedure"
    FINANCIAL_DATA = "financial_data"
    PERSONAL_DATA = "personal_data"
    GENERAL_INFO = "general_info"
    UNKNOWN = "unknown"

class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    CRITICAL_RISK = "critical_risk"

@dataclass
class UnifiedAnalysis:
    """Combined result of intent classification and guardrails analysis"""
    # Intent Classification
    intent: QueryIntent
    confidence: float
    reasoning: str
    keywords: List[str]
    is_policy_related: bool
    is_financial_sensitive: bool
    
    # Guardrails Analysis
    overall_risk: RiskLevel
    contains_sensitive_data: bool
    detected_issues: List[str]
    recommendation: str
    
    # Unified Analysis
    should_allow: bool
    filter_action: str
    security_notes: str

class UnifiedLLMAnalyzer:
    """
    Unified LLM analyzer that combines intent classification and guardrails analysis
    into a single API call for improved performance.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️ Warning: OPENAI_API_KEY not found. Unified analyzer will use fallback methods.")
            self.client = None
        else:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                print("✅ Unified LLM Analyzer initialized successfully")
            except Exception as e:
                print(f"❌ Failed to initialize Unified LLM Analyzer: {e}")
                self.client = None
        
        # Performance statistics
        self.stats = {
            'total_analyses': 0,
            'unified_calls': 0,
            'fallback_calls': 0,
            'errors': 0,
            'avg_response_time': 0.0
        }
    
    def analyze_query_and_response(self, query: str, response: str = "", user_role: str = "Junior") -> UnifiedAnalysis:
        """
        Perform unified analysis of query intent and content security in a single LLM call.
        
        Args:
            query: User's query
            response: LLM response (optional, for response validation)
            user_role: User's role for access control
            
        Returns:
            UnifiedAnalysis with combined results
        """
        self.stats['total_analyses'] += 1
        
        if not self.client:
            return self._fallback_analysis(query, response, user_role)
        
        try:
            start_time = datetime.now()
            
            analysis = self._unified_llm_analysis(query, response, user_role)
            self.stats['unified_calls'] += 1
            
            # Update performance stats
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            self.stats['avg_response_time'] = (
                (self.stats['avg_response_time'] * (self.stats['unified_calls'] - 1) + response_time) 
                / self.stats['unified_calls']
            )
            
            return analysis
            
        except Exception as e:
            print(f"❌ Unified Analysis Error: {e}")
            self.stats['errors'] += 1
            return self._fallback_analysis(query, response, user_role)
    
    def _unified_llm_analysis(self, query: str, response: str, user_role: str) -> UnifiedAnalysis:
        """Perform unified LLM analysis combining classification and guardrails"""
        
        prompt = f"""
You are an expert AI security analyst for a corporate knowledge management system. 
Perform BOTH intent classification AND security analysis in a single comprehensive evaluation.

USER QUERY: "{query}"
USER RESPONSE: "{response}"
USER ROLE: {user_role}

TASK 1 - INTENT CLASSIFICATION:
Classify the query into ONE category:
1. POLICY_PROCEDURE - Company policies, procedures, how-to guides
2. FINANCIAL_DATA - Specific financial numbers, budgets, revenues  
3. PERSONAL_DATA - Individual employee information, salaries, personal details
4. GENERAL_INFO - General company information, non-sensitive data

TASK 2 - SECURITY ANALYSIS:
Assess security risks and sensitive content:
- Does content contain salary amounts, compensation details?
- Are there privacy concerns with employee data?
- Should access be restricted based on user role?

TASK 3 - UNIFIED DECISION:
Make a final recommendation: ALLOW, ALLOW_WITH_SCREENING, or DENY

Guidelines:
- PERSONAL_DATA queries about salaries = HIGH_RISK, usually DENY
- POLICY_PROCEDURE queries = LOW_RISK, usually ALLOW  
- Consider user role: Admin has more access than Junior
- Be conservative with financial/personal data

Respond with JSON only:
{{
    "intent_classification": {{
        "category": "POLICY_PROCEDURE|FINANCIAL_DATA|PERSONAL_DATA|GENERAL_INFO",
        "confidence": 0.95,
        "reasoning": "Why this category was chosen",
        "keywords": ["key", "terms"],
        "is_policy_related": true/false,
        "is_financial_sensitive": true/false
    }},
    "security_analysis": {{
        "overall_risk": "LOW_RISK|MEDIUM_RISK|HIGH_RISK|CRITICAL_RISK",
        "contains_sensitive_data": true/false,
        "detected_issues": ["issue1", "issue2"],
        "recommendation": "ALLOW|ALLOW_WITH_SCREENING|DENY",
        "security_notes": "Brief security assessment"
    }},
    "unified_decision": {{
        "should_allow": true/false,
        "filter_action": "allow|allow_with_screening|deny",
        "final_reasoning": "Combined analysis reasoning"
    }}
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a security expert and intent classifier. Always respond with valid JSON. Be thorough but concise."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=600
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Extract classification data
            classification = result['intent_classification']
            security = result['security_analysis']
            decision = result['unified_decision']
            
            return UnifiedAnalysis(
                # Intent Classification
                intent=QueryIntent(classification['category'].lower()),
                confidence=classification['confidence'],
                reasoning=classification['reasoning'],
                keywords=classification['keywords'],
                is_policy_related=classification['is_policy_related'],
                is_financial_sensitive=classification['is_financial_sensitive'],
                
                # Security Analysis
                overall_risk=RiskLevel(security['overall_risk'].lower()),
                contains_sensitive_data=security['contains_sensitive_data'],
                detected_issues=security['detected_issues'],
                recommendation=security['recommendation'],
                
                # Unified Decision
                should_allow=decision['should_allow'],
                filter_action=decision['filter_action'],
                security_notes=decision['final_reasoning']
            )
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            raise
        except Exception as e:
            print(f"LLM API error: {e}")
            raise
    
    def _fallback_analysis(self, query: str, response: str, user_role: str) -> UnifiedAnalysis:
        """Fallback analysis using regex patterns when LLM is unavailable"""
        self.stats['fallback_calls'] += 1
        
        query_lower = query.lower()
        
        # Simple pattern-based classification
        financial_keywords = ['salary', 'compensation', 'pay', 'earn', 'income', 'money', 'budget', 'revenue']
        policy_keywords = ['policy', 'procedure', 'how to', 'submit', 'deadline', 'guidelines']
        personal_keywords = ['salary', 'compensation', 'pay', 'earn', 'makes', 'income']
        
        # Determine intent
        if any(keyword in query_lower for keyword in personal_keywords) and any(re.search(r'\b[A-Z][a-z]+\b', query) for _ in [1]):
            intent = QueryIntent.PERSONAL_DATA
            is_financial_sensitive = True
            overall_risk = RiskLevel.HIGH_RISK
            should_allow = False
            filter_action = "deny"
        elif any(keyword in query_lower for keyword in policy_keywords):
            intent = QueryIntent.POLICY_PROCEDURE
            is_financial_sensitive = False
            overall_risk = RiskLevel.LOW_RISK
            should_allow = True
            filter_action = "allow"
        elif any(keyword in query_lower for keyword in financial_keywords):
            intent = QueryIntent.FINANCIAL_DATA
            is_financial_sensitive = True
            overall_risk = RiskLevel.MEDIUM_RISK
            should_allow = user_role in ['Manager', 'Admin']
            filter_action = "allow_with_screening" if should_allow else "deny"
        else:
            intent = QueryIntent.GENERAL_INFO
            is_financial_sensitive = False
            overall_risk = RiskLevel.LOW_RISK
            should_allow = True
            filter_action = "allow"
        
        return UnifiedAnalysis(
            # Intent Classification
            intent=intent,
            confidence=0.7,  # Lower confidence for fallback
            reasoning="Fallback pattern-based classification",
            keywords=[],
            is_policy_related=(intent == QueryIntent.POLICY_PROCEDURE),
            is_financial_sensitive=is_financial_sensitive,
            
            # Security Analysis
            overall_risk=overall_risk,
            contains_sensitive_data=is_financial_sensitive,
            detected_issues=["Potential sensitive content"] if is_financial_sensitive else [],
            recommendation=filter_action.upper(),
            
            # Unified Decision
            should_allow=should_allow,
            filter_action=filter_action,
            security_notes="Fallback analysis based on keyword patterns"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            **self.stats,
            'performance_improvement': f"{((2.0 - self.stats['avg_response_time']) / 2.0 * 100):.1f}%" if self.stats['avg_response_time'] > 0 else "N/A",
            'api_call_reduction': f"{(1 - (self.stats['unified_calls'] / max(self.stats['total_analyses'] * 2, 1))) * 100:.1f}%"
        }

# Example usage and testing
if __name__ == "__main__":
    analyzer = UnifiedLLMAnalyzer()
    
    # Test queries
    test_cases = [
        ("what is lisa park's salary", ""),
        ("how do I submit expense reports", ""),
        ("who is the HR manager", ""),
        ("what's our Q3 revenue", "")
    ]
    
    print("🧪 Testing Unified LLM Analyzer...")
    for query, response in test_cases:
        print(f"\n📝 Query: '{query}'")
        result = analyzer.analyze_query_and_response(query, response, "Admin")
        print(f"🎯 Intent: {result.intent.value}")
        print(f"🛡️ Risk: {result.overall_risk.value}")
        print(f"✅ Action: {result.filter_action}")
        print(f"📊 Confidence: {result.confidence}")
    
    print(f"\n📈 Performance Stats: {analyzer.get_stats()}") 