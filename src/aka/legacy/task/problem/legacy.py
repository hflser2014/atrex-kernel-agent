"""Load existing kernel/native/SOL operators with their original validation rules."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aka.contracts.problem import LoadedProblem
from .layout import (
    AGENT_PROBLEM_FILENAME, find_atrex_bench_root, has_agent_problem, is_sol_op,
    should_use_generalized_problem, validate_agent_problem, validate_private_shapes,
)


@dataclass(frozen=True)
class LegacyProblemProvider:
    optimization_mode: str = "leaderboard"

    def load(self, directory: Path, *, optimization_mode=None) -> LoadedProblem:
        """Preserve the original operator resolver's validation order and errors."""
        optimization_mode = optimization_mode or self.optimization_mode
        d = Path(directory).resolve()
        if not d.is_dir():
            raise SystemExit(f"--op-dir not found: {d}")
        ref = d / "reference.py"
        if not ref.is_file():
            raise SystemExit(f"--op-dir has no reference.py: {d}")
        atrex_bench_root = ""
        provided_problem = has_agent_problem(d)
        shapes_path = d / "shapes.json"
        generalized = should_use_generalized_problem(d, optimization_mode)
        if generalized and provided_problem:
            if not shapes_path.is_file():
                raise SystemExit(
                    "generalized Atrex-Bench operator requires private evaluator shapes.json: "
                    f"{d}"
                )
            try:
                validate_agent_problem(
                    d / AGENT_PROBLEM_FILENAME,
                    private_shapes_path=shapes_path,
                )
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
        if not is_sol_op(d) and shapes_path.is_file():
            try:
                validate_private_shapes(shapes_path)
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
            native_root = find_atrex_bench_root(d)
            if native_root is None:
                raise SystemExit(
                    "native Atrex-Bench operator requires its canonical scripts/run_eval.py and "
                    f"src/atrex_bench runtime in an ancestor directory: {d}"
                )
            atrex_bench_root = str(native_root)
        return LoadedProblem(
            name=d.name, directory=d, reference=ref,
            bench_root=Path(atrex_bench_root) if atrex_bench_root else None,
            public_contract=d / AGENT_PROBLEM_FILENAME if generalized and provided_problem else None,
            public_contract_source="provided" if generalized and provided_problem else ("auto" if generalized else "none"),
        )

    def inputs(self, operator_dir, workspace, optimization_mode, bench_root, generated_digest=""):
        from .inputs import BenchInputs
        return BenchInputs(operator_dir, workspace, optimization_mode, bench_root, generated_digest)

    def sol_files(self, operator_dir):
        from .inputs import sol_problem_files
        return sol_problem_files(operator_dir)
