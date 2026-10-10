"""Problem loading describes existing inputs; it does not prepare a workspace."""
from pathlib import Path
from typing import Protocol

from .problem import LoadedProblem


class ProblemProvider(Protocol):
    def load(self, directory: Path, *, optimization_mode: str | None = None) -> LoadedProblem:
        """Validate input layout and return host-owned facts without running a task."""
        ...


    def inputs(self, operator_dir: Path, workspace: Path, optimization_mode: str,
               bench_root: str, generated_digest: str = ""):
        """Provide public input contributions and private evaluator checks."""
        ...

    def sol_files(self, operator_dir: Path):
        """Describe the operator ground truth for workspace installation."""
        ...
