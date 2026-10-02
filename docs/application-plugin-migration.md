# Run AKA through the application framework

AKA exposes a programmatic Bootstrap entry that selects an Application through
Core. The default adapter calls the original optimization body. Workflow,
evaluation, sandbox, tools and recovery retain their existing implementations.
The existing script still calls the application directly; an installed command
is not provided in this version.

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
of `orchestrator.optimize.main` call `_run_application` directly. The adapter
calls that same internal entry, including its original recovery wrapper, and
never calls public `main` again.

## Install the programmatic adapter

Build the packages with a Python 3.10+ environment containing the `build` frontend:

```sh
python -m pip install build
python tools/build_distributions.py --output /tmp/aka-dist
python -m pip install /tmp/aka-dist/*.whl
```

The adapter requires a **matching application checkout**, including its normal
runtime files, required submodules and application dependencies. It does not
contain the whole optimization application. Keep packages and checkout from the
same source revision; the `0.1.0` version alone does not identify an unreleased
checkout. Initialize required submodules as described in Quick Start before
exporting a checkout without Git metadata. The adapter validates the import
location, not every file's release hash.

For source development, use `PYTHONPATH=src` from the checkout root to import the
framework. For installed use, make the matching checkout importable, for example
by adding its absolute path to `PYTHONPATH` before starting Python. Pass the same
absolute path in `ApplicationRequest.repo_root`.

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

Then invoke it explicitly, with the matching checkout importable:

```python
from pathlib import Path
from aka.bootstrap.application import run_application
from aka.contracts.application import ApplicationRequest

exit_code = run_application(
    ApplicationRequest(Path("/path/to/aka"), ("example-argument",)),
    patch_files=(Path("select-application.json"),),
)
```

`run_application` accepts `profile`, `profiles_dir`, `patch_files`, programmatic
`patches`, and `variables`. The packaged profile is `application`; profiles are
JSON files in the selected directory. Relative paths resolve from the caller's
working directory. The selected implementation receives the request's original
argument sequence. There is no fallback to the default when a provider is missing, disabled, inactive or invalid.
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
script commands, workspace formats and policy; child scripts still call the
application directly. Each programmatic Bootstrap invocation creates its own Core
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
| `atrex-aka-core` | `aka`, `aka.core` | 3.9+ |
| `atrex-aka-contracts` | `aka.contracts` | 3.9+ |
| `atrex-aka-optimization` | `aka.bootstrap`, profiles | 3.10+ |

Core alone has no application dependency. The three packages own disjoint files;
the adapter pins matching Core and Contracts versions. Build tooling stages owned
files, builds sdists, then builds wheels from those sdists.

The legacy adapter is a migration bridge. It can be removed when the application
implementation and its runtime resources are packaged and callers use a supported
Bootstrap entry, with equivalent startup, recovery and installation checks.
Execution extraction is not required for this version to operate.

See [the framework interface](plugin-framework.md) for dependency, scope, event,
configuration and cleanup semantics.
