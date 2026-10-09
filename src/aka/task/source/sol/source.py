"""SOL initial files rendered with the original source semantics."""
from dataclasses import dataclass
from pathlib import Path
import json
from .render import _render_kernel, _solution_json
from ..snapshot import snapshot

GROUND_TRUTH = ("definition.json", "reference.py", "workload.jsonl")


@dataclass(frozen=True)
class SolSourceProvider:
    operator_dir: str
    name: str
    framework: str
    platform: str
    gpu_wiki: str = ""
    definition: dict | None = None

    def materialize_ground_truth(self, workspace):
        op = Path(self.operator_dir)
        for name in GROUND_TRUTH:
            (workspace / name).write_text((op / name).read_text(encoding="utf-8"), encoding="utf-8")

    def materialize(self, workspace):
        op = Path(self.operator_dir)
        definition = self.definition if self.definition is not None else json.loads((op / "definition.json").read_text(encoding="utf-8"))
        (workspace / "kernel.py").write_text(
            _render_kernel(definition, (op / "reference.py").read_text(encoding="utf-8")), encoding="utf-8")
        (workspace / "solution.json").write_text(
            json.dumps(_solution_json(definition, self.name, self.framework, self.platform), indent=2) + "\n",
            encoding="utf-8")
        return snapshot(workspace, ("kernel.py", "solution.json"))

