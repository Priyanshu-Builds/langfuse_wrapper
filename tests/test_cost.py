"""Tests for langfuse_wrapper.cost (price table + estimation)."""

from __future__ import annotations

import pytest

from langfuse_wrapper import cost
from langfuse_wrapper.types import ModelPrice


def test_exact_model_price_lookup() -> None:
    price = cost.get_model_price("gpt-4o")
    assert price == ModelPrice(0.0025, 0.010)


def test_prefix_match_resolves_versioned_name() -> None:
    # claude-opus-4-8 has no exact entry; resolves to the claude-opus-4 prefix.
    assert cost.get_model_price("claude-opus-4-8") == ModelPrice(0.015, 0.075)


def test_longest_prefix_wins() -> None:
    # both "gpt-4o" and "gpt-4o-mini" are prefixes of this; the longer one must win.
    assert cost.get_model_price("gpt-4o-mini-2024") == ModelPrice(0.00015, 0.0006)


def test_unknown_model_returns_none() -> None:
    assert cost.get_model_price("some-unknown-model") is None


def test_estimate_cost_math() -> None:
    # 1000 input @ 0.0025/1k = 0.0025 ; 500 output @ 0.010/1k = 0.005
    result = cost.estimate_cost("gpt-4o", 1000, 500)
    assert result is not None
    assert result.input_cost == pytest.approx(0.0025)
    assert result.output_cost == pytest.approx(0.005)
    assert result.total_cost == pytest.approx(0.0075)


def test_estimate_cost_unknown_model_is_none() -> None:
    assert cost.estimate_cost("mystery-model", 100, 100) is None


def test_register_model_price_override(monkeypatch: pytest.MonkeyPatch) -> None:
    # isolate the module-level table so the override does not leak into other tests
    monkeypatch.setattr(cost, "_PRICES", dict(cost._PRICES))
    cost.register_model_price("claude-fable-5", 0.01, 0.05)
    assert cost.get_model_price("claude-fable-5") == ModelPrice(0.01, 0.05)
    result = cost.estimate_cost("claude-fable-5", 2000, 1000)
    assert result is not None
    assert result.total_cost == pytest.approx(2000 / 1000 * 0.01 + 1000 / 1000 * 0.05)
