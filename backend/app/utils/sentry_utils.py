"""
Sentry utility helpers for SantoniBot.

All functions are safe to call even when Sentry is not configured.
They check for SENTRY_DSN at runtime and become no-ops when disabled.
"""

import logging
from contextlib import contextmanager
from typing import Any

from app.config import get_settings

logger = logging.getLogger("santonibot.sentry")


def _sentry_enabled() -> bool:
    """Check if Sentry is configured (DSN is set)."""
    return bool(get_settings().sentry_dsn)


def capture_agent_error(
    agent_name: str,
    error: Exception,
    context: dict[str, Any] | None = None,
) -> None:
    """Capture an exception in Sentry with agent-specific context.

    Args:
        agent_name: Name of the agent that encountered the error.
        error: The exception to report.
        context: Additional key-value pairs to attach to the Sentry event.
    """
    if not _sentry_enabled():
        return

    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("agent", agent_name)
            scope.set_tag("error_type", type(error).__name__)
            scope.set_context("agent_context", {
                "agent_name": agent_name,
                **(context or {}),
            })
            sentry_sdk.capture_exception(error)
    except Exception as exc:
        logger.debug("Failed to capture error in Sentry: %s", exc)


def set_agent_context(agent_name: str, query_type: str = "") -> None:
    """Set Sentry tags for the current agent operation.

    Args:
        agent_name: Name of the agent handling the request.
        query_type: Type of query being processed (e.g., 'ventas_resumen').
    """
    if not _sentry_enabled():
        return

    try:
        import sentry_sdk

        sentry_sdk.set_tag("agent", agent_name)
        if query_type:
            sentry_sdk.set_tag("query_type", query_type)
    except Exception as exc:
        logger.debug("Failed to set Sentry agent context: %s", exc)


@contextmanager
def track_query_performance(agent_name: str, description: str = ""):
    """Context manager that creates a Sentry span for measuring query performance.

    Usage::

        with track_query_performance("ventas", "fetch top clients"):
            data = build_top_clients(...)

    When Sentry is not configured, this is a transparent no-op.

    Args:
        agent_name: Name of the agent executing the query.
        description: Human-readable description of the operation.
    """
    if not _sentry_enabled():
        yield
        return

    try:
        import sentry_sdk

        with sentry_sdk.start_span(
            op="db.query",
            name=description or f"{agent_name}.fetch_data",
        ) as span:
            span.set_data("agent", agent_name)
            if description:
                span.set_data("description", description)
            yield span
    except Exception:
        # If Sentry span creation fails, just execute the block normally
        yield


def add_breadcrumb(
    category: str,
    message: str,
    level: str = "info",
    data: dict[str, Any] | None = None,
) -> None:
    """Add a Sentry breadcrumb for debugging context.

    Args:
        category: Breadcrumb category (e.g., 'agent', 'query', 'orchestrator').
        message: Description of the event.
        level: Severity level ('debug', 'info', 'warning', 'error').
        data: Additional data to attach.
    """
    if not _sentry_enabled():
        return

    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            category=category,
            message=message,
            level=level,
            data=data or {},
        )
    except Exception:
        pass
