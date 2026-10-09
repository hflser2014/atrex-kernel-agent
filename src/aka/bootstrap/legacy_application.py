"""Bind the legacy checkout entry without importing or running it during boot."""
from __future__ import annotations

import importlib
import importlib.util
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from aka.application.legacy import LegacyApplication

_default_composition = ContextVar("aka_legacy_default_composition", default=False)
LEGACY_COMPOSITION_ERROR = (
    "legacy application requires the default application composition; "
    "custom application providers must own their child and recovery behavior"
)


@contextmanager
def legacy_composition(compatible: bool):
    token = _default_composition.set(compatible)
    try:
        yield
    finally:
        _default_composition.reset(token)


class LegacyEntrypoint:
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = Path(repo_root).resolve()

    def __call__(self, argv: list[str] | None) -> int:
        # Also reject custom providers that wrap this adapter. Context is scoped
        # to an invocation and never inherited as process-global configuration.
        if not _default_composition.get():
            raise RuntimeError(LEGACY_COMPOSITION_ERROR)
        expected = self._repo_root / "orchestrator" / "optimize.py"
        # Direct script execution aliases __main__ under this name and has no
        # module spec. Reuse that live object instead of importing a second copy.
        module = sys.modules.get("orchestrator.optimize")
        if module is None:
            try:
                spec = importlib.util.find_spec("orchestrator.optimize")
            except ModuleNotFoundError as exc:
                raise RuntimeError("make the matching AKA checkout importable before invocation") from exc
            if spec is None or spec.origin is None or Path(spec.origin).resolve() != expected:
                raise RuntimeError(f"application import does not match the requested checkout: {expected}")
            module = importlib.import_module("orchestrator.optimize")
        if Path(module.__file__).resolve() != expected:
            raise RuntimeError("a different AKA checkout is already loaded")
        entry = getattr(module, "_run_application", None)
        if not callable(entry):
            raise RuntimeError("checkout lacks the non-dispatching application entry; use a matching revision")
        # Never call public main: it will become the Core dispatcher. The internal
        # entry retains the full recovery wrapper, not just _run_main's campaign loop.
        return entry(argv)


def create_legacy_application(repo_root: Path) -> LegacyApplication:
    """Construct with a concrete lazy entry; leave composition ownership here."""
    return LegacyApplication(repo_root=repo_root, entry=LegacyEntrypoint(repo_root))
