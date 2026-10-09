"""Source preparation and candidate operations independent of the application."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SourceSnapshot:
    paths: tuple[str, ...]
    sha256: str


class SourceProvider(Protocol):
    def materialize(self, workspace: Path) -> SourceSnapshot: ...


class SolSource(SourceProvider, Protocol):
    def materialize_ground_truth(self, workspace: Path) -> None: ...
