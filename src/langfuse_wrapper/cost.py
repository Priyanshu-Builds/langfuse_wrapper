"""Client-side LLM cost estimation.

Langfuse computes cost server-side from token usage and its own price table; this module is a
**client-side convenience** for runtime budgeting/guardrails and for supplying an explicit cost
when a model is unknown to your Langfuse instance. It is not the source of truth.

Prices are USD per 1000 tokens and are **indicative defaults** — verify against current provider
pricing and override with :func:`register_model_price` as needed. Lookup matches the exact model
name first, then falls back to the longest registered key that is a prefix of the requested model
(so versioned names like ``claude-opus-4-8`` resolve to ``claude-opus-4``).
"""

from __future__ import annotations

from .types import CostResult, ModelPrice

# USD per 1000 tokens: (input, output). Indicative defaults; override via register_model_price().
_PRICES: dict[str, ModelPrice] = {
    # Anthropic Claude
    "claude-opus-4": ModelPrice(0.015, 0.075),
    "claude-sonnet-4": ModelPrice(0.003, 0.015),
    "claude-haiku-4": ModelPrice(0.0008, 0.004),
    "claude-3-5-sonnet": ModelPrice(0.003, 0.015),
    "claude-3-5-haiku": ModelPrice(0.0008, 0.004),
    "claude-3-opus": ModelPrice(0.015, 0.075),
    "claude-3-sonnet": ModelPrice(0.003, 0.015),
    "claude-3-haiku": ModelPrice(0.00025, 0.00125),
    # OpenAI
    "gpt-4o-mini": ModelPrice(0.00015, 0.0006),
    "gpt-4o": ModelPrice(0.0025, 0.010),
    "gpt-4-turbo": ModelPrice(0.010, 0.030),
    "gpt-4": ModelPrice(0.030, 0.060),
    "gpt-3.5-turbo": ModelPrice(0.0005, 0.0015),
    "o1-mini": ModelPrice(0.0011, 0.0044),
    "o1": ModelPrice(0.015, 0.060),
    "o3-mini": ModelPrice(0.0011, 0.0044),
}


def register_model_price(model: str, input_per_1k: float, output_per_1k: float) -> None:
    """Add or override the price (USD per 1000 tokens) for a model name or prefix."""
    _PRICES[model] = ModelPrice(input_per_1k, output_per_1k)


def get_model_price(model: str) -> ModelPrice | None:
    """Return the price for ``model``: exact match, else longest matching registered prefix."""
    exact = _PRICES.get(model)
    if exact is not None:
        return exact
    candidates = [key for key in _PRICES if model.startswith(key)]
    if not candidates:
        return None
    return _PRICES[max(candidates, key=len)]


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> CostResult | None:
    """Estimate USD cost for a call, or ``None`` if the model's price is unknown."""
    price = get_model_price(model)
    if price is None:
        return None
    input_cost = input_tokens / 1000 * price.input_per_1k
    output_cost = output_tokens / 1000 * price.output_per_1k
    return CostResult(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=input_cost + output_cost,
    )
