"""Shared pytest fixtures.

Every test runs with a clean environment and a reset wrapper singleton, so state never leaks
between tests and a developer's real ``LANGFUSE_*`` env / ``.env`` file cannot influence results.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from langfuse_wrapper import client

_WRAPPER_ENV_VARS = [
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_BASE_URL",
    "LANGFUSE_HOST",
    "LFWRAP_ENABLED",
    "LFWRAP_SCRUB_PII",
]


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[None]:
    for var in _WRAPPER_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    # Run from a clean cwd so a real `.env` in the repo root is never picked up.
    monkeypatch.chdir(tmp_path)
    client.reset()
    yield
    client.reset()
