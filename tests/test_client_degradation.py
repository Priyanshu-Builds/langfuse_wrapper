"""Tests for graceful degradation and client resolution in langfuse_wrapper.client."""

from __future__ import annotations

import pytest

import langfuse_wrapper as lw
from langfuse_wrapper import client as client_mod
from langfuse_wrapper._noop import NoopClient, NoopSpan


def test_no_credentials_yields_noop_client() -> None:
    c = lw.get_client()
    assert isinstance(c, NoopClient)
    assert lw.is_enabled() is False


def test_noop_context_manager_yields_chainable_span() -> None:
    c = lw.get_client()
    with c.start_as_current_observation(name="unit", as_type="span") as span:
        assert isinstance(span, NoopSpan)
        # mutators are chainable, queries/scores never raise
        assert span.update(output="ignored") is span
        assert span.end() is span
        span.score(name="quality", value=1.0)
    # top-level flush is safe when inactive
    lw.flush()


def test_noop_client_methods_do_not_raise() -> None:
    c = lw.get_client()
    assert c.get_prompt("does-not-matter") is None
    assert c.get_current_trace_id() is None
    assert c.get_trace_url() is None
    assert c.auth_check() is False
    c.create_score(name="s", value=1)
    c.score_current_trace(name="s", value=1)
    c.update_current_span(output="x")
    c.flush()
    c.shutdown()


def test_configure_disables_even_with_credentials() -> None:
    s = lw.configure(public_key="pk", secret_key="sk", enabled=False)
    assert s.has_credentials is True
    assert s.is_active is False
    assert isinstance(lw.get_client(), NoopClient)


def test_active_builds_real_client_with_expected_args(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeLangfuse:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(client_mod, "Langfuse", FakeLangfuse)
    lw.configure(public_key="pk", secret_key="sk", base_url="https://self.hosted")

    c = lw.get_client()
    assert isinstance(c, FakeLangfuse)
    assert captured == {
        "public_key": "pk",
        "secret_key": "sk",
        "base_url": "https://self.hosted",
    }
    assert lw.is_enabled() is True


def test_client_is_cached_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: object())
    lw.configure(public_key="pk", secret_key="sk")
    assert lw.get_client() is lw.get_client()


def test_configure_resets_cached_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: object())
    lw.configure(public_key="pk", secret_key="sk")
    first = lw.get_client()
    lw.configure(public_key="pk2", secret_key="sk2")
    assert lw.get_client() is not first


def test_client_init_failure_falls_back_to_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**kwargs: object) -> None:
        raise RuntimeError("cannot reach Langfuse")

    monkeypatch.setattr(client_mod, "Langfuse", boom)
    lw.configure(public_key="pk", secret_key="sk")
    assert isinstance(lw.get_client(), NoopClient)
