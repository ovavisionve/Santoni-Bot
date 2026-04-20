"""base_agent package (split from base_agent.py, Abr 2026).

Public re-exports preserve the old `from app.agents.base_agent import BaseAgent`
and `from app.agents.base_agent import _build_datetime_context` call sites.
"""

from .base import BaseAgent
from .datetime_ctx import _build_datetime_context

__all__ = ["BaseAgent", "_build_datetime_context"]
