"""Run the selected kernel Source from the task-owned workspace shell."""
from pathlib import Path
import subprocess
import sys

# Direct source-checkout execution also works before installing the distributions.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from aka.task.source.composition import compose_source


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    with compose_source(config={"kernel_demo": arguments[0]}) as owner:
        try:
            owner.source.materialize(Path(arguments[1]))
        except subprocess.CalledProcessError as exc:
            return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
