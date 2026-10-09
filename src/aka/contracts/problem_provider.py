"""Problem loading describes existing inputs; it does not prepare a workspace."""
from pathlib import Path
from typing import Protocol

from .problem import LoadedProblem


class ProblemProvider(Protocol):
    def load(self, directory: Path) -> LoadedProblem:
        """Validate input layout and return host-owned facts without running a task."""
        ...

