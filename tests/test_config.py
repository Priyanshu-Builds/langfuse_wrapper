"""Tests for langfuse_wrapper.config.Settings."""

from __future__ import annotations

import pytest

from langfuse_wrapper.config import Settings


def test_defaults_with_no_env() -> None:
    s = Settings()
    assert s.public_key is None
    assert s.secret_key is None
    assert s.base_url is None
    assert s.enabled is True
    assert s.scrub_pii is False
    assert s.has_credentials is False
    assert s.is_active is False


def test_reads_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-123")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-456")
    s = Settings()
    assert s.public_key == "pk-lf-123"
    assert s.secret_key == "sk-lf-456"
    assert s.has_credentials is True
    assert s.is_active is True


def test_host_alias_used_when_base_url_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_HOST", "https://langfuse.internal")
    assert Settings().base_url == "https://langfuse.internal"


def test_base_url_wins_over_host_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_HOST", "https://deprecated.host")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://current.base")
    assert Settings().base_url == "https://current.base"


def test_enabled_false_disables_even_with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    monkeypatch.setenv("LFWRAP_ENABLED", "false")
    s = Settings()
    assert s.enabled is False
    assert s.has_credentials is True
    assert s.is_active is False


def test_only_one_credential_is_not_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    s = Settings()
    assert s.has_credentials is False
    assert s.is_active is False


def test_scrub_pii_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LFWRAP_SCRUB_PII", "true")
    assert Settings().scrub_pii is True
