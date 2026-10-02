# Run AKA through the application framework

AKA supports the existing optimization script and an installed command. Both use
Bootstrap and Core to select an Application, then the default adapter calls the
original optimization body. Workflow, evaluation, sandbox, tools and recovery
continue to use their existing implementations.

## Existing checkout interface

Use Python 3.10 or later and the prerequisites in [Quick Start](quickstart.md).
From a source checkout, no framework installation is required:

```sh
python orchestrator/optimize.py --help
python orchestrator/optimize.py \
  --op-dir /path/to/problem --platform L20N --framework Triton \
  --agent-cli codex --workspace /path/to/runs
```

`--op-dir` selects the problem. It accepts the current native Atrex-Bench layout
(`reference.py`, `input.py`, `shapes.json`, within its owning Bench checkout) or
SOL layout (`definition.json`, `reference.py`, `workload.jsonl`). See
[problem preparation](quickstart.md) for the complete requirements. The AKA
checkout path and the problem path are separate inputs.

Existing arguments, defaults, environment variables and saved workspaces retain
their meanings. Direct execution, `python -m orchestrator.optimize`, and imports
of `orchestrator.optimize.main` all dispatch through Core. The application body
remains behind `_run_application`, including the original recovery wrapper. The
default adapter never calls public `main` again.

## Installed command

Build the packages with a Python 3.10+ environment containing the `build` frontend:

```sh
python -m pip install build
python tools/build_distributions.py --output /tmp/aka-dist
python -m pip install /tmp/aka-dist/*.whl
```

The adapter packages require a **matching application checkout**, including its
normal runtime files, required submodules and application dependencies. They do
not contain the whole optimization application. Keep the packages and checkout
from the same source revision; the `0.1.0` package version alone does not identify
an unreleased checkout. The CLI validates the import location, not every file's
release hash. Initialize required submodules as described in Quick Start before
exporting a checkout without Git metadata.

The command can run from any working directory:

```sh
aka --help
aka optimize --help
aka optimize --repo-root /path/to/aka -- --help
aka optimize --repo-root /path/to/aka --profile application -- \
  --op-dir /path/to/problem --platform L20N --framework Triton \
  --agent-cli codex --workspace /path/to/runs
```

`python -m aka` accepts the same commands. The mandatory `--` separates framework
options from the original application's arguments. `--repo-root` identifies the
matching AKA checkout and makes it importable during the call; it does not change
the working directory. `--op-dir` after the separator selects the problem.
Without `--workspace`, the original current-directory workspace default applies.

Framework options are `--repo-root`, `--profile`, `--profiles-dir`, and repeatable
`--patch`. Relative paths resolve from the caller's working directory. A profile
is a JSON file in the chosen profiles directory; the packaged default is
`application`. Framework flags do not replace similarly named application flags,
which belong after `--`.

Core owns the neutral command dispatcher. The adapter contributes `optimize` via
the `aka.commands` package entry-point group. Help lists installed contributions
without importing them; unknown or duplicate command names fail before loading a
command. There is no implicit default command or Execution command in this version.
Source-only use of `python -m aka` requires installed command metadata; use the
original script for development without package installation.

## Select another application

An application plugin supplies the `application` service and a synchronous
`run(ApplicationRequest) -> int`. Plugin import and `apply` only construct the
adapter. Register owned cleanup with `ctx.effect`; the caller owns the composition.
For example, install the following as an importable module `example_app`:

```python
name = "example-app"
provide = ("application",)

def apply(ctx, config):
    class Application:
        def run(self, request):
            print(request.repo_root, request.argv)
            return 0
    ctx.provide("application", Application())
```

Use a patch file such as `select-application.json`:

```json
{
  "api_version": 1,
  "patches": [
    {"id": "application", "remove": true},
    {"id": "example", "insert": {"name": "example_app", "required": true}}
  ]
}
```

Then invoke it explicitly:

```sh
aka optimize --repo-root /path/to/aka --patch select-application.json -- example-argument
```

The selected implementation receives only the arguments after `--`. There is no
fallback to the default when a provider is missing, disabled, inactive or invalid.
The application plugin is an adapter for the whole application, not a new Workflow
implementation or an additional long-term business selection slot.

The legacy adapter supports only the default effective composition: the same rows
and application variables as the packaged `application` profile. An equivalent
profile in another file is accepted; provenance and documentation fields do not
affect that comparison. Customized compositions containing the legacy plugin fail
before plugin setup. An alternate provider that tries to delegate to the legacy
adapter also fails before the original application runs, and its registered
effects are disposed. This prevents child or recovery processes silently losing
the selected composition. Independent alternate applications own their process
launch and continuation behavior. Custom compositions around the legacy
application require a future explicit launch/recovery integration.

## Programmatic invocation and ownership

Make the matching checkout importable, then pass it explicitly:

```python
from pathlib import Path
from aka.bootstrap.application import run_application
from aka.contracts.application import ApplicationRequest

exit_code = run_application(ApplicationRequest(Path("/path/to/aka"), ("--help",)))
```

`argv=None` preserves the original `sys.argv[1:]` behavior; an explicit sequence is
copied without adding options. The request does not change cwd, environment,
stdio or signal ownership. Normal return, application failure, `SystemExit` and
interrupts all dispose the owned Core composition. Local disposal does not cancel
detached or remote jobs. Registered effects are cleaned up; arbitrary plugin side
effects cannot be undone automatically.

The default adapter checks that the resolved `orchestrator.optimize` belongs to
`repo_root` and reuses the existing direct-script module. It calls the internal
entry exactly once. Framework child processes and recovery keep their original
script commands, workspace formats and policy; each process creates its own Core
root. No new identity lock or persisted campaign format is enabled.

Existing tool-plugin locks include absolute plugin paths and interpreter identity.
Resume an existing run with those locked inputs intact: upgrading the application
in the same checkout is supported, but moving to another checkout or interpreter
can still be rejected by the existing lock. Do not rewrite the lock to bypass the
check. Keep the original checkout/environment available for rollback; this change
does not migrate old workspaces to a different plugin location.

## Distribution

| Distribution | Ownership | Python |
| --- | --- | --- |
| `atrex-aka-core` | `aka`, neutral dispatcher, `aka.core` | 3.9+ |
| `atrex-aka-contracts` | `aka.contracts` | 3.9+ |
| `atrex-aka-optimization` | `aka.bootstrap`, profiles, application command | 3.10+ |

Core alone has no application dependency. The three packages own disjoint files;
the adapter pins matching Core and Contracts versions. Build tooling stages owned
files, builds sdists, then builds wheels from those sdists.

The launcher and legacy adapter are migration bridges used by existing entrypoints.
They can be removed when the application implementation and its runtime resources
are packaged and all callers use the supported Bootstrap entry, with equivalent
startup, recovery and installation checks. Execution extraction is not required
for this version to operate.

See [the framework interface](plugin-framework.md) for dependency, scope, event,
configuration and cleanup semantics.
