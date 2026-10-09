"""Select, run and dispose one application composition."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from aka.contracts.application import ApplicationRequest
from aka.core.boot import boot
from aka.core.effects import call_sync
from aka.core.keys import ServiceKey
from aka.core.errors import BootFailure

from .composition import PROFILES_DIR, compose_application, is_default_application
from .legacy_application import LEGACY_COMPOSITION_ERROR, legacy_composition

APPLICATION = ServiceKey("application", "Application", module="aka.contracts.application")


def run_application(
    request: ApplicationRequest,
    *,
    profile: str = "application",
    profiles_dir: Path = PROFILES_DIR,
    patch_files: Sequence[Path] = (),
    patches: Sequence[Mapping[str, Any]] = (),
    variables: Mapping[str, str] | None = None,
    tokens: Sequence[ServiceKey] = (),
) -> int:
    """Own one composition, including explicitly registered dependency tokens.

    Application plugins resolve declared injections during setup and pass the
    actual values to their constructors. Applications only receive a request
    when invoked; the host disposes the composition on every exit. Additional
    tokens do not broaden the legacy profile's child/recovery compatibility.
    """
    composition = compose_application(
        request.repo_root, profile=profile, profiles_dir=profiles_dir,
        patch_files=patch_files, patches=patches, variables=variables,
    )
    compatible = is_default_application(composition, request.repo_root)
    if not compatible and any(row.name == "aka.bootstrap.application_plugin" for row in composition.enabled):
        raise BootFailure((("application", LEGACY_COMPOSITION_ERROR),))
    report = boot(composition, tokens=(APPLICATION, *tokens), required_services=(APPLICATION.name,))
    try:
        application = report.service(APPLICATION.name)
        entry = getattr(application, "run", None)
        if not callable(entry):
            raise TypeError("selected application must implement run(request)")
        with legacy_composition(compatible):
            result = call_sync(entry, request)
        if type(result) is not int:
            raise TypeError("application.run must return an integer exit code")
        return result
    finally:
        # Only registered effects are unwound; this does not cancel remote work.
        report.dispose()
