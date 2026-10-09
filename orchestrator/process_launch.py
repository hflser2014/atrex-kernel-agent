"""Select the optimizer's Python launch script independently of module identity."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator

_entrypoint: ContextVar[Path | None] = ContextVar("optimizer_entrypoint", default=None)
_DEFAULT_ENTRYPOINT = Path(__file__).resolve().with_name("optimize.py")


def optimizer_entrypoint() -> Path:
    """Return the script shared by framework children and environment recovery."""
    selected = _entrypoint.get()
    return _DEFAULT_ENTRYPOINT if selected is None else selected


@contextmanager
def use_optimizer_entrypoint(script: Path) -> Iterator[Path]:
    """Use a readable Python script for this invocation; restore it on every exit.

    The caller invokes optimize.main inside this scope. New processes execute
    the selected script with the existing interpreter and argv; that script is
    responsible for rebuilding its configuration and adapters.
    """
    selected = Path(script).expanduser().resolve()
    if not selected.is_file():
        raise ValueError(f"optimizer entrypoint is not a file: {selected}")
    with selected.open("rb") as stream:
        stream.read(1)
    token = _entrypoint.set(selected)
    try:
        yield selected
    finally:
        _entrypoint.reset(token)
