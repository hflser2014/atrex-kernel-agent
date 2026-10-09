# Run AKA through profile-selected startup

AKA supports the existing optimization script and an installed command. Both use a
launch profile to select a Startup service through Bootstrap and Core. The legacy
adapter calls the original optimization body. Evaluation, sandbox, tools and recovery
continue to use their existing implementations.

## Existing checkout interface

Use Python 3.10 or later and the prerequisites in [Quick Start](quickstart.md). From a
source checkout, no framework installation is required:

```sh
python orchestrator/optimize.py --help
python orchestrator/optimize.py \
  --op-dir /path/to/problem --platform L20N --framework Triton \
  --agent-cli codex --workspace /path/to/runs
```

`--op-dir` selects the problem. It accepts the current native Atrex-Bench layout
(`reference.py`, `input.py`, `shapes.json`, within its owning Bench checkout) or SOL
layout (`definition.json`, `reference.py`, `workload.jsonl`). See [problem
preparation](quickstart.md) for the complete requirements. The AKA checkout path and the
problem path are separate inputs.

Existing optimization arguments and defaults retain their meanings. Profile-selected
environment values and absence are captured for children and recovery. Direct execution,
`python -m orchestrator.optimize`, and imports of `orchestrator.optimize.main` all
dispatch through Core. The application body remains behind `_run_application`, including
the original recovery wrapper. The default adapter never calls public `main` again.

## Installed command

Build the packages with a Python 3.10+ environment containing the `build` frontend:

```sh
python -m pip install build
python tools/build_distributions.py --output /tmp/aka-dist
python -m pip install /tmp/aka-dist/*.whl
```

The adapter packages require a **matching application checkout**, including its normal
runtime files, required submodules and application dependencies. They do not contain the
whole optimization application. Keep the packages and checkout from the same source
revision; the `0.1.0` package version alone does not identify an unreleased checkout.
The legacy adapter validates checkout imports; launch reconstruction also checks the
recorded implementation and explicitly declared resource identities. Initialize required
submodules as described in Quick Start before exporting a checkout without Git metadata.

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
options from the original application's arguments. `--repo-root` identifies the matching
AKA checkout and makes it importable during the call; it does not change the working
directory. `--op-dir` after the separator selects the problem. Without `--workspace`,
the original current-directory workspace default applies.

Framework options are `--repo-root`, `--profile`, `--profiles-dir`, and repeatable
`--patch`. Relative paths resolve from the caller's working directory. A profile is a
JSON file in the chosen profiles directory; the packaged default is `application`.
Framework flags do not replace similarly named application flags, which belong after
`--`.

Core owns the neutral command dispatcher. Bootstrap contributes `run`, and Optimization
contributes `optimize`, via the `aka.commands` package entry-point group. Help lists
installed contributions without importing them; unknown or duplicate command names fail
before loading a command. There is no implicit default command or Execution command in
this version. Source-only use of `python -m aka` requires installed command metadata;
use the original script for development without package installation.

## Select a startup implementation

A launch profile names a Core composition and a service implementing the neutral
synchronous `Startup.run(Invocation) -> int` protocol. Bootstrap does not require
Application or Workflow specifically. Plugin import and `apply(ctx, config)` only
construct instances and register services; invocation starts after assembly.

For example, install this importable module as `example_workflow.py`:

```python
name = "example-workflow"
provide = ("workflow",)

class Workflow:
    def run(self, invocation):
        print(invocation.argv)
        return 0

def apply(ctx, config):
    ctx.provide("workflow", Workflow())
```

Create `profiles/launch.json`:

```json
{"api_version": 1, "composition": "workflow", "target": "workflow"}
```

Create its Core composition at `profiles/compositions/workflow.json`:

```json
{
  "api_version": 1,
  "patches": [
    {"id": "workflow", "insert": {"name": "example_workflow", "required": true}}
  ]
}
```

Then run it with Bootstrap installed and the plugin importable:

```sh
aka run --profile /path/to/profiles/launch.json -- example-argument
```

The instance receives the arguments after `--` as `Invocation.argv`. Removing, disabling
or failing the required target does not fall back to a default. `--patch` and `--var
NAME=VALUE` operate on the referenced Core composition. Additional business tokens must
be defined as `ServiceKey` objects in code and registered through installed `aka.tokens`
entry points or supplied programmatically; profile `tokens` selects those registered
names. `required_services` requires corresponding selected tokens. The target's Startup
token is supplied by the host.

Launch profiles can additionally declare `bindings` (string values), `environment`
(names whose values or absence must survive restart) and `resources` (root/paths whose
content and directory membership determine identity). Resource declarations may pin
submodules by relative path and commit; uninitialized directories preserve the original
initialization flow, while initialized checkouts must match the parent gitlink and
declared commit with a clean working tree.

Custom compositions retaining the legacy plugin are supported when they can be
reconstructed consistently. The legacy profile selects `startup`, implemented by
`aka.legacy.application.plugin`. The temporary Application adapter can later be replaced
by Workflow through a launch-profile change. Bootstrap keeps the same Startup protocol.
Targets own forwarding `Invocation.environment` to children and persisting the selection
for delayed restarts; they do not retain Core's context or composition owner.

## Programmatic invocation and ownership

For a generic startup, use a launch profile and neutral invocation:

```python
from pathlib import Path
from aka.bootstrap.host import run_profile
from aka.contracts.startup import Invocation

exit_code = run_profile(Path("/path/to/profiles/launch.json"), Invocation(("arg1",)))
```

For the preserved optimizer, make the matching checkout importable and use its legacy
host. Generic `aka run` does not add business checkouts to `sys.path`:

```python
from pathlib import Path
from aka.legacy.application.host import run_application
from aka.contracts.application import ApplicationRequest

exit_code = run_application(ApplicationRequest(Path("/path/to/aka"), ("--help",)))
```

`argv=None` preserves the original `sys.argv[1:]` behavior; an explicit sequence is
copied without adding options. The request does not change cwd, environment, stdio or
signal ownership. Normal return, application failure, `SystemExit` and interrupts all
dispose the owned Core composition. Local disposal does not cancel detached or remote
jobs. Registered effects are cleaned up; arbitrary plugin side effects cannot be undone
automatically.

The default adapter checks that `orchestrator.optimize` belongs to the configured
`repo_root` and reuses the existing direct-script module. It calls the original non-dispatching entry exactly once. Core freezes defaults/interpolation before setup.
Bootstrap captures the target, tokens, effective composition and identity of Core,
Bootstrap, Contracts, plugins and declared resources. Post-setup verification rejects
changes outside the frozen composition, including dynamic `Context.plugin()` children
not recorded in its rows.

## Current child and recovery behavior

Framework children receive `AKA_LAUNCH_SELECTION` and `AKA_LAUNCH_DIGEST` through
`Invocation.environment`. Recorded environment values are applied to children; values of
`None` remove the corresponding keys. The legacy adapter persists `launch-selection.json` for delayed recovery. Current schema 4 `restart.json` contains
`launch_environment` referencing this durable file and its digest. The monitor restores
the recorded values instead of inheriting unrelated launch selection variables. Missing
or changed selection, tokens, implementations or resources fail before setup. Core
identity locks remain opt-in and separate from business locks and recovery state.

An existing main schema 3 recovery record without `launch_environment` or any
`launch-selection.json` uses the built-in default legacy profile. Custom profiles,
patches, variables, tokens and supplied continuation selections are rejected.
All original resolved-configuration and state-path checks still apply. Only the
recovery owner may persist the selection and upgrade the record to schema 4,
after those checks pass; a non-owner cannot perform this upgrade. Schema 4 and
records with launch-selection evidence never fall back to the default when their
selection is missing, corrupt or mismatched. Schema 3 retains main's environment
recovery semantics; historical environment values that were never recorded are
not reconstructed. Broader restart-format redesign is deferred.

Existing tool-plugin locks also record absolute plugin paths and interpreter identity.
Retain those inputs and do not rewrite locks to bypass identity checks.

## Distribution

| Distribution | Ownership | Python |
| --- | --- | --- |
| `atrex-aka-core` | `aka`, neutral dispatcher, `aka.core` | 3.9+ |
| `atrex-aka-contracts` | `aka.contracts` | 3.9+ |
| `atrex-aka-bootstrap` | `aka.bootstrap`, generic `aka run` command | 3.10+ |
| `atrex-aka-optimization` | `aka.legacy`, default profiles, `aka optimize` command | 3.10+ |

Core alone has no application dependency. Bootstrap depends only on Core and Contracts;
Optimization depends on Bootstrap. The four packages own disjoint files and pin matching
dependency versions. Distribution boundaries are installation ownership units, not a
requirement to package every future module separately. Build tooling stages owned files,
builds sdists, then builds wheels from those sdists.

The launcher and legacy adapter are migration bridges used by existing entrypoints. They
can be removed when the application implementation and its runtime resources are
packaged and all callers use the supported Bootstrap entry, with equivalent startup,
recovery and installation checks. Execution extraction is not required for this version
to operate.

See [the framework interface](plugin-framework.md) for dependency, scope, event,
configuration and cleanup semantics.
