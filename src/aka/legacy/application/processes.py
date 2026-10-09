"""Translate neutral continuation facts for preserved optimizer process launches."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from aka.bootstrap.continuation import SELECTION_ENV, DIGEST_ENV, digest, read

_launch_environment = ContextVar("aka_legacy_launch_environment", default=None)


@contextmanager
def use_launch_environment(environment):
    token = _launch_environment.set(dict(environment))
    try:
        yield
    finally:
        _launch_environment.reset(token)


def child_environment():
    return dict(_launch_environment.get() or {})


def recovery_environment(directory: Path):
    environment = child_environment()
    payload = read(environment)
    if payload is None:
        return {}
    path = directory / "launch-selection.json"
    if path.exists():
        if path.read_text() != payload:
            raise RuntimeError("refusing to replace recovery launch selection with a different composition")
    else:
        from orchestrator.environment_recovery import durable_write_text
        durable_write_text(path, payload)
        path.chmod(0o600)
    return {SELECTION_ENV: str(path), DIGEST_ENV: digest(payload)}
