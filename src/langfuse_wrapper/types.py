"""Small typed value objects used across langfuse_wrapper."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    """Token usage for a single model call."""

    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class ModelPrice:
    """USD price per 1000 tokens for a model."""

    input_per_1k: float
    output_per_1k: float


@dataclass(frozen=True)
class CostResult:
    """Result of a client-side cost estimate (all costs in USD)."""

    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
