"""Load the application framework from this checkout or its installed packages."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


def task_modules():
    source = Path(__file__).resolve().parent.parent / "src"
    if (source / "aka" / "task" / "problem").is_dir() and str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from aka.task import problem
    return problem


def resolve_problem(directory: str, optimization_mode: str = "leaderboard") -> dict:
    task_modules()
    from aka.bootstrap.task import resolve_operator_directory
    return resolve_operator_directory(directory, optimization_mode)


def run(argv: Optional[list[str]] = None) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    source = repo_root / "src"
    # A source checkout supports the historical command without an install step.
    # Exported application-only checkouts use the installed adapter distributions.
    if (source / "aka" / "bootstrap" / "host.py").is_file():
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
    from aka.legacy.application.host import run_application
    from aka.contracts.application import ApplicationRequest

    return run_application(ApplicationRequest(repo_root, argv))
