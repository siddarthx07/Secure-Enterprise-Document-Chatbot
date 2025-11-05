#!/usr/bin/env python3
"""
LLM Guardrails System for Enhanced Content Filtering

Implements Named Entity Recognition (NER) and LLM-based content validation
to strengthen rule-based judgment for sensitive financial data detection.
"""

import os
import json
import openai
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import re


class ContentSensitivity(Enum):
    """Content sensitivity levels"""
    SAFE = "safe"
    SENSITIVE_FINANCIAL = "sensitive_financial"
    SENSITIVE_PERSONAL = "sensitive_personal"
    HIGHLY_SENSITIVE = "highly_sensitive"


@dataclass
class NERResult:
    """Named Entity Recognition result"""
    entities: List[Dict[str, str]]  
    person_names: List[str]
    financial_terms: List[str]
    confidence: float


@dataclass
class ContentValidation:
    """Content validation result"""
    contains_sensitive_data: bool
    sensitivity_level: ContentSensitivity
    detected_issues: List[str]
    confidence: float
    reasoning: str


class LLMGuardrails:
    """
    Advanced LLM-based guardrails system with NER and content validation
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize the LLM Guardrails system"""
        self.model = model
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️ Warning: OPENAI_API_KEY not found. LLM Guardrails will use fallback methods.")
            self.client = None
        else:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                print("✅ LLM Guardrails initialized successfully")
            except Exception as e:
                print(f"❌ Failed to initialize LLM Guardrails: {e}")
                self.client = None
        
        # Statistics
        self.stats = {
            'total_validations': 0,
            'ner_calls': 0,
            'content_validations': 0,
            'sensitive_content_detected': 0,
            'errors': 0
        }
    
    def extract_entities(self, text: str) -> NERResult:
        """
        Extract named entities from text using LLM-based NER
        
        Args:
            text: Input text to analyze
            
        Returns:
            NERResult with extracted entities
        """
        self.stats['ner_calls'] += 1
        
        if not self.client:
            return self._fallback_ner(text)
        
        try:
            prompt = f"""
You are an expert Named Entity Recognition (NER) system for corporate content analysis.

Extract and classify entities from this text, focusing on:
1. PERSON - Individual names (employees, people)
2. FINANCIAL - Financial terms, amounts, salary-related words
3. ORGANIZATION - Company names, departments
4. ROLE - Job titles, positions

Text to analyze: "{text}"

Respond with JSON only:
{{
    "entities": [
        {{"text": "entity_text", "label": "PERSON|FINANCIAL|ORGANIZATION|ROLE", "confidence": 0.95}},
        ...
    ],
    "person_names": ["Name1", "Name2"],
    "financial_terms": ["salary", "compensation", "100k"],
    "overall_confidence": 0.90
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise NER system. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return NERResult(
                entities=result.get('entities', []),
                person_names=result.get('person_names', []),
                financial_terms=result.get('financial_terms', []),
                confidence=result.get('overall_confidence', 0.8)
            )
            
        except Exception as e:
            print(f"NER Error: {e}")
            self.stats['errors'] += 1
            return self._fallback_ner(text)
    
    def _fallback_ner(self, text: str) -> NERResult:
        """Fallback NER using regex patterns"""
        entities = []
        person_names = []
        financial_terms = []
        
        # Person name patterns
        person_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Full names
            r'\b[A-Z][a-z]+\b'  # Single names (when in salary context)
        ]
        
        # Financial term patterns
        financial_patterns = [
            r'\$[\d,]+', r'salary', r'compensation', r'pay', r'earn', r'income',
            r'annually', r'yearly', r'bracket', r'range', r'figure', r'100k', r'6-figure'
        ]
        
        # Extract person names
        for pattern in person_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match not in person_names:
                    person_names.append(match)
                    entities.append({
                        "text": match,
                        "label": "PERSON",
                        "confidence": 0.8
                    })
        
        # Extract financial terms
        for pattern in financial_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.lower() not in [term.lower() for term in financial_terms]:
                    financial_terms.append(match)
                    entities.append({
                        "text": match,
                        "label": "FINANCIAL",
                        "confidence": 0.7
                    })
        
        return NERResult(
            entities=entities,
            person_names=person_names,
            financial_terms=financial_terms,
            confidence=0.7
        )
    
    def validate_content_sensitivity(self, text: str, query_context: str = "") -> ContentValidation:
        """
        Validate if content contains sensitive financial data using LLM
        
        Args:
            text: Content to validate (response or query)
            query_context: Original query for context
            
        Returns:
            ContentValidation result
        """
        self.stats['content_validations'] += 1
        
        if not self.client:
            return self._fallback_content_validation(text, query_context)
        
        try:
            prompt = f"""
You are a corporate security expert analyzing content for sensitive financial information.

CRITICAL QUESTION: Does the content include sensitive financial data such as salaries, compensation, or personal financial information? (yes/no)

Content to analyze: "{text}"
Original query context: "{query_context}"

Analyze for:
1. Specific salary amounts (e.g., "$68,000", "125k")
2. Personal compensation details
3. Individual financial information
4. Salary comparisons or ranges
5. Financial data about specific employees

Respond with JSON only:
{{
    "contains_sensitive_data": true/false,
    "sensitivity_level": "safe|sensitive_financial|sensitive_personal|highly_sensitive",
    "detected_issues": ["issue1", "issue2"],
    "confidence": 0.95,
    "reasoning": "Brief explanation of why this is/isn't sensitive"
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a security expert. Always respond with valid JSON. Be conservative - when in doubt, mark as sensitive."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=400
            )
            
            result = json.loads(response.choices[0].message.content)
            
            if result['contains_sensitive_data']:
                self.stats['sensitive_content_detected'] += 1
            
            return ContentValidation(
                contains_sensitive_data=result['contains_sensitive_data'],
                sensitivity_level=ContentSensitivity(result['sensitivity_level']),
                detected_issues=result['detected_issues'],
                confidence=result['confidence'],
                reasoning=result['reasoning']
            )
            
        except Exception as e:
            print(f"Content Validation Error: {e}")
            self.stats['errors'] += 1
            return self._fallback_content_validation(text, query_context)
    
    def _fallback_content_validation(self, text: str, query_context: str = "") -> ContentValidation:
        """Fallback content validation using pattern matching"""
        detected_issues = []
        contains_sensitive = False
        sensitivity_level = ContentSensitivity.SAFE
        
        # Check for salary amounts
        salary_patterns = [
            r'\$[\d,]+',  # $68,000
            r'[\d,]+\s*(?:dollars|USD)',  # 68,000 dollars
            r'salary\s+(?:is|of|equals|:)\s+[\$€£¥]?\d+',  # salary is $68,000
            r'annual\s+salary\s+(?:is|of)\s+[\$€£¥]?\d+',  # annual salary is $68,000
        ]
        
        for pattern in salary_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                detected_issues.append(f"Salary amount detected: {pattern}")
                contains_sensitive = True
                sensitivity_level = ContentSensitivity.HIGHLY_SENSITIVE
        
        # Check for personal financial references
        personal_financial_patterns = [
            r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:makes|earns|salary|compensation)',
            r'(?:makes|earns)\s+\$[\d,]+',
            r'salary\s+of\s+\$[\d,]+'
        ]
        
        for pattern in personal_financial_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                detected_issues.append(f"Personal financial data detected: {pattern}")
                contains_sensitive = True
                if sensitivity_level == ContentSensitivity.SAFE:
                    sensitivity_level = ContentSensitivity.SENSITIVE_PERSONAL
        
        return ContentValidation(
            contains_sensitive_data=contains_sensitive,
            sensitivity_level=sensitivity_level,
            detected_issues=detected_issues,
            confidence=0.8,
            reasoning="Pattern-based fallback validation"
        )
    
    def comprehensive_analysis(self, query: str, response: str = "") -> Dict[str, Any]:
        """
        Perform comprehensive analysis combining NER and content validation
        
        Args:
            query: User query
            response: System response (optional)
            
        Returns:
            Complete analysis results
        """
        self.stats['total_validations'] += 1
        
        # Extract entities from query
        query_ner = self.extract_entities(query)
        
        # Validate query sensitivity
        query_validation = self.validate_content_sensitivity(query)
        
        # If response provided, analyze it too
        response_ner = None
        response_validation = None
        if response:
            response_ner = self.extract_entities(response)
            response_validation = self.validate_content_sensitivity(response, query)
        
        # Determine overall risk
        overall_risk = self._calculate_overall_risk(query_validation, response_validation)
        
        return {
            'query_analysis': {
                'ner': query_ner,
                'validation': query_validation
            },
            'response_analysis': {
                'ner': response_ner,
                'validation': response_validation
            } if response else None,
            'overall_risk': overall_risk,
            'recommendation': self._get_recommendation(overall_risk),
            'timestamp': self._get_timestamp()
        }
    
    def _calculate_overall_risk(self, query_val: ContentValidation, response_val: Optional[ContentValidation]) -> str:
        """Calculate overall risk level"""
        if response_val and response_val.contains_sensitive_data:
            return "HIGH_RISK"
        elif query_val.contains_sensitive_data:
            return "MEDIUM_RISK"
        else:
            return "LOW_RISK"
    
    def _get_recommendation(self, risk_level: str) -> str:
        """Get security recommendation based on risk level"""
        recommendations = {
            "HIGH_RISK": "BLOCK - Response contains sensitive financial data",
            "MEDIUM_RISK": "REVIEW - Query requests sensitive information",
            "LOW_RISK": "ALLOW - No sensitive content detected"
        }
        return recommendations.get(risk_level, "REVIEW")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get guardrails statistics"""
        return {
            **self.stats,
            'detection_rate': self.stats['sensitive_content_detected'] / max(self.stats['total_validations'], 1)
        }


# Example usage and testing
if __name__ == "__main__":
    # Test the guardrails system
    guardrails = LLMGuardrails()
    
    test_cases = [
        {
            'query': 'What is Lisa Park salary?',
            'response': 'Lisa Park annual salary is $68,000.'
        },
        {
            'query': 'How do I submit expense reports?',
            'response': 'You can submit expense reports through the HR portal.'
        },
        {
            'query': 'Is Siddarth Bandi in the $100k+ bracket?',
            'response': 'Yes, Siddarth Bandi falls within the 100k+ bracket with a salary of $98,000.'
        }
    ]
    
    print("=== LLM Guardrails Testing ===")
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        analysis = guardrails.comprehensive_analysis(case['query'], case['response'])
        
        print(f"Query: {case['query']}")
        print(f"Response: {case['response']}")
        print(f"Overall Risk: {analysis['overall_risk']}")
        print(f"Recommendation: {analysis['recommendation']}")
        
        if analysis['response_analysis']:
            validation = analysis['response_analysis']['validation']
            print(f"Sensitive Content Detected: {validation.contains_sensitive_data}")
            print(f"Issues: {validation.detected_issues}")
    
    print(f"\n=== Statistics ===")
    stats = guardrails.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}") 