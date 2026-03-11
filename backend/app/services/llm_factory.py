"""
LLM Factory: Creates the correct LLM instance based on configuration.

Supported providers:
- AI_PROVIDER=groq       → Groq (free tier, 100K tokens/day limit)
- AI_PROVIDER=openrouter  → OpenRouter (many models, pay-as-you-go, recommended)
- AI_PROVIDER=anthropic   → Claude (premium, best for documents)

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
        provider: Force a specific provider ("groq", "openrouter", or "anthropic").
                  If None, uses the AI_PROVIDER setting from .env.
    """
    settings = get_settings()

    # Determine which provider to use
    chosen = (provider or settings.ai_provider).lower()

    # Fallback chain: if chosen provider has no key, try alternatives
    if chosen == "anthropic" and not settings.anthropic_api_key:
        logger.warning(
            "Anthropic requested but ANTHROPIC_API_KEY is empty. Falling back."
        )
        chosen = "openrouter" if settings.openrouter_api_key else "groq"

    if chosen == "openrouter" and not settings.openrouter_api_key:
        logger.warning(
            "OpenRouter requested but OPENROUTER_API_KEY is empty. Falling back to Groq."
        )
        chosen = "groq"

    if chosen == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs: dict = {
            "api_key": settings.anthropic_api_key,
            "model": settings.anthropic_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "default_request_timeout": 45,
        }
        if settings.anthropic_base_url:
            kwargs["anthropic_api_url"] = settings.anthropic_base_url
            logger.info(
                "Using Anthropic Claude (%s) via proxy %s for %s",
                settings.anthropic_model, settings.anthropic_base_url, purpose,
            )
        else:
            logger.info("Using Anthropic Claude (%s) for %s", settings.anthropic_model, purpose)
        return ChatAnthropic(**kwargs)

    elif chosen == "openrouter":
        from langchain_openai import ChatOpenAI

        logger.info("Using OpenRouter (%s) for %s", settings.openrouter_model, purpose)
        return ChatOpenAI(
            openai_api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model=settings.openrouter_model,
            temperature=temperature,
            max_tokens=max_tokens,
            request_timeout=45,
        )

    else:
        from langchain_groq import ChatGroq

        logger.info("Using Groq (%s) for %s", settings.groq_model, purpose)
        return ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=temperature,
            max_tokens=max_tokens,
            request_timeout=45,
        )


def is_claude_available() -> bool:
    """Check if Claude API is configured and available."""
    settings = get_settings()
    return bool(settings.anthropic_api_key)
