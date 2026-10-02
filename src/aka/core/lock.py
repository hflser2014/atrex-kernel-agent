"""Versioned, declaration-driven composition identity locks."""
from __future__ import annotations
import hashlib, importlib.metadata, importlib.util, json, os, tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping
from .composition import ResolvedComposition, apply_interpolation
from .declaration import PluginDeclaration
from .errors import CompositionError
from .keys import ServiceKey

LOCK_VERSION, LOCK_NAME, STATE_DIR = 2, "composition.json", ".atrex_plugins"

def package_dir(module: str) -> Path | None:
    try: spec = importlib.util.find_spec(module)
    except (ImportError, ValueError): return None
    if spec is None: return None
    locations = tuple(spec.submodule_search_locations or ())
    return Path(locations[0]) if locations else Path(spec.origin).parent if spec.origin else None

def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def _files(package: str, names: Iterable[str]) -> dict[str, str]:
    root = package_dir(package)
    if root is None: raise CompositionError(package, "identity package is unavailable")
    out = {}
    for name in names:
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise CompositionError(package, f"identity file is missing: {name}")
        out[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out

def snapshot(
    composition: ResolvedComposition,
    declarations: Mapping[str, PluginDeclaration | None],
    tokens: Iterable[ServiceKey] = (),
    *,
    effective_configs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    entries = []
    for row in composition.rows:
        declaration = declarations.get(row.id)
        if declaration is None:
            entries.append({
                "id": row.id, "module": row.name, "enabled": not row.disabled,
                "required": row.required, "group": row.group, "isolate": list(row.isolate),
                "inject": list(row.inject), "config_digest": _digest(row.config),
                "schema_digest": "unavailable", "resume_policy": "strict",
                "identity_files": {},
            })
            continue
        package = declaration.module.rsplit(".", 1)[0] if declaration.module.endswith(".plugin") else declaration.module
        if declaration.identity_files:
            identity_root, names = package, declaration.identity_files
        else:
            spec = importlib.util.find_spec(declaration.module)
            if spec is None or spec.origin is None:
                raise CompositionError(row.id, "plugin implementation is unavailable")
            locations = tuple(spec.submodule_search_locations or ())
            identity_root = declaration.module if locations else declaration.module.rsplit(".", 1)[0]
            root = package_dir(identity_root)
            names = tuple(
                path.relative_to(root).as_posix()
                for path in sorted(root.rglob("*"))
                if path.is_file() and "__pycache__" not in path.parts
                and path.name != ".DS_Store" and path.suffix not in {".pyc", ".pyo"}
            )
        identities = {identity_root: _files(identity_root, names)}
        for dependency in declaration.identity_packages:
            root = package_dir(dependency)
            if root is None: raise CompositionError(row.id, f"identity package is unavailable: {dependency}")
            names = (p.relative_to(root).as_posix() for p in sorted(root.rglob("*"))
                     if p.is_file() and "__pycache__" not in p.parts
                     and not any(part.endswith((".dist-info", ".egg-info")) for part in p.parts)
                     and p.name != ".DS_Store" and p.suffix not in {".pyc", ".pyo"})
            identities[dependency] = _files(dependency, names)
        effective_config = (
            dict(effective_configs[row.id])
            if effective_configs is not None and row.id in effective_configs
            else {
                **declaration.defaults,
                **dict(
                    apply_interpolation(
                        row.config,
                        allowlist=declaration.interpolate,
                        variables=composition.variables,
                        source=f"entry:{row.id}",
                    )
                ),
            }
        )
        entries.append({
            "id": row.id, "module": row.name, "enabled": not row.disabled,
            "required": row.required, "group": row.group, "isolate": list(row.isolate),
            "inject": list(row.inject),
            "config_digest": _digest(effective_config),
            "schema_digest": _digest(declaration.config_schema),
            "resume_policy": declaration.resume_policy, "identity_files": identities,
            "observational_fields": list(declaration.observational_fields),
        })
    framework = {}
    for package in ("aka.core",):
        root = package_dir(package)
        names = tuple(p.relative_to(root).as_posix() for p in sorted(root.rglob("*.py"))) if root else ()
        framework[package] = _files(package, names) if root else {}
    aka_root = package_dir("aka")
    framework["aka"] = _files("aka", ("__init__.py",)) if aka_root else {}
    try: version = importlib.metadata.version("atrex-aka-core")
    except importlib.metadata.PackageNotFoundError: version = "source"
    return {
        "lock_version": LOCK_VERSION, "profile": composition.profile,
        "variables_digest": _digest(composition.variables),
        "core_version": version, "core_digest": _digest(framework),
        "tokens": [{"name": t.name, "module": t.module, "definition": t.definition,
                    "cardinality": t.cardinality, "protocol_version": t.protocol_version}
                   for t in sorted(tokens, key=lambda item: item.name)],
        "entries": entries,
    }

def lock_path(workspace: Path) -> Path:
    return workspace / STATE_DIR / LOCK_NAME

def read(workspace: Path) -> Mapping[str, Any] | None:
    path = lock_path(workspace)
    if not path.exists(): return None
    try: value = json.loads(path.read_text())
    except (OSError, ValueError) as exc: raise CompositionError(str(path), f"unreadable composition lock: {exc}") from exc
    version = value.get("lock_version") if isinstance(value, dict) else None
    if version != LOCK_VERSION: raise CompositionError(str(path), f"unsupported composition lock version: {version}")
    entries = value.get("entries")
    if not isinstance(entries, list) or any(not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in entries):
        raise CompositionError(str(path), "composition lock entries must be objects with string ids")
    return value

def differences(stored: Mapping[str, Any], current: Mapping[str, Any]) -> tuple[str, ...]:
    diffs = []
    old = {e["id"]: e for e in stored.get("entries", [])}
    new = {e["id"]: e for e in current.get("entries", [])}
    for entry_id in sorted(set(old) | set(new)):
        if old.get(entry_id) != new.get(entry_id):
            before, after = old.get(entry_id, {}), new.get(entry_id, {})
            fields = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
            diffs.append(f"{entry_id}: fields changed {','.join(fields)}")
    for field in ("core_version", "core_digest", "tokens", "variables_digest"):
        if stored.get(field) != current.get(field): diffs.append(f"{field}: changed")
    return tuple(diffs)

def reconcile(workspace: Path, current: Mapping[str, Any], *, mode: str) -> tuple[str, ...]:
    path, stored = lock_path(workspace), read(workspace)
    if mode == "create":
        if stored is not None: raise CompositionError(str(path), "create requires an unlocked workspace")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            fd, name = tempfile.mkstemp(prefix=".composition-", dir=path.parent)
            temporary = Path(name)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(current, stream, indent=2, sort_keys=True); stream.write("\n")
                stream.flush(); os.fsync(stream.fileno())
            os.link(temporary, path)
        except FileExistsError as exc:
            raise CompositionError(str(path), "composition lock appeared during create") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return ()
    if mode != "resume": raise ValueError("lock mode must be create or resume")
    if stored is None: raise CompositionError(str(path), "resume requires an existing version 2 lock")
    diffs = differences(stored, current)
    old, new = ({e["id"]: e for e in stored.get("entries", [])},
                {e["id"]: e for e in current.get("entries", [])})
    strict = {i for i in set(old) | set(new)
              if old.get(i, {}).get("resume_policy", "strict") == "strict"
              or new.get(i, {}).get("resume_policy", "strict") == "strict"}
    sensitive = []
    for diff in diffs:
        subject = diff.split(":", 1)[0]
        if diff.startswith(("core_", "tokens:", "variables_digest:")) or subject in strict:
            sensitive.append(diff); continue
        if subject in old or subject in new:
            fields = set(diff.rsplit(" ", 1)[-1].split(","))
            allowed = set(old.get(subject, {}).get("observational_fields", ()))
            allowed &= set(new.get(subject, {}).get("observational_fields", ()))
            if not fields <= allowed:
                sensitive.append(diff)
    if sensitive: raise CompositionError(str(path), "resume identity mismatch: " + "; ".join(sensitive))
    return diffs

__all__ = ["LOCK_NAME", "LOCK_VERSION", "differences", "lock_path", "package_dir", "read", "reconcile", "snapshot"]
