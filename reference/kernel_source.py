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
from aka.bootstrap.workspace import candidate_workspace


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if arguments and arguments[0] == "--initialize":
        _, reference_dir, entry, *inputs = arguments
        with source_provider(kernel_demo=inputs[1] if len(inputs) > 1 else "__missing_kernel_demo__") as source:
            content = source.prepare()
        with candidate_workspace() as workspace:
            return workspace.initialize_kernel(Path(reference_dir), entry, inputs, content=content)
    with source_provider(kernel_demo=arguments[0]) as source:
        content = source.prepare()
    with candidate_workspace() as workspace:
        try:
            workspace.install_files(Path(arguments[1]), content.files)
        except subprocess.CalledProcessError as exc:
            return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
