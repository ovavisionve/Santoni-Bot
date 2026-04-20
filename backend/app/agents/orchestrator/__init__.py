"""Orchestrator package — classifies intent and routes to agents.

Split from monolithic orchestrator.py (1,036 lines):
  - keywords.py: keyword rules, follow-up patterns, domain constants
  - classifier.py: classification functions (keyword, capability, confidence)
  - routing.py: Orchestrator class (process, stream, document handling)
"""

from .classifier import (
    classify_by_keywords,
    classify_with_capabilities,
    classify_with_confidence,
    compute_confidence_score,
    should_try_sql_direct,
)
from .routing import Orchestrator

__all__ = [
    "Orchestrator",
    "classify_by_keywords",
    "classify_with_capabilities",
    "classify_with_confidence",
    "compute_confidence_score",
    "should_try_sql_direct",
]
