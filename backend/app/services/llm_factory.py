"""
LLM Factory: Creates the correct LLM instance based on configuration.

Supports:
- Groq (default, free tier, Llama 3.3 70B)
- Anthropic Claude (paid, supports documents/vision, higher quality)

When ANTHROPIC_API_KEY is set and AI_PROVIDER=anthropic, uses Claude.
Otherwise falls back to Groq.
"""

import logging

from langchain_core.language_models import BaseChatModel

from app.config import get_settings

logger = logging.getLogger("santonibot.llm")


def create_llm(
    temperature: float = 0.1,
    max_tokens: int = 4096,
    purpose: str = "agent",
) -> BaseChatModel:
    """
    Create an LLM instance based on the configured AI provider.

    Args:
        temperature: LLM temperature (0 = deterministic, 1 = creative)
        max_tokens: Maximum tokens in response
        purpose: "classifier" for orchestrator (fast, low tokens) or "agent" for responses
    """
    settings = get_settings()

    # Determine which provider to use
    provider = settings.ai_provider.lower()

    # If anthropic is selected but no key, fall back to groq
    if provider == "anthropic" and not settings.anthropic_api_key:
        logger.warning(
            "AI_PROVIDER=anthropic but ANTHROPIC_API_KEY is empty. Falling back to Groq."
        )
        provider = "groq"

    if provider == "anthropic":
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

        return ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
