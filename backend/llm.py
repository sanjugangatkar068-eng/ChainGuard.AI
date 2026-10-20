"""Provider-agnostic LLM helper.

Reads configuration from the environment so the app never hardcodes a key:

    LLM_PROVIDER   one of: none (default), openai, anthropic
    LLM_API_KEY    the provider API key
    LLM_MODEL      optional model override
    LLM_BASE_URL   optional base URL (for OpenAI-compatible endpoints)

When the provider is unset or no key is present, `is_configured()` is False and
callers fall back to deterministic, rules-based behaviour.
"""

import os

import httpx

DEFAULT_TIMEOUT = 25.0


class LLMUnavailable(RuntimeError):
    """Raised when the LLM is not configured or the call fails."""


def _cfg() -> dict:
    return {
        "provider": (os.getenv("LLM_PROVIDER", "none") or "none").strip().lower(),
        "api_key": (os.getenv("LLM_API_KEY", "") or "").strip(),
        "model": (os.getenv("LLM_MODEL", "") or "").strip(),
        "base_url": (os.getenv("LLM_BASE_URL", "") or "").strip(),
    }


def is_configured() -> bool:
    cfg = _cfg()
    return cfg["provider"] in ("openai", "anthropic") and bool(cfg["api_key"])


def complete(system: str, user: str, *, max_tokens: int = 400,
             timeout: float = DEFAULT_TIMEOUT) -> str:
    """Return the model's text response, or raise LLMUnavailable."""
    cfg = _cfg()
    if not is_configured():
        raise LLMUnavailable("LLM is not configured")

    try:
        if cfg["provider"] == "openai":
            base = cfg["base_url"] or "https://api.openai.com/v1"
            model = cfg["model"] or "gpt-4o-mini"
            response = httpx.post(
                f"{base}/chat/completions",
                timeout=timeout,
                headers={"Authorization": f"Bearer {cfg['api_key']}"},
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()

        if cfg["provider"] == "anthropic":
            base = cfg["base_url"] or "https://api.anthropic.com"
            model = cfg["model"] or "claude-3-5-sonnet-latest"
            response = httpx.post(
                f"{base}/v1/messages",
                timeout=timeout,
                headers={
                    "x-api-key": cfg["api_key"],
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"].strip()
    except httpx.HTTPError as exc:
        raise LLMUnavailable(f"LLM request failed: {exc}") from exc
    except (KeyError, IndexError, ValueError) as exc:
        raise LLMUnavailable(f"Unexpected LLM response: {exc}") from exc

    raise LLMUnavailable(f"Unknown provider: {cfg['provider']}")
