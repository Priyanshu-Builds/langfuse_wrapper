"""Tests for the LangChain / LangGraph integration (get_handler)."""

from __future__ import annotations

from typing import Any

import pytest

import langfuse_wrapper as lw
from langfuse_wrapper import client as client_mod


def test_get_handler_returns_none_when_inactive() -> None:
    assert lw.get_handler() is None


def test_get_handler_active_returns_configured_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeHandler:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    import langfuse.langchain as lc_module

    monkeypatch.setattr(lc_module, "CallbackHandler", FakeHandler)
    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: object())
    lw.configure(public_key="pk-project-a", secret_key="sk")

    handler = lw.get_handler()
    assert isinstance(handler, FakeHandler)
    assert captured["public_key"] == "pk-project-a"


def test_get_handler_forwards_explicit_public_key(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeHandler:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    import langfuse.langchain as lc_module

    monkeypatch.setattr(lc_module, "CallbackHandler", FakeHandler)
    monkeypatch.setattr(client_mod, "Langfuse", lambda **kwargs: object())
    lw.configure(public_key="pk-default", secret_key="sk")

    lw.get_handler(public_key="pk-override")
    assert captured["public_key"] == "pk-override"
