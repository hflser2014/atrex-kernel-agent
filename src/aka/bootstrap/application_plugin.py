"""Default plugin: construct the whole existing application without running it."""
from .legacy_application import LegacyApplication

name = "application-plugin"
provide = ("application",)
identity_files = ("application_plugin.py", "legacy_application.py")


def apply(ctx, config):
    ctx.provide("application", LegacyApplication())
