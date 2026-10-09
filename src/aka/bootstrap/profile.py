"""Launch manifests reference Core profiles and select registered startup seams."""
from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Mapping, Sequence

from aka.core.boot import compose, token_table
from aka.core.composition import ResolvedComposition, substitute
from aka.core.errors import CompositionError
from aka.core.keys import ServiceKey


@dataclass(frozen=True)
class Selection:
    composition: ResolvedComposition
    target: str
    tokens: tuple[ServiceKey, ...]
    required_services: tuple[str, ...]
    resources: tuple[tuple[Path, tuple[str, ...]], ...]


def registered_tokens(extra: Sequence[ServiceKey] = ()) -> dict[str, ServiceKey]:
    available = entry_points()
    entries = (available.select(group="aka.tokens") if hasattr(available, "select")
               else available.get("aka.tokens", ()))
    values = list(extra)
    for entry in entries:
        token = entry.load()
        if not isinstance(token, ServiceKey):
            raise TypeError(f"registered token {entry.name} must be a ServiceKey")
        values.append(token)
    return token_table(values)


def startup_token(name: str) -> ServiceKey:
    # Names choose implementations; protocol metadata remains defined in code.
    return ServiceKey(name, "Startup", module="aka.contracts.startup")


def resolve_profile(profile: Path, *, patch_files: Sequence[Path] = (),
                    patches: Sequence[Mapping[str, Any]] = (),
                    variables: Mapping[str, str] | None = None,
                    tokens: Sequence[ServiceKey] = ()) -> Selection:
    profile = Path(profile).expanduser().resolve()
    try:
        value = json.loads(profile.read_text())
    except (OSError, ValueError) as exc:
        raise CompositionError(str(profile), f"cannot read launch profile: {exc}") from exc
    fields = {"api_version", "composition", "target", "tokens", "required_services", "resources", "doc"}
    if (not isinstance(value, dict) or type(value.get("api_version")) is not int
            or value["api_version"] != 1 or set(value) - fields):
        raise CompositionError(str(profile), "invalid launch profile fields or version")
    composition_name = value.get("composition")
    if (not isinstance(composition_name, str) or not composition_name
            or Path(composition_name).name != composition_name):
        raise CompositionError(str(profile), "composition must name a sibling Core profile")
    target = value.get("target")
    if not isinstance(target, str):
        raise CompositionError(str(profile), "target must name a Startup service")
    startup = startup_token(target)
    registry = registered_tokens(tokens)
    registry = token_table((*registry.values(), startup))
    def names(key):
        items = value.get(key, [])
        if (not isinstance(items, list) or any(not isinstance(x, str) or not x for x in items)
                or len(items) != len(set(items))):
            raise CompositionError(str(profile), f"{key} must contain unique service names")
        return tuple(items)
    selected = names("tokens")
    required = tuple(dict.fromkeys((target, *names("required_services"))))
    unknown = sorted((set(selected) | set(required)) - set(registry))
    if unknown:
        raise CompositionError(str(profile), f"unregistered tokens: {', '.join(unknown)}")
    seams = token_table((startup, *(registry[name] for name in selected), *tokens))
    if set(required) - set(seams):
        raise CompositionError(str(profile), "required services must have selected tokens")
    composition = compose(composition_name, profiles_dir=profile.parent / "compositions",
                          patch_files=patch_files, patches=patches, variables=variables)
    resources = value.get("resources", [])
    if not isinstance(resources, list):
        raise CompositionError(str(profile), "resources must be an array")
    resolved = []
    for resource in resources:
        if (not isinstance(resource, dict) or set(resource) != {"root", "paths"}
                or not isinstance(resource["root"], str)
                or not isinstance(resource["paths"], list)
                or not resource["paths"]
                or any(not isinstance(x, str) or not x for x in resource["paths"])):
            raise CompositionError(str(profile), "resources require root and nonempty paths")
        path = Path(substitute(resource["root"], composition.variables, str(profile))).expanduser()
        if not path.is_absolute():
            path = profile.parent / path
        resolved.append((path.resolve(), tuple(resource["paths"])))
    return Selection(composition, target, tuple(seams.values()), required, tuple(resolved))
