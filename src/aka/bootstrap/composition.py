"""Bootstrap-owned application variable namespace and profile selection."""
from __future__ import annotations

from pathlib import Path
from dataclasses import replace
from typing import Any, Mapping, Sequence

from aka.core.boot import compose
from aka.core.composition import ResolvedComposition
from aka.core.errors import CompositionError

PROFILES_DIR = Path(__file__).with_name("profiles")
COMPOSITION_VARS = (
    "repo_root", "workspace", "campaign_name", "operator", "platform", "arch",
    "framework", "optimization_mode",
)


def application_variables(repo_root: Path, values: Mapping[str, str] | None = None) -> dict[str, str]:
    """Keep application blanks explicit; Core neither names nor defaults them.

    Parsed campaign values must be supplied by the application caller. This layer
    does not parse argv a second time or invent new optimization defaults.
    """
    values = dict(values or {})
    unknown = sorted(set(values) - set(COMPOSITION_VARS))
    if unknown:
        raise CompositionError("variables", f"unsupported application variables: {', '.join(unknown)}")
    resolved_root = repo_root.resolve()
    if "repo_root" in values:
        supplied_root = values["repo_root"]
        if not isinstance(supplied_root, str) or not supplied_root.strip():
            raise CompositionError("variables", "repo_root must be a nonblank path")
        if Path(supplied_root).resolve() != resolved_root:
            raise CompositionError(
                "variables",
                f"repo_root variable {supplied_root!r} conflicts with explicit repo_root {str(resolved_root)!r}",
            )
    result = {name: str(values.get(name, "")) for name in COMPOSITION_VARS}
    result["repo_root"] = str(resolved_root)
    return result


def compose_application(
    repo_root: Path,
    *,
    profile: str = "application",
    profiles_dir: Path = PROFILES_DIR,
    patch_files: Sequence[Path] = (),
    patches: Sequence[Mapping[str, Any]] = (),
    variables: Mapping[str, str] | None = None,
) -> ResolvedComposition:
    return compose(
        profile, profiles_dir=profiles_dir, patch_files=patch_files, patches=patches,
        variables=application_variables(repo_root, variables),
    )


def is_default_application(composition: ResolvedComposition, repo_root: Path) -> bool:
    """Legacy child/recovery commands can reproduce only the default composition.

    Provenance and documentation do not change runtime selection. All rows and
    application variables must otherwise match, including disabled rows.
    """
    default = compose_application(repo_root)

    def runtime_rows(rows):
        return tuple(replace(row, doc="", source="", config_source="") for row in rows)

    return (runtime_rows(composition.rows) == runtime_rows(default.rows)
            and composition.variables == default.variables)
