"""Scoring / evaluation helpers over Langfuse's score API.

* :func:`score` — attach a score to the **current** trace (default) or observation, from inside a
  traced scope. The common case: ``score("relevance", 0.9)``.
* :func:`create_score` — attach a score to a specific trace/observation by id, e.g. for a deferred
  or asynchronous evaluation after the run completed.

Both route through the graceful-degradation gate, so scoring is a safe no-op when the wrapper is
inactive. ``data_type`` is inferred as ``BOOLEAN`` for ``bool`` values (which are otherwise
ambiguous with numeric scores); other types are left for Langfuse to infer unless you pass it.
"""

from __future__ import annotations

from typing import Any, Literal

from .client import get_client

ScoreTarget = Literal["trace", "observation"]
ScoreDataType = Literal["NUMERIC", "CATEGORICAL", "BOOLEAN", "TEXT", "CORRECTION"]


def _resolve_data_type(value: Any, data_type: ScoreDataType | None) -> ScoreDataType | None:
    if data_type is not None:
        return data_type
    if isinstance(value, bool):
        return "BOOLEAN"
    return None  # let Langfuse infer NUMERIC / CATEGORICAL


def score(
    name: str,
    value: float | str | bool,
    *,
    target: ScoreTarget = "trace",
    data_type: ScoreDataType | None = None,
    comment: str | None = None,
    metadata: Any | None = None,
    config_id: str | None = None,
) -> None:
    """Score the current trace (default) or current observation. No-op when inactive."""
    kwargs: dict[str, Any] = {"name": name, "value": value}
    resolved = _resolve_data_type(value, data_type)
    if resolved is not None:
        kwargs["data_type"] = resolved
    if comment is not None:
        kwargs["comment"] = comment
    if metadata is not None:
        kwargs["metadata"] = metadata
    if config_id is not None:
        kwargs["config_id"] = config_id

    client = get_client()
    if target == "observation":
        client.score_current_span(**kwargs)
    else:
        client.score_current_trace(**kwargs)


def create_score(
    name: str,
    value: float | str | bool,
    *,
    trace_id: str | None = None,
    observation_id: str | None = None,
    session_id: str | None = None,
    data_type: ScoreDataType | None = None,
    comment: str | None = None,
    metadata: Any | None = None,
    config_id: str | None = None,
    score_id: str | None = None,
) -> None:
    """Score a specific trace/observation by id (e.g. a deferred eval). No-op when inactive."""
    kwargs: dict[str, Any] = {"name": name, "value": value}
    resolved = _resolve_data_type(value, data_type)
    optional = {
        "trace_id": trace_id,
        "observation_id": observation_id,
        "session_id": session_id,
        "data_type": resolved,
        "comment": comment,
        "metadata": metadata,
        "config_id": config_id,
        "score_id": score_id,
    }
    for key, val in optional.items():
        if val is not None:
            kwargs[key] = val

    get_client().create_score(**kwargs)
