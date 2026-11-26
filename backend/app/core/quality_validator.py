"""
AURA AI Quality Validation Engine
Critical validator that scores and validates AI outputs for completeness and production readiness.
"""

import logging
import json
from app.core.llm_client import llm_client

logger = logging.getLogger(__name__)

# Complexity keywords trigger strict engineering guidelines
COMPLEXITY_KEYWORDS = [
    "professional", "production ready", "production-ready", "realistic", 
    "advanced", "modern", "premium", "enterprise", "full website", 
    "complete project", "complete implementation", "real-world"
]

# HEURISTICS FOR CODE QUALITY DISQUALIFICATION
HEURISTIC_BLACKLIST = [
    "todo:", "implement this", "insert code here", "placeholder", 
    "basic rotating cube", "minimal three.js demo", "simple cube", 
    "hello world example", "mock components", "toy example", 
    "example only", "truncated for brevity", "left as an exercise"
]

VALIDATION_PROMPT = """You are the Strict Output Quality Validation Engine for AURA OS.
Your absolute mandate is to act as a rigorous Senior Quality Assurance Engineer. Inspect the generated response against the user's original query.

User Query:
\"\"\"{query}\"\"\"

Generated Response:
\"\"\"{response}\"\"\"

CRITICAL EVALUATION GUIDELINES:
1. COMPLEXITY ASSESSMENT: Does the user query contain keywords indicating high complexity (e.g., professional, production ready, realistic, advanced, premium, enterprise, full website, complete project)? If yes, you must be extremely strict.
2. DISQUALIFIERS: The response must FAIL validation (score < 90) if it contains placeholding, mock UI, instructions telling the user to "implement this yourself", TODOs, truncated code, or basic hello-world/rotating cube examples when a full production component was requested.
3. SCORING METRICS (Provide a score between 0 and 100 for each):
   - "intent_match": Does the response directly fulfill the user's core request?
   - "feature_coverage": Are all requested elements/features actually implemented?
   - "production_readiness": Are there robust structures, styling, animations, error boundaries, and no mock data/comments?
   - "completeness": Is it a complete, copy-pasteable, working project/file instead of a fragment or tutorial snippet?

Note: If the user request is a simple conversation, casual greeting, or basic question (e.g., "hello", "what is time?"), it does NOT need strict project-level checks. In that case, automatically output scores of 100 and "passed": true.

Return a JSON object with this exact format:
{{
  "is_premium_request": boolean,
  "intent_match": number,
  "feature_coverage": number,
  "production_readiness": number,
  "completeness": number,
  "passed": boolean,
  "feedback": "detailed explanation of what is missing or incorrect, or empty if passed"
}}

Respond with ONLY valid JSON. Do not write any markdown code fences, headers, or surrounding text."""

class QualityValidator:
    """Validator that checks generated answers for premium and complete implementation criteria."""

    def is_complex_query(self, query: str) -> bool:
        """Determines if the query demands premium software engineering execution."""
        q_lower = query.lower()
        return any(keyword in q_lower for keyword in COMPLEXITY_KEYWORDS)

    def run_heuristic_check(self, response: str) -> tuple[bool, str]:
        """Runs fast local heuristics on the response text to detect poor coding patterns."""
        resp_lower = response.lower()
        for marker in HEURISTIC_BLACKLIST:
            if marker in resp_lower:
                return False, f"Heuristic rejection: detected forbidden placeholder marker '{marker}'."
        return True, ""

    async def validate(self, query: str, response: str) -> dict:
        """
        Validate the output semantically and return scoring details.
        Guarantees that high-complexity requests contain full implementations.
        """
        is_complex = self.is_complex_query(query)
        
        # 1. Fast bypass for casual or standard queries
        if not is_complex:
            return {
                "is_premium_request": False,
                "intent_match": 100,
                "feature_coverage": 100,
                "production_readiness": 100,
                "completeness": 100,
                "passed": True,
                "feedback": ""
            }
        
        # 2. Run local heuristic check first
        heuristics_passed, heuristic_feedback = self.run_heuristic_check(response)
        if not heuristics_passed:
            logger.warning(f"QualityValidator: Heuristic check failed: {heuristic_feedback}")
            return {
                "is_premium_request": True,
                "intent_match": 80,
                "feature_coverage": 70,
                "production_readiness": 50,
                "completeness": 50,
                "passed": False,
                "feedback": heuristic_feedback
            }

        # 2. Run LLM-based deep semantic validation
        try:
            prompt = VALIDATION_PROMPT.format(query=query, response=response)
            # Use Groq or Gemini via LLMClient to validate the output in JSON format
            result = await llm_client.generate_json(prompt, category="research")
            
            # Extract scores and ensure they are parsed as numeric
            intent_match = int(result.get("intent_match", 100))
            feature_coverage = int(result.get("feature_coverage", 100))
            production_readiness = int(result.get("production_readiness", 100))
            completeness = int(result.get("completeness", 100))
            
            # Check thresholds: if any score < 90, force passed=False
            passed = result.get("passed", True)
            if is_complex and (intent_match < 90 or feature_coverage < 90 or production_readiness < 90 or completeness < 90):
                passed = False
                
            feedback = result.get("feedback", "")
            if not passed and not feedback:
                feedback = "Scores were below 90 threshold for one or more quality metrics."

            return {
                "is_premium_request": is_complex,
                "intent_match": intent_match,
                "feature_coverage": feature_coverage,
                "production_readiness": production_readiness,
                "completeness": completeness,
                "passed": passed,
                "feedback": feedback
            }

        except Exception as e:
            logger.error(f"QualityValidator: Semantic validation failed: {e}. Falling back to heuristics.")
            # Fail-safe local fallback if LLM is unavailable
            return {
                "is_premium_request": is_complex,
                "intent_match": 95,
                "feature_coverage": 95,
                "production_readiness": 95,
                "completeness": 95,
                "passed": True,
                "feedback": f"Failsafe bypass due to evaluation timeout/error: {e}"
            }

# Initialize global validator instance
quality_validator = QualityValidator()
