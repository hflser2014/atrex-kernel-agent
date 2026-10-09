"""Source preparation and candidate operations independent of the application."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Any


@dataclass(frozen=True)
class SourceSnapshot:
    paths: tuple[str, ...]
    sha256: str


class SourceProvider(Protocol):
    def materialize(self, workspace: Path) -> SourceSnapshot: ...


class SolSource(SourceProvider, Protocol):
    def materialize_ground_truth(self, workspace: Path) -> None: ...


@dataclass(frozen=True)
class CandidateHandle:
    episode: int
    base_commit: str
    branch: str
    path: Path


class CandidateWorkspace(Protocol):
    def initialize_kernel(self, reference_dir: Path, entry: str, arguments: list[str]) -> int: ...
    def prepare_sol(self, workspace: Path, source: SolSource, **options: Any) -> None: ...
    def commit_sol(self, workspace: Path) -> None: ...
    def install_runtime(self, workspace: Path, atrex_bench_root: Path | None = None, **options: Any) -> None: ...
    def plan(self, workspace: Path, episode: int, base_commit: str, root: Path | None = None) -> CandidateHandle: ...
    def materialize(self, handle: CandidateHandle, workspace: Path) -> None: ...
    def validate_candidate(self, handle: CandidateHandle, candidate_commit: str) -> tuple[str, list[str]]: ...
    def archive(self, handle: CandidateHandle, destination: Path, candidate_commit: str = "HEAD") -> Path: ...
    def remove(self, handle: CandidateHandle, workspace: Path) -> None: ...
    def promote(self, workspace: Path, *, base_commit: str, candidate_commit: str, episode: int,
                evidence: dict[str, Any], memory_version: int, memory_record: dict[str, Any]) -> str: ...
    def write_revision(self, workspace: Path, revision: str, changed_paths: list[str],
                       destination: Path, label: str) -> dict[str, str | None]: ...

