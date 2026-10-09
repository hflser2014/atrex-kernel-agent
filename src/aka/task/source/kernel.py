"""Original kernel copy operation; no Git, workspace resources or evaluation."""
from dataclasses import dataclass
from pathlib import Path
import subprocess
from .snapshot import snapshot


@dataclass(frozen=True)
class KernelSourceProvider:
    kernel_demo: str

    def materialize(self, workspace: Path):
        subprocess.run(["cp", self.kernel_demo, str(workspace / "kernel.py")], check=True)
        return snapshot(workspace, ("kernel.py",))

