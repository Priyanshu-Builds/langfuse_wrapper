"""Tests for langfuse_wrapper.llm (usage extraction + track_llm)."""

from __future__ import annotations

from typing import Any

import pytest

from langfuse_wrapper import llm
from langfuse_wrapper.types import Usage


class _Usage:
    def __init__(self, **kwargs: int) -> None:
        self.__dict__.update(kwargs)


class _Response:
    def __init__(self, usage: Any) -> None:
        self.usage = usage


class FakeObservation:
    """Records the kwargs passed to update()."""

    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []

    def update(self, **kwargs: Any) -> FakeObservation:
        self.updates.append(kwargs)
        return self


# --- extract_usage ----------------------------------------------------------


def test_extract_usage_anthropic_object() -> None:
    resp = _Response(_Usage(input_tokens=120, output_tokens=45))
    assert llm.extract_usage(resp) == Usage(120, 45)


def test_extract_usage_openai_object() -> None:
    resp = _Response(_Usage(prompt_tokens=200, completion_tokens=80))
    assert llm.extract_usage(resp) == Usage(200, 80)


def test_extract_usage_dict_form() -> None:
    resp = {"usage": {"input_tokens": 10, "output_tokens": 5}}
    assert llm.extract_usage(resp) == Usage(10, 5)


def test_extract_usage_missing_returns_none() -> None:
    assert llm.extract_usage({"no_usage": True}) is None
    assert llm.extract_usage(_Response(None)) is None


# --- track_llm --------------------------------------------------------------


def test_track_llm_from_response_sends_usage_and_model() -> None:
    obs = FakeObservation()
    resp = _Response(_Usage(input_tokens=100, output_tokens=50))
    llm.track_llm(obs, resp, model="claude-opus-4-8")
    assert obs.updates == [
        {
            "usage_details": {"input": 100, "output": 50, "total": 150},
            "model": "claude-opus-4-8",
        }
    ]


def test_track_llm_no_cost_by_default() -> None:
    obs = FakeObservation()
    llm.track_llm(obs, model="gpt-4o", input_tokens=1000, output_tokens=500)
    assert "cost_details" not in obs.updates[0]


def test_track_llm_record_cost_adds_cost_details() -> None:
    obs = FakeObservation()
    llm.track_llm(obs, model="gpt-4o", input_tokens=1000, output_tokens=500, record_cost=True)
    cost_details = obs.updates[0]["cost_details"]
    assert cost_details["input"] == pytest.approx(0.0025)
    assert cost_details["output"] == pytest.approx(0.005)
    assert cost_details["total"] == pytest.approx(0.0075)


def test_track_llm_record_cost_unknown_model_omits_cost() -> None:
    obs = FakeObservation()
    llm.track_llm(obs, model="mystery", input_tokens=100, output_tokens=100, record_cost=True)
    assert "cost_details" not in obs.updates[0]
    assert obs.updates[0]["model"] == "mystery"


def test_track_llm_explicit_usage_takes_priority() -> None:
    obs = FakeObservation()
    resp = _Response(_Usage(input_tokens=999, output_tokens=999))
    llm.track_llm(obs, resp, usage=Usage(1, 2))
    assert obs.updates[0]["usage_details"] == {"input": 1, "output": 2, "total": 3}


def test_track_llm_no_usage_leaves_observation_untouched() -> None:
    obs = FakeObservation()
    llm.track_llm(obs, model="gpt-4o")  # no response, no tokens
    assert obs.updates == []
