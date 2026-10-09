"""Source preparation and candidate operations independent of the application."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Any

from .content import SourceContent, WorkspaceFile


@dataclass(frozen=True)
class SourceSnapshot:
    paths: tuple[str, ...]
    sha256: str


class SourceProvider(Protocol):
    def prepare(self) -> SourceContent:
        """Describe initial source files without writing an agent workspace."""
        ...


@dataclass(frozen=True)
class CandidateHandle:
    episode: int
    base_commit: str
    branch: str
    path: Path


class CandidateWorkspace(Protocol):
    def install_files(self, workspace: Path, files: tuple[WorkspaceFile, ...]) -> SourceSnapshot: ...
    def initialize_kernel(self, reference_dir: Path, entry: str, arguments: list[str],
                          *, content: SourceContent, working_directory: Path | None = None) -> int: ...
    def prepare_sol(self, workspace: Path, content: SourceContent, *,
                    problem_files: tuple[WorkspaceFile, ...], reference_dir: Path) -> None: ...
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

