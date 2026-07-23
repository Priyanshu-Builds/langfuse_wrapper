"""Tests for langfuse_wrapper.scrubbing and its wiring into the client."""

from __future__ import annotations

from typing import Any

import pytest

import langfuse_wrapper as lw
from langfuse_wrapper import client as client_mod
from langfuse_wrapper import scrubbing

# --- individual redaction rules ---------------------------------------------


def test_scrub_email() -> None:
    assert scrubbing.scrub_text("ping me at a.b+x@example.co.uk please") == (
        "ping me at [REDACTED_EMAIL] please"
    )


def test_scrub_credit_card() -> None:
    assert scrubbing.scrub_text("card 4111 1111 1111 1111 ok") == "card [REDACTED_CC] ok"


def test_scrub_ssn() -> None:
    assert scrubbing.scrub_text("ssn 123-45-6789") == "ssn [REDACTED_SSN]"


def test_scrub_ipv4() -> None:
    assert scrubbing.scrub_text("from 192.168.1.100 now") == "from [REDACTED_IP] now"


def test_scrub_phone() -> None:
    assert scrubbing.scrub_text("call (415) 555-2671") == "call [REDACTED_PHONE]"


# --- recursion --------------------------------------------------------------


def test_scrub_recurses_nested_structures() -> None:
    data = {
        "user": {"email": "x@y.com", "age": 30},
        "notes": ["reach 555-123-4567", "fine"],
        "count": 5,
        "flag": None,
    }
    result = scrubbing.scrub(data)
    assert result == {
        "user": {"email": "[REDACTED_EMAIL]", "age": 30},
        "notes": ["reach [REDACTED_PHONE]", "fine"],
        "count": 5,
        "flag": None,
    }


def test_scrub_leaves_non_strings_untouched() -> None:
    assert scrubbing.scrub(42) == 42
    assert scrubbing.scrub(None) is None
    assert scrubbing.scrub(3.14) == 3.14


def test_scrub_tuple_preserves_type() -> None:
    out = scrubbing.scrub(("a@b.com", 1))
    assert out == ("[REDACTED_EMAIL]", 1)
    assert isinstance(out, tuple)


# --- register_pattern -------------------------------------------------------


def test_register_pattern_custom(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scrubbing, "_PATTERNS", dict(scrubbing._PATTERNS))
    scrubbing.register_pattern("employee_id", r"EMP\d{5}", "[REDACTED_EMP]")
    assert scrubbing.scrub_text("id EMP01234 here") == "id [REDACTED_EMP] here"


# --- make_mask --------------------------------------------------------------


def test_make_mask_scrubs_data_kwarg() -> None:
    mask = scrubbing.make_mask()
    assert mask(data="mail a@b.com") == "mail [REDACTED_EMAIL]"
    assert mask(data={"e": "a@b.com"}) == {"e": "[REDACTED_EMAIL]"}


# --- wiring into the client -------------------------------------------------


def test_client_receives_mask_when_scrub_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        client_mod, "Langfuse", lambda **kwargs: captured.update(kwargs) or object()
    )
    lw.configure(public_key="pk", secret_key="sk", scrub_pii=True)
    lw.get_client()
    assert "mask" in captured
    assert captured["mask"](data="a@b.com") == "[REDACTED_EMAIL]"


def test_client_has_no_mask_when_scrub_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        client_mod, "Langfuse", lambda **kwargs: captured.update(kwargs) or object()
    )
    lw.configure(public_key="pk", secret_key="sk")
    lw.get_client()
    assert "mask" not in captured
