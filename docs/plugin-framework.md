# Plugin framework interface

Core provides a synchronous plugin runtime independent of the optimization
application. This guide describes the framework shipped in this source tree.
The existing optimization entrypoint does not use Core in this version.

## Installation

Core supports Python 3.9 or later and has no runtime dependencies. Build and
install it from this checkout using an environment with the `build` frontend:

```sh
python -m pip install build
python tools/build_distributions.py --output /tmp/aka-core-dist
python -m pip install /tmp/aka-core-dist/*.whl
```

## Responsibilities

`aka.core` owns declarations, JSON composition, dependencies, service Realms,
contribution Scopes, effects, events and optional identity locks. It imports
neither the optimization application nor Execution. The existing `plugin_runtime/`
tool/skill registry is unrelated and remains untouched.

## Plugin declaration and lifetime

A plugin module declares a stable `name` matching its module name (underscores
become hyphens), a plain synchronous `apply(ctx, config)`, and optional `provide`,
`inject`, `optional_inject`, `Config`, `Defaults` and `interpolate` exports.
`apply` constructs and registers objects; application execution belongs to its caller.

`ctx.provide(name, value)` registers a module implementation. Consumers declare
injections and obtain the selected object via `ctx.get(name)`. Service tokens
validate declared metadata, not the complete implementation protocol. Callers
remain responsible for validating the behavior of provided implementations.

Required injections gate activation. Dependencies track **registration serials**,
not just provider identity; optional provider appearance and withdrawal also
change the dependency epoch. `Root.settle()` drains queued transitions. This
supports Core-level replacement but does not promise safe live replacement during
optimization. Divergent settling is bounded and reported.

Setup, config validators, event callbacks and cleanup are synchronous. Known async
hooks are rejected before invocation; synchronous wrappers returning awaitables
are rejected at the call site. Returned coroutine objects are closed rather than
silently discarded. Core does not create an event loop or await these hooks.

`ctx.effect(dispose)` and a cleanup callable returned by `apply` register owned
effects. Teardown unwinds effects in reverse order, is idempotent, and drains the
stack even if one cleanup fails. Ordinary cleanup errors are aggregated;
`BaseException` is re-raised after draining. Borrowing an object does not transfer
ownership. Unregistered side effects cannot be undone automatically. Local
teardown does not imply cancellation of detached or remote jobs.

## Composition and required checks

`aka.core.boot.compose()` loads a profile from a caller-selected directory. Bundles
are applied first, followed by profile patches, patch files and programmatic
patches. Patches replace the **whole config**, never deep-merge it. Dependency
injection, not row order, determines activation order.

`boot(composition, tokens=..., required_rows=..., required_services=...)` validates
configuration before applying plugins and rejects duplicate single providers.
A required row must be active even if it was disabled. An explicitly requested
missing row fails; a required service must exist in the root Realm. Removing a row
removes its own declaration. Callers can independently require services. There
is no fallback to the default when selection fails.
Still-mounted children declared with `ctx.plugin(..., required=True)` must also
be active when boot finishes; a pending or failed required child fails boot and
disposes the composition. Explicitly disposed children are no longer requirements.

Core receives a caller-supplied variable map; it has no application-variable
allowlist or hidden defaults. `${aka:name}` references that map; `${env:NAME}` reads
the process environment (an unset environment name yields an empty string).
References are permitted only in plugin-declared dotted field paths. Unknown
variables, unsupported reference syntax and references outside those paths fail.
No expression evaluation or recursive interpolation occurs. Callers own their
variable names and defaults.

Identity locks are opt-in through `boot(..., workspace=..., lock_mode=...)`.
Callers choose whether to enable a lock; Core does not define application recovery
policy or a persisted campaign format.

## Isolation and events

Service **Realm** isolation controls visibility of selected implementations.
Named contribution **Scope** rules control contribution lookup. Neither provides
per-plugin event routing: events are shared inside a Root. Separate independent
application invocations use separate roots.

Event listeners run in order/registration order, except `parallel`, which uses a
thread pool and waits for completion (not async lifecycle support):

| Mode | Behavior |
| --- | --- |
| `emit` | Notify all live observers; report ordinary observer exceptions |
| `parallel` | Notify concurrently; report ordinary observer exceptions |
| `serial` | Stop at the first non-`None` result, including `False`, `0` and `""` |
| `bail` | Stop at the first truthy result; skip falsey values |
| `waterfall` | Nested delegation through `next`; a listener may short-circuit, which is recorded |

Serial, bail and waterfall errors propagate. Waterfall delegates may be called
once and only during their dispatch. Monotonic waterfalls enforce declared
shrink checks on both forwarding and returning. Observer errors reach the Root's
error reporting path; they are not silently treated as successful results.

## DSH comparison and limits

AKA Core is inspired by Cordis plus loader mechanics, not by DSH's product
`packages/core` plugin collection. It is not a Cordis-compatible runtime.
DSH's asynchronous lifecycle, contextual event routing and event stop rules differ.
No DSH dependency is installed. Async lifecycle, contextual event isolation,
automatic discovery and application hot reload are not PR1 promises.
