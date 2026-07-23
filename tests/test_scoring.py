"""Tests for langfuse_wrapper.scoring."""

from __future__ import annotations

from typing import Any

import pytest

import langfuse_wrapper as lw
from langfuse_wrapper import client as client_mod
from langfuse_wrapper import scoring


class FakeClient:
    def __init__(self) -> None:
        self.trace_scores: list[dict[str, Any]] = []
        self.span_scores: list[dict[str, Any]] = []
        self.created: list[dict[str, Any]] = []

    def score_current_trace(self, **kwargs: Any) -> None:
        self.trace_scores.append(kwargs)

    def score_current_span(self, **kwargs: Any) -> None:
        self.span_scores.append(kwargs)

    def create_score(self, **kwargs: Any) -> None:
        self.created.append(kwargs)


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    client = FakeClient()
    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: client)
    lw.configure(public_key="pk", secret_key="sk")
    return client


# --- inactive (graceful degradation) ----------------------------------------


def test_score_inactive_is_noop() -> None:
    scoring.score("relevance", 0.9)  # no client configured; must not raise


def test_create_score_inactive_is_noop() -> None:
    scoring.create_score("relevance", 0.9, trace_id="t1")  # must not raise


# --- score() ----------------------------------------------------------------


def test_score_defaults_to_current_trace(fake_client: FakeClient) -> None:
    scoring.score("relevance", 0.9)
    assert fake_client.trace_scores == [{"name": "relevance", "value": 0.9}]
    assert fake_client.span_scores == []


def test_score_observation_target(fake_client: FakeClient) -> None:
    scoring.score("toxicity", 0.1, target="observation")
    assert fake_client.span_scores == [{"name": "toxicity", "value": 0.1}]
    assert fake_client.trace_scores == []


def test_score_bool_infers_boolean_data_type(fake_client: FakeClient) -> None:
    scoring.score("passed", True)
    assert fake_client.trace_scores[0]["data_type"] == "BOOLEAN"


def test_score_numeric_leaves_data_type_to_langfuse(fake_client: FakeClient) -> None:
    scoring.score("score", 0.5)
    assert "data_type" not in fake_client.trace_scores[0]


def test_score_explicit_data_type_and_metadata(fake_client: FakeClient) -> None:
    scoring.score(
        "sentiment", "positive", data_type="CATEGORICAL", comment="looks good", config_id="c1"
    )
    entry = fake_client.trace_scores[0]
    assert entry["data_type"] == "CATEGORICAL"
    assert entry["comment"] == "looks good"
    assert entry["config_id"] == "c1"


# --- create_score() ---------------------------------------------------------


def test_create_score_forwards_ids(fake_client: FakeClient) -> None:
    scoring.create_score("accuracy", 1.0, trace_id="t1", observation_id="o1", session_id="s1")
    entry = fake_client.created[0]
    assert entry["name"] == "accuracy"
    assert entry["value"] == 1.0
    assert entry["trace_id"] == "t1"
    assert entry["observation_id"] == "o1"
    assert entry["session_id"] == "s1"


def test_create_score_omits_unset_optionals(fake_client: FakeClient) -> None:
    scoring.create_score("accuracy", 1.0, trace_id="t1")
    entry = fake_client.created[0]
    assert set(entry) == {"name", "value", "trace_id"}
