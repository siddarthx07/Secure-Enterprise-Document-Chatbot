"""
Financial Content Filter for TechConsult Knowledge Chatbot

Provides intelligent filtering and rule-based judgment for financial information
based on user roles and query context.
"""

import re
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union
from enum import Enum

# Import LLM modules
try:
    from llm_modules.llm_intent_classifier import LLMIntentClassifier, QueryIntent, IntentClassification
    LLM_AVAILABLE = bool(os.getenv('OPENAI_API_KEY'))
except ImportError:
    LLM_AVAILABLE = False

try:
    from llm_modules.llm_guardrails import LLMGuardrails
    GUARDRAILS_AVAILABLE = LLM_AVAILABLE
except ImportError:
    GUARDRAILS_AVAILABLE = False

try:
    from llm_modules.llm_unified_analyzer import UnifiedLLMAnalyzer, UnifiedAnalysis
except ImportError:
    pass


class FilterAction(Enum):
    """Possible actions the filter can take"""
    ALLOW = "allow"
    ALLOW_WITH_REDACTION = "allow_with_redaction"
    ALLOW_WITH_EMAIL_CHECK = "allow_with_email_check"
    ALLOW_WITH_SCREENING = "allow_with_screening"
    DENY = "deny"


class FinancialContentFilter:
    """
    Implements intelligent filtering and rule-based judgment for financial information
    in queries and responses.
    """
    
    def __init__(self, audit_log_enabled: bool = True, use_llm_classification: bool = True, 
                 use_guardrails: bool = True, use_unified_analyzer: bool = True):
        """Initialize the financial content filter with detection patterns"""
        self.audit_log_enabled = audit_log_enabled
        self.use_llm_classification = use_llm_classification and LLM_AVAILABLE
        self.use_guardrails = use_guardrails and GUARDRAILS_AVAILABLE
        self.use_unified_analyzer = use_unified_analyzer and LLM_AVAILABLE
        
        # Initialize Unified LLM Analyzer (preferred method)
        if self.use_unified_analyzer:
            try:
                self.unified_analyzer = UnifiedLLMAnalyzer()
                self.use_llm_classification = False
                self.use_guardrails = False
                self.llm_classifier = None
                self.guardrails = None
            except Exception:
                self.use_unified_analyzer = False
                self.unified_analyzer = None
        else:
            self.unified_analyzer = None
        
        # Initialize LLM classifier if available and enabled
        if self.use_llm_classification and not self.use_unified_analyzer:
            try:
                self.llm_classifier = LLMIntentClassifier()
            except Exception:
                self.use_llm_classification = False
                self.llm_classifier = None
        else:
            self.llm_classifier = None
        
        # Initialize LLM Guardrails if available and enabled
        if self.use_guardrails and not self.use_unified_analyzer:
            try:
                self.guardrails = LLMGuardrails()
            except Exception:
                self.use_guardrails = False
                self.guardrails = None
        else:
            self.guardrails = None
        
        # Financial pattern detection
        self.financial_patterns = [
            r'(?:[\$€£¥])[\d,.]+',
            r'\d+(?:\.\d+)?\s*(?:dollars|euros|pounds)',
            r'\d+(?:\.\d+)?[kKmMbB]\b',
            r'(?:revenue|profit|budget|expense|cost)\s+of\s+[\$€£¥]?\d+',
            r'(?:revenue|profit|budget|expense|cost)\s+[\$€£¥]?\d+',
            r'salary\s+(?:is|of|equals|:)\s+[\$€£¥]?\d+[,.]?\d*',
            r'annual\s+salary\s+(?:is|of|equals|:)\s+[\$€£¥]?\d+[,.]?\d*',
            r'makes\s+[\$€£¥]?\d+[,.]?\d*\s*(?:per|a|an)?\s*(?:year|month|week|annually)?',
            r'earns\s+[\$€£¥]?\d+[,.]?\d*\s*(?:per|a|an)?\s*(?:year|month|week|annually)?',
            r'paid\s+[\$€£¥]?\d+[,.]?\d*\s*(?:per|a|an)?\s*(?:year|month|week|annually)?',
            r'with\s+an?\s+annual\s+salary\s+of\s+[\$€£¥]?\d+[,.]?\d*',
            r'salary\s+of\s+[\$€£¥]?\d+[,.]?\d*',
            r'compensation\s+of\s+[\$€£¥]?\d+[,.]?\d*',
            r'income\s+of\s+[\$€£¥]?\d+[,.]?\d*',
            r'[\$€£¥]\d{2,3},\d{3}',
            r'[\$€£¥]\d{2,3}\.\d{3}',
            r'\d{2,3},\d{3}\s*(?:dollars|USD|\$)',
        ]
        
        self.compiled_financial_patterns = [re.compile(p, re.IGNORECASE) for p in self.financial_patterns]
        
        # Self-reference detection patterns
        self.self_reference_patterns = [
            r'\bmy\s+(?:salary|compensation|pay|income|earnings|money)\b',
            r'\bi\s+(?:make|earn|get\s+paid|receive|am\s+paid)\b',
            r'\bhow\s+much\s+(?:do\s+)?i\s+(?:make|earn|get\s+paid|receive)\b',
            r'what\s+(?:is|\'s)\s+my\s+(?:salary|compensation|pay|income|earnings)\b',
            r'how\s+much\s+(?:money|salary|compensation)\s+do\s+i\s+(?:make|earn|get)\b'
        ]
        self.compiled_self_patterns = [re.compile(p, re.IGNORECASE) for p in self.self_reference_patterns]
        
        # Person reference detection patterns (ordered from most specific to least specific)
        self.person_reference_patterns = [
            r'what\s+is\s+(?:the\s+)?salary of ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'whats?\s+(?:the\s+)?salary of ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'salary of ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'(?:the\s+)?salary of ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) salary',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* salary',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) compensation',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) pay',
            r'how much does ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) make',
            r'what is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* salary',
            r'what does ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) earn',
            r'how much does ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) earn',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\'s income',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) income',
            r'how much money does ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) make',
            r'what does ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) take home',
            r'how much does ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) take home',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* take home',
            r'what is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* take home',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) take home (?:pay|salary|income)',
            r'what does ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) (?:make|earn|get)\s+(?:monthly|weekly|daily)',
            r'how much does ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) (?:make|earn|get)\s+(?:monthly|weekly|daily)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* (?:monthly|weekly|daily) (?:pay|salary|income)',
            r'what is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* (?:monthly|weekly|daily) (?:pay|salary|income)',
            r'who is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'tell me about ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'information about ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'how much does ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) earn annually',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) earn annually',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) earns annually',
            r'what does ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) earn annually',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* pay details',
            r'show me ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* pay details',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* compensation package',
            r'what[\'s]* ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* compensation package',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* total remuneration',
            r'tell me ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s]* total remuneration',
            r'tell me what ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) annually',
            r'what ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) annually',
            r'is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) in the .+ bracket',
            r'does ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) fall in',
        ]
        self.compiled_person_patterns = [re.compile(p, re.IGNORECASE) for p in self.person_reference_patterns]
        
        # Aggregate salary query patterns
        self.aggregate_salary_patterns = [
            r'who\s+(?:makes|earns|gets|is paid|receives)\s+(?:the\s+)?(?:most|highest|greatest|least|lowest|minimum|maximum)',
            r'who\s+(?:makes|earns|gets|is paid|receives)\s+(?:less|more)\s+than',
            r'who\s+(?:makes|earns|gets|is paid|receives)\s+(?:below|above|under|over)',
            r'who\s+(?:makes|earns|gets|is paid|receives)\s+(?:less|more)\s+than\s+(?:the\s+)?(?:average|avg|median)',
            r'who\s+(?:makes|earns|gets|is paid|receives)\s+(?:below|above|under|over)\s+(?:the\s+)?(?:average|avg|median)',
            r'who\s+(?:makes|earns|gets|is paid|receives)\s+the\s+(?:less|more)\s+than',
            r'who\s+(?:makes|earns|gets|is paid|receives)\s+the\s+(?:less|more)\s+than\s+(?:the\s+)?(?:average|avg|median)',
            r'who\s+(?:makes|earns|gets|is paid|receives)\s+the\s+(?:least|most)',
            r'who\s+(?:is\s+paid|gets\s+paid)\s+(?:the\s+)?(?:most|highest|least|lowest)',
            r'who\s+(?:is\s+paid|gets\s+paid)\s+(?:less|more)\s+than',
            r'who\s+(?:is\s+paid|gets\s+paid)\s+(?:below|above|under|over)',
            r'who\s+(?:makes|earns|gets|is paid|receives)\s+(?:the\s+)?(?:average|avg|median)',
            r'who\s+(?:makes|earns|gets|is paid|receives)\s+(?:around|about|approximately)\s+(?:the\s+)?(?:average|avg|median)',
            r'highest\s+(?:paid|salary|earner)',
            r'lowest\s+(?:paid|salary|earner)',
            r'(?:maximum|minimum)\s+salary',
            r'(?:most|least)\s+(?:paid|salary)',
            r'average\s+salary',
            r'median\s+salary',
            r'salary\s+(?:range|distribution|statistics)',
            r'who\s+earns\s+[\$€£¥]?\d+[,.]?\d*',
            r'who\s+makes\s+[\$€£¥]?\d+[,.]?\d*',
            r'who\s+gets\s+paid\s+[\$€£¥]?\d+[,.]?\d*',
            r'who\s+receives\s+[\$€£¥]?\d+[,.]?\d*',
            r'which\s+employee\s+(?:earns|makes|gets)\s+[\$€£¥]?\d+[,.]?\d*',
            r'employee\s+(?:earning|making)\s+[\$€£¥]?\d+[,.]?\d*',
            r'compare\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+salary',
            r'is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+paid\s+fairly',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+salary\s+(?:compared|vs)',
            r'highest\s+salary\s+in\s+(?:sales|marketing|engineering)',
            r'which\s+employee\s+has\s+the\s+highest\s+salary',
            r'who\s+earns\s+(?:the\s+)?(?:most|least|highest|lowest)\s+in\s+(?:sales|marketing|engineering|hr)',
            r'highest\s+earner\s+in\s+(?:sales|marketing|engineering|hr)',
            r'lowest\s+earner\s+in\s+(?:sales|marketing|engineering|hr)'
        ]
        self.compiled_aggregate_patterns = [re.compile(p, re.IGNORECASE) for p in self.aggregate_salary_patterns]
        
        # Financial terms for detection
        self.financial_keywords = [
            'salary', 'compensation', 'pay', 'earn', 'income', 'make', 'makes',
            'revenue', 'profit', 'budget', 'expense', 'cost',
            'dollar', 'euro', 'pound', 'money', 'cash',
            'financial', 'finance', 'fiscal', 'annually', 'yearly',
            'bracket', 'range', '100k', '$100k', 'figure',
            'take home', 'monthly', 'weekly', 'daily', 'paid',
            'paycheck', 'wage', 'wages', 'earnings', 'remuneration'
        ]
        
        # Safe policy related terms
        self.safe_policy_contexts = [
            'leave policy', 'vacation policy', 'time off', 'pto policy',
            'holiday policy', 'annual leave', 'sick leave', 'days per month',
            'days per year', 'paid leave', 'unpaid leave', 'maternity leave',
            'paternity leave', 'vacation days', 'how many days', 'days off',
            'holidays', 'policy', 'procedure', 'benefit', 'health insurance',
            'medical', 'dental', 'vision', 'retirement', '401k'
        ]
        
        # Expense-related policy patterns
        self.expense_policy_patterns = [
            r'how\s+(?:do\s+i|to)\s+submit\s+expense\s+reports?',
            r'expense\s+report\s+(?:process|procedure|submission|policy)',
            r'submit\s+(?:an?\s+)?expense\s+reports?',
            r'how\s+to\s+(?:file|submit|complete)\s+expense',
            r'how\s+(?:do\s+i|to)\s+file\s+expense\s+reports?',
            r'can\s+i\s+submit\s+(?:an?\s+)?expense\s+without\s+(?:manager\s+)?approval',
            r'(?:do\s+i\s+need|need)\s+(?:manager\s+)?approval\s+for\s+expense',
            r'expense\s+approval\s+(?:process|procedure|policy|requirements?)',
            r'who\s+should\s+approve\s+my\s+expense\s+report',
            r'who\s+approves?\s+expense\s+reports?',
            r'(?:are|is)\s+(?:personal\s+)?expenses?\s+reimbursable',
            r'what\s+expenses?\s+(?:are\s+)?(?:can\s+be\s+)?reimbursed?',
            r'(?:which|what\s+kind\s+of|what\s+types?\s+of)\s+expenses?\s+(?:can\s+i\s+)?(?:claim|get\s+reimbursed)',
            r'reimbursable\s+expenses?',
            r'expense\s+reimbursement\s+(?:process|procedure|policy|eligibility)',
            r'what\s+(?:are\s+the\s+)?acceptable\s+expense\s+categories',
            r'acceptable\s+expense\s+categories\s+for\s+reimbursement',
            r'(?:what\'?s\s+the\s+)?deadline\s+to\s+submit\s+(?:my\s+)?expenses?',
            r'are\s+alcohol\s+expenses?\s+reimbursed?',
            r'what\s+qualifies\s+as\s+(?:a\s+)?reimbursable\s+business\s+expense',
            r'can\s+i\s+get\s+reimbursed\s+for\s+remote\s+work\s+equipment',
            r'(?:business\s+travel|travel)\s+expense\s+(?:policy|procedure|reimbursement)',
            r'what\s+(?:kind\s+of\s+)?expenses?\s+(?:can\s+i\s+)?(?:claim|submit)\s+for\s+(?:business\s+)?travel',
            r'travel\s+(?:related\s+)?expense\s+(?:policy|guidelines)',
            r'(?:what\'?s\s+the\s+)?deadline\s+for\s+(?:submitting|filing)\s+(?:business\s+)?expenses?',
            r'what\s+is\s+the\s+(?:submission\s+)?deadline\s+for\s+(?:business\s+)?expenses?',
            r'when\s+(?:do\s+i\s+need\s+to|should\s+i)\s+submit\s+expense\s+reports?',
            r'expense\s+(?:submission\s+)?deadline',
            r'how\s+long\s+(?:do\s+i\s+have\s+)?to\s+submit\s+expenses?',
            r'how\s+(?:do\s+i|to)\s+track\s+(?:my\s+)?(?:submitted\s+)?expense\s+reports?',
            r'track\s+(?:my\s+)?(?:submitted\s+)?expense\s+reports?',
            r'status\s+of\s+(?:my\s+)?expense\s+reports?',
            r'check\s+(?:my\s+)?expense\s+report\s+status',
            r'expense\s+(?:form|forms|submission|guidelines|policy)',
            r'reimbursement\s+(?:process|procedure|policy)',
            r'business\s+expense\s+(?:policy|procedure|guidelines)'
        ]
        self.compiled_expense_policy_patterns = [re.compile(p, re.IGNORECASE) for p in self.expense_policy_patterns]

    def analyze_query(self, query: str, user_email: str, user_role: str) -> Dict[str, Any]:
        """Analyze a user query to determine if it contains sensitive financial information requests"""
        query_lower = query.lower()
        
        analysis = {
            "original_query": query,
            "is_financial": False,
            "is_salary_related": False,
            "is_self_data_request": False,
            "is_about_person": False,
            "is_person_salary_query": False,
            "is_aggregate_salary_query": False,
            "target_person": None,
            "is_policy_context": False,
            "user_email": user_email,
            "user_role": user_role,
            "llm_classification": None
        }
        
        # Check for expense policy patterns first
        for pattern in self.compiled_expense_policy_patterns:
            if pattern.search(query):
                analysis["is_policy_context"] = True
                analysis["is_financial"] = False
                analysis["is_salary_related"] = False
                return analysis
        
        # Check for other safe policy contexts
        safe_policy_contexts = ["policy", "policies", "guidelines", "rules", "procedures"]
        has_safe_context = any(safe_context in query_lower for safe_context in safe_policy_contexts)
        if has_safe_context and not any(keyword in query_lower for keyword in ["salary", "pay", "wage", "compensation", "revenue", "profit"]):
            analysis["is_policy_context"] = True
            analysis["is_financial"] = False
            analysis["is_salary_related"] = False
            return analysis
        
        # Check for aggregate salary queries
        if any(pattern.search(query) for pattern in self.compiled_aggregate_patterns):
            analysis["is_aggregate_salary_query"] = True
            analysis["is_salary_related"] = True
            analysis["is_financial"] = True
            return analysis
        
        # Fast path for non-financial queries
        has_financial_keywords = any(keyword in query_lower for keyword in self.financial_keywords)
        has_financial_patterns = any(pattern.search(query) for pattern in self.compiled_financial_patterns[:5])
        
        if not has_financial_keywords and not has_financial_patterns:
            self._extract_person_details(query, analysis)
            analysis["is_financial"] = False
            analysis["is_salary_related"] = False
            return analysis
        
        # Use unified LLM analyzer if available
        if self.use_unified_analyzer and self.unified_analyzer:
            try:
                unified_result = self.unified_analyzer.analyze_query_and_response(query, "", user_role)
                analysis["llm_classification"] = IntentClassification(
                    intent=unified_result.intent,
                    confidence=unified_result.confidence,
                    reasoning=unified_result.reasoning,
                    keywords=unified_result.keywords,
                    is_policy_related=unified_result.is_policy_related,
                    is_financial_sensitive=unified_result.is_financial_sensitive
                )
                
                if unified_result.intent.value == 'policy_procedure':
                    analysis["is_policy_context"] = True
                    analysis["is_financial"] = False
                elif unified_result.intent.value == 'financial_data':
                    analysis["is_financial"] = True
                elif unified_result.intent.value == 'personal_data':
                    analysis["is_financial"] = True
                    analysis["is_salary_related"] = True
                    analysis["is_about_person"] = True
                
                if unified_result.confidence > 0.8:
                    self._extract_person_details(query, analysis)
                    self._check_self_reference(query, analysis)
                    
                    # CRITICAL FIX: For high-confidence personal data queries, ensure salary detection flags are set
                    if unified_result.intent.value == 'personal_data' and unified_result.is_financial_sensitive:
                        # Check if this is specifically a salary query about a person
                        salary_keywords = ["salary", "compensation", "pay", "earn", "income", "money", "wage", "wages"]
                        if any(keyword in query_lower for keyword in salary_keywords):
                            analysis["is_salary_related"] = True
                            analysis["is_financial"] = True
                            
                            # If we found a person and it's salary-related, mark as person salary query
                            if analysis.get("is_about_person") and analysis.get("target_person"):
                                analysis["is_person_salary_query"] = True
                    
                    return analysis
                    
            except Exception:
                pass
        
        # Fallback LLM classification
        elif self.use_llm_classification and self.llm_classifier:
            try:
                llm_result = self.llm_classifier.classify_intent(query)
                analysis["llm_classification"] = llm_result
                
                if llm_result.intent.value == 'policy_procedure':
                    analysis["is_policy_context"] = True
                    analysis["is_financial"] = False
                elif llm_result.intent.value == 'financial_data':
                    analysis["is_financial"] = True
                elif llm_result.intent.value == 'personal_data':
                    analysis["is_financial"] = True
                    analysis["is_salary_related"] = True
                    analysis["is_about_person"] = True
                
                if llm_result.confidence > 0.8:
                    self._extract_person_details(query, analysis)
                    self._check_self_reference(query, analysis)
                    
                    # CRITICAL FIX: For high-confidence personal data queries, ensure salary detection flags are set
                    if llm_result.intent.value == 'personal_data' and llm_result.is_financial_sensitive:
                        # Check if this is specifically a salary query about a person
                        salary_keywords = ["salary", "compensation", "pay", "earn", "income", "money", "wage", "wages"]
                        if any(keyword in query_lower for keyword in salary_keywords):
                            analysis["is_salary_related"] = True
                            analysis["is_financial"] = True
                            
                            # If we found a person and it's salary-related, mark as person salary query
                            if analysis.get("is_about_person") and analysis.get("target_person"):
                                analysis["is_person_salary_query"] = True
                    
                    return analysis
                    
            except Exception:
                pass
        
        # Regex-based analysis
        if has_financial_keywords:
            analysis["is_financial"] = True
        
        # Check for financial patterns
        for pattern in self.compiled_financial_patterns:
            if pattern.search(query):
                analysis["is_financial"] = True
                analysis["is_salary_related"] = True
        
        # Check for salary-related keywords
        if any(keyword in query_lower for keyword in ["salary", "compensation", "pay", "earn", "income", "money"]):
            analysis["is_salary_related"] = True
        
        # Check for self-reference patterns
        for pattern in self.compiled_self_patterns:
            if pattern.search(query):
                analysis["is_self_data_request"] = True
                break
        
        # Additional self-reference detection
        self_identity_patterns = [
            r'\bwho\s+am\s+i\b', r'\bwho\s+i\s+am\b', r'\btell\s+me\s+about\s+myself\b',
            r'\bmy\s+information\b', r'\bmy\s+details\b', r'\babout\s+me\b',
            r'\bwhats?\s+my\s+name\b', r'\bwhat\s+is\s+my\s+name\b', r'\bmy\s+name\b'
        ]
        
        for pattern in self_identity_patterns:
            if re.search(pattern, query_lower):
                analysis["is_self_data_request"] = True
                break
        
        # Check for person-specific queries
        for pattern in self.compiled_person_patterns:
            match = pattern.search(query)
            if match:
                analysis["is_about_person"] = True
                if match.groups():
                    analysis["target_person"] = match.group(1).strip()
                break
        
        # Determine if this is a salary query about a specific person
        if analysis["is_about_person"] and analysis["is_salary_related"]:
            analysis["is_person_salary_query"] = True
        
        # Look for potential names if not found
        if not analysis["target_person"]:
            name_pattern = re.compile(r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b')
            name_matches = name_pattern.finditer(query)
            for match in name_matches:
                if analysis["is_salary_related"]:
                    analysis["target_person"] = match.group(1)
                    analysis["is_about_person"] = True
                    break
        
        # Ensure financial flag is set based on multiple indicators
        if not analysis["is_financial"]:
            if any(pattern.search(query) for pattern in self.compiled_financial_patterns):
                analysis["is_financial"] = True
            
            if analysis["is_salary_related"] and (analysis["is_self_data_request"] or analysis["is_about_person"]) and not analysis["is_policy_context"]:
                analysis["is_financial"] = True
        
        return analysis
    
    def _extract_person_details(self, query: str, analysis: Dict[str, Any]):
        """Extract person details from query"""
        for pattern in self.compiled_person_patterns:
            match = pattern.search(query)
            if match:
                analysis["is_about_person"] = True
                if match.groups():
                    analysis["target_person"] = match.group(1).strip()
                else:
                    name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', match.group(0), re.IGNORECASE)
                    if name_match:
                        analysis["target_person"] = name_match.group(1)
                break
    
    def _check_self_reference(self, query: str, analysis: Dict[str, Any]):
        """Check for self-reference patterns in query"""
        for pattern in self.compiled_self_patterns:
            if pattern.search(query):
                analysis["is_self_data_request"] = True
                break

    def determine_action(self, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the appropriate filtering action based on query analysis and user role"""
        # Policy related queries: always allow
        if query_analysis.get("is_policy_context", False):
            return {
                "action": FilterAction.ALLOW,
                "reason": "Policy-related query - no financial data filtering needed"
            }
        
        # Non-financial queries: allow with light screening
        if not query_analysis.get("is_financial", False):
            # Check if this is a query about a person that might return salary information
            query_lower = query_analysis["original_query"].lower()
            person_query_patterns = [
                r'\bwho\s+is\s+[a-z]+\s+[a-z]+\b',
                r'\btell\s+me\s+about\s+[a-z]+\s+[a-z]+\b',
                r'\bwhat\s+do\s+you\s+know\s+about\s+[a-z]+\s+[a-z]+\b',
                r'\binfo\s+on\s+[a-z]+\s+[a-z]+\b',
                r'\bdetails\s+about\s+[a-z]+\s+[a-z]+\b',
            ]
            
            for pattern in person_query_patterns:
                if re.search(pattern, query_lower):
                    return {
                        "action": FilterAction.ALLOW_WITH_SCREENING,
                        "reason": "Person information query - will be screened for salary content"
                    }
            
            return {
                "action": FilterAction.ALLOW_WITH_SCREENING,
                "reason": "General query - will be screened for sensitive content"
            }
        
        # Aggregate salary queries: always deny
        if query_analysis.get("is_aggregate_salary_query", False):
            return {
                "action": FilterAction.DENY,
                "reason": "Aggregate salary queries are not permitted for any user role"
            }
        
        # Self-data requests: allow with email verification
        if query_analysis.get("is_self_data_request", False):
            return {
                "action": FilterAction.ALLOW_WITH_EMAIL_CHECK,
                "reason": "Self-data request - will verify user identity in documents"
            }
        
        # Person-specific salary queries: apply role-based rules
        if query_analysis.get("is_person_salary_query", False):
            user_role = query_analysis.get("user_role", "").lower()
            target_person = query_analysis.get("target_person", "Unknown")
            
            if user_role in ["admin", "manager"]:
                return {
                    "action": FilterAction.ALLOW_WITH_REDACTION,
                    "reason": f"Admin/Manager access to {target_person}'s information with salary redaction"
                }
            else:
                return {
                    "action": FilterAction.DENY,
                    "reason": f"Insufficient privileges to access {target_person}'s salary information"
                }
        
        # Special handling for Junior/Senior users - allow company financial data with screening
        user_role = query_analysis.get("user_role", "").lower()
        if user_role in ["junior", "senior"]:
            # Only block actual person-specific salary queries, allow company financial data with screening
            if query_analysis.get("is_person_salary_query", False) or query_analysis.get("is_aggregate_salary_query", False):
                return {
                    "action": FilterAction.DENY,
                    "reason": "Access to salary information is restricted"
                }
            else:
                return {
                    "action": FilterAction.ALLOW_WITH_SCREENING,
                    "reason": f"{query_analysis['user_role']} role - general content screening applied"
                }
        
        # General financial queries: apply role-based rules for Manager/Admin
        if query_analysis.get("is_financial", False):
            if user_role in ["admin", "manager"]:
                # Distinguish between company financial data and individual salary data
                if query_analysis.get("is_salary_related", False) and query_analysis.get("is_about_person", False):
                    # Individual salary data - apply redaction even for Manager/Admin
                    return {
                        "action": FilterAction.ALLOW_WITH_REDACTION,
                        "reason": f"{query_analysis['user_role']} access to individual information with salary redaction"
                    }
                else:
                    # Company financial data (quarterly earnings, revenue, etc.) - allow for Manager/Admin
                    return {
                        "action": FilterAction.ALLOW,
                        "reason": f"{query_analysis['user_role']} accessing company financial data"
                    }
            else:
                return {
                    "action": FilterAction.DENY,
                    "reason": "Insufficient privileges to access detailed financial information"
                }
        
        # Default case: allow with screening
        return {
            "action": FilterAction.ALLOW_WITH_SCREENING,
            "reason": "General query - will be screened for sensitive content"
        }

    def verify_user_identity_in_documents(self, user_email: str, document_context: str) -> Dict[str, Any]:
        """Verify user identity against employee documents"""
        verification_result = {
            "email_found": False,
            "user_info": {},
            "verification_successful": False
        }
        
        if not user_email or not document_context:
            return verification_result
        
        # Simple email verification
        if user_email.lower() in document_context.lower():
            verification_result["email_found"] = True
            verification_result["verification_successful"] = True
        
        return verification_result

    def filter_response(self, response: str, query_analysis: Dict[str, Any], 
                      rule_result: Dict[str, Any]) -> Tuple[str, bool]:
        """Apply filtering to LLM response based on rules and guardrails"""
        action = rule_result["action"]
        
        if action == FilterAction.ALLOW:
            return response, False
        
        elif action == FilterAction.DENY:
            return "I cannot provide that information due to access restrictions.", True
        
        elif action == FilterAction.ALLOW_WITH_EMAIL_CHECK:
            # This should be handled before calling this method
            return response, False
        
        elif action == FilterAction.ALLOW_WITH_REDACTION:
            # Apply salary redaction
            filtered_response, was_filtered = self._filter_salary_from_person_response(response)
            
            # Apply guardrails if available
            if self.use_guardrails and self.guardrails:
                try:
                    guardrails_analysis = self.guardrails.analyze_response(
                        response, query_analysis["original_query"], query_analysis["user_role"]
                    )
                    if guardrails_analysis.get("requires_redaction", False):
                        filtered_response = self._apply_guardrails_redaction(filtered_response, guardrails_analysis)
                        was_filtered = True
                except Exception:
                    pass
            
            return filtered_response, was_filtered
        
        elif action == FilterAction.ALLOW_WITH_SCREENING:
            # Light screening for sensitive content
            filtered_response, was_filtered = self._filter_salary_from_person_response(response)
            return filtered_response, was_filtered
        
        return response, False

    def filter_context(self, context: str, query_analysis: Dict[str, Any],
                     rule_result: Dict[str, Any]) -> Tuple[str, bool]:
        """Filter sensitive financial information from retrieved document context"""
        action = rule_result["action"]
        
        if action in [FilterAction.ALLOW, FilterAction.ALLOW_WITH_EMAIL_CHECK]:
            return context, False
        elif action == FilterAction.DENY:
            return "", True
        elif action in [FilterAction.ALLOW_WITH_REDACTION, FilterAction.ALLOW_WITH_SCREENING]:
            filtered_context, was_filtered = self._filter_salary_from_person_response(context)
            return filtered_context, was_filtered
        
        return context, False

    def log_sensitive_query(self, query_analysis: Dict[str, Any], 
                          rule_result: Dict[str, Any], 
                          response_was_filtered: bool) -> Dict[str, Any]:
        """Record sensitive query information for auditing"""
        if not self.audit_log_enabled:
            return {}
        
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_email": query_analysis.get("user_email", "unknown"),
            "user_role": query_analysis.get("user_role", "unknown"),
            "query": query_analysis.get("original_query", ""),
            "is_financial": query_analysis.get("is_financial", False),
            "is_salary_related": query_analysis.get("is_salary_related", False),
            "target_person": query_analysis.get("target_person", None),
            "action_taken": rule_result.get("action", "unknown").value if hasattr(rule_result.get("action", "unknown"), 'value') else str(rule_result.get("action", "unknown")),
            "reason": rule_result.get("reason", ""),
            "response_filtered": response_was_filtered
        }
        
        return audit_entry

    def process_query(self, query: str, user_email: str, user_role: str, document_context: Optional[str] = None) -> Dict[str, Any]:
        """Complete pipeline to process a query and determine filtering actions"""
        # Analyze the query
        query_analysis = self.analyze_query(query, user_email, user_role)
        
        # Determine the appropriate action
        rule_result = self.determine_action(query_analysis)
        
        # Log sensitive queries
        audit_entry = self.log_sensitive_query(query_analysis, rule_result, False)
        
        return {
            "query_analysis": query_analysis,
            "rule_result": rule_result,
            "audit_entry": audit_entry,
            "should_filter_context": rule_result["action"] in [FilterAction.DENY, FilterAction.ALLOW_WITH_REDACTION, FilterAction.ALLOW_WITH_SCREENING],
            "should_verify_email": rule_result["action"] == FilterAction.ALLOW_WITH_EMAIL_CHECK
        }

    def verify_email_in_context(self, user_email: str, document_context: str) -> bool:
        """Simple email verification - check if user's email appears in document context"""
        if not user_email or not document_context:
            return False
        
        # Simple case-insensitive search
        if user_email.lower() in document_context.lower():
            return True
        
        # Extract username from email and search for that
        username = user_email.split('@')[0].lower()
        if len(username) > 2 and username in document_context.lower():
            return True
        
        return False
          
    def _apply_guardrails_redaction(self, response: str, guardrails_analysis: Dict[str, Any]) -> str:
        """Apply advanced redaction based on guardrails analysis"""
        redacted_response = response
        
        # Apply redactions based on guardrails recommendations
        if "redaction_patterns" in guardrails_analysis:
            for pattern in guardrails_analysis["redaction_patterns"]:
                redacted_response = re.sub(pattern, "[REDACTED]", redacted_response, flags=re.IGNORECASE)
        
        return redacted_response

    def _filter_salary_from_person_response(self, response: str) -> Tuple[str, bool]:
        """Filter salary information from responses about people"""
        was_filtered = False
        filtered_response = response
        
        # Apply financial pattern filtering
        for pattern in self.compiled_financial_patterns:
            if pattern.search(filtered_response):
                filtered_response = pattern.sub("[SALARY INFORMATION REDACTED]", filtered_response)
                was_filtered = True
        
        return filtered_response, was_filtered 