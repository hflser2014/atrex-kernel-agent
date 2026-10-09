"""Default plugin: construct the whole existing application without running it."""
from pathlib import Path

from .legacy_application import create_legacy_application

name = "application-plugin"
provide = ("application",)
identity_files = ("application_plugin.py", "legacy_application.py")
identity_packages = ("aka.application",)


def apply(ctx, config):
    # Assembly reads host variables once. The Application receives a bound
    # execution entry, never the Context, Root or a lookup callback.
    repo_root = Path(ctx.fiber.root.variables["repo_root"])
    ctx.provide("application", create_legacy_application(repo_root))
