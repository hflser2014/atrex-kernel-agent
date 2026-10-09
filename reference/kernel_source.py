"""Compatibility entry for the legacy workspace initializer."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
from orchestrator._bootstrap import task_modules

task_modules()
from aka.bootstrap.source import source_provider


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    with source_provider(kernel_demo=arguments[0]) as source:
        try:
            source.materialize(Path(arguments[1]))
        except subprocess.CalledProcessError as exc:
            return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
