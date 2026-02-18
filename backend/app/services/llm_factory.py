"""
LLM Factory: Creates the correct LLM instance based on configuration.

Hybrid mode (default):
- AI_PROVIDER=groq  → all regular queries use Groq (free)
- ANTHROPIC_API_KEY  → Claude available on-demand for document analysis

Use create_llm() for regular queries (uses AI_PROVIDER setting).
Use create_llm(provider="anthropic") to force Claude for document tasks.
"""

import logging

from langchain_core.language_models import BaseChatModel

from app.config import get_settings

logger = logging.getLogger("santonibot.llm")


def create_llm(
    temperature: float = 0.1,
    max_tokens: int = 4096,
    purpose: str = "agent",
    provider: str | None = None,
) -> BaseChatModel:
    """
    Create an LLM instance.

    Args:
        temperature: LLM temperature (0 = deterministic, 1 = creative)
        max_tokens: Maximum tokens in response
        purpose: "classifier" for orchestrator (fast, low tokens) or "agent" for responses
        provider: Force a specific provider ("groq" or "anthropic").
                  If None, uses the AI_PROVIDER setting from .env.
    """
    settings = get_settings()

    # Determine which provider to use
    chosen = (provider or settings.ai_provider).lower()

    # If anthropic is requested but no key, fall back to groq
    if chosen == "anthropic" and not settings.anthropic_api_key:
        logger.warning(
            "Anthropic requested but ANTHROPIC_API_KEY is empty. Falling back to Groq."
        )
        chosen = "groq"

    if chosen == "anthropic":
        from langchain_anthropic import ChatAnthropic

        logger.info("Using Anthropic Claude (%s) for %s", settings.anthropic_model, purpose)
        return ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        from langchain_groq import ChatGroq

        logger.info("Using Groq (%s) for %s", settings.groq_model, purpose)
        return ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )


def is_claude_available() -> bool:
    """Check if Claude API is configured and available."""
    settings = get_settings()
    return bool(settings.anthropic_api_key)
