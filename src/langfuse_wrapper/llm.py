"""Record LLM token usage (and optionally client-side cost) onto an observation.

``track_llm`` reads usage from a provider response (Anthropic or OpenAI shapes, object or dict)
or from explicit token counts, and writes it to a generation via ``observation.update``. By
default it sends ``usage_details`` + ``model`` and lets Langfuse compute cost server-side; pass
``record_cost=True`` to also attach a client-side USD estimate (useful for models Langfuse does
not price, or for surfacing a runtime cost). No-op-safe: on a NoopSpan the update does nothing.
"""

from __future__ import annotations

from typing import Any

from .cost import estimate_cost
from .types import Usage


def _get(obj: Any, *names: str) -> Any:
    """Fetch the first present attribute/key from an object or dict."""
    for name in names:
        if isinstance(obj, dict):
            if name in obj:
                return obj[name]
        elif hasattr(obj, name):
            return getattr(obj, name)
    return None


def extract_usage(response: Any) -> Usage | None:
    """Extract token usage from a provider response, or ``None`` if not found.

    Handles Anthropic (``usage.input_tokens`` / ``output_tokens``) and OpenAI
    (``usage.prompt_tokens`` / ``completion_tokens``), as objects or dicts.
    """
    usage = _get(response, "usage")
    if usage is None:
        return None
    input_tokens = _get(usage, "input_tokens", "prompt_tokens")
    output_tokens = _get(usage, "output_tokens", "completion_tokens")
    if input_tokens is None and output_tokens is None:
        return None
    return Usage(int(input_tokens or 0), int(output_tokens or 0))


def track_llm(
    observation: Any,
    response: Any = None,
    *,
    model: str | None = None,
    usage: Usage | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    record_cost: bool = False,
) -> Any:
    """Record usage (and optionally cost) onto ``observation`` and return it.

    Usage is resolved in priority order: explicit ``usage``, then explicit
    ``input_tokens``/``output_tokens``, then extracted from ``response``. If no usage can be
    determined, the observation is returned unchanged.
    """
    resolved = usage
    if resolved is None and (input_tokens is not None or output_tokens is not None):
        resolved = Usage(input_tokens or 0, output_tokens or 0)
    if resolved is None and response is not None:
        resolved = extract_usage(response)
    if resolved is None:
        return observation

    update_kwargs: dict[str, Any] = {
        "usage_details": {
            "input": resolved.input_tokens,
            "output": resolved.output_tokens,
            "total": resolved.total_tokens,
        }
    }
    if model is not None:
        update_kwargs["model"] = model

    if record_cost and model is not None:
        cost = estimate_cost(model, resolved.input_tokens, resolved.output_tokens)
        if cost is not None:
            update_kwargs["cost_details"] = {
                "input": cost.input_cost,
                "output": cost.output_cost,
                "total": cost.total_cost,
            }

    observation.update(**update_kwargs)
    return observation
