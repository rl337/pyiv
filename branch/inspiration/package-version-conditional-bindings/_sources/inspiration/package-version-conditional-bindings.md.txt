# Inspiration: generalized version-aware conditional bindings

Status: proposal, not implemented.

The central abstraction is **version-conditioned bindings over named version sources**, not specifically Python package versions. Package-version conditions are a convenience adapter over that core.

## Motivation

A host application may inherit a package such as `requests` transitively, with a version chosen by other dependencies. An adapter library should be able to register implementations compatible with different installed versions without requiring the host to select the adapter manually.

pyiv already provides Guice-style configuration, `Config.register`, and a fluent `self.get_binder().bind(Abstract).to(Concrete)` API. Extend that existing Binder surface rather than introducing a new binding dialect.

## Proposed developer experience

```python
from pyiv import Config

class HttpConfig(Config):
    def configure(self):
        binder = self.get_binder()
        binder.bind(HttpClient).to(RequestHttpClientLegacy).for_package_version(
            "requests", "<2.30"
        )
        binder.bind(HttpClient).to(RequestHttpClientModern).for_package_version(
            "requests", ">=2.30,<3"
        )
```

This syntax is illustrative and must be validated against BindingBuilder internals. The method should be available on the builder and coexist with `.in_scope(...)` and other binding options. Version specifiers should follow PEP 440, preferably using an optional integration with `packaging` or a documented small stdlib-only strategy that preserves pyiv's zero-runtime-dependency promise. Do not implement an incomplete custom PEP 440 parser silently.

## Generalized version binding design

Proposed fluent Binder usage (illustrative, not yet implemented):

```python
binder = self.get_binder()
binder.bind(EventDecoder).to(AvroDecoderV1).for_version(
    "event-schema", from_version=1, to_version=3
)
binder.bind(EventDecoder).to(AvroDecoderV2).for_version(
    "event-schema", from_version=4, to_version=7
)
```

The API must define whether `to_version` is inclusive; for integer schema revisions, inclusive bounds are intuitive. Also support open-ended intervals, exact versions, and explicit exclusive endpoints. Avoid implicit conversion between arbitrary version types.

Separate three responsibilities:

- **Version source**: obtains the current value for a named domain, such as `event-schema`, `requests`, `protobuf-message`, or `wire-protocol`.
- **Version comparator / range**: compares values within that domain. Integer schema revisions, semantic versions, and PEP 440 package versions have different ordering rules. Never assume lexicographic string ordering.
- **Conditional binding selector**: filters candidate implementations and applies documented ambiguity/fallback policy.

`for_package_version(distribution, specifier)` should compile to the same internal conditional-binding representation, using `importlib.metadata` as the source and a PEP 440-compliant matcher. Avoid a second package-specific selection engine.

### Two resolution lifetimes

1. **Environment-scoped**: installed package versions or static application versions are stable for an injector. Selection may be finalized at injector construction.
6. **Request/message-scoped**: Avro writer schema IDs, Protobuf envelope schema revisions, or negotiated protocol versions may differ between successive resolutions. Supply a version context to the relevant resolution or create an explicitly scoped child injector. Never cache a schema-specific singleton across incompatible version contexts.

For example, an application might conceptually resolve `EventDecoder` with `{"event-schema": 5}` for one message and `{"event-schema": 2}` for the next. The final public context-passing API should follow pyiv's existing injector and scope conventions rather than inventing a separate container.

### Avro / Protobuf caveats

Avro schema fingerprints, registry IDs, and Protobuf descriptor identities are not necessarily ordered version numbers. A registry subject's explicit revision number or an application-defined compatibility epoch may provide a valid ordered domain. In Protobuf, a message's generated type does not automatically reveal an ordered schema revision. Where no meaningful total order exists, use exact-match identities or a separate compatibility predicate rather than inventing an ordering.

## Python interpreter version specialization

The running interpreter is another stable, environment-scoped version source. Expose a convenience method on the existing fluent Binder builder:

```python
binder = self.get_binder()
binder.bind(AsyncRunner).to(LegacyAsyncRunner).for_python_version("<3.11")
binder.bind(AsyncRunner).to(TaskGroupAsyncRunner).for_python_version(">=3.11")
```

`for_python_version(specifier)` should use the same generic version-condition selector as `for_version` and `for_package_version`, with an interpreter-version provider based on `sys.version_info` and a documented comparison policy. It must not mistake the installed interpreter version for a package distribution version.

User stories:
- Select compatible implementations for Python 3.8 through current supported interpreters without callers branching on `sys.version_info`.
- Permit testing simulated Python versions through injected version providers, not by changing the actual runtime.
- Respect Python's parsing and import limitations: version-specific modules containing unsupported syntax or unavailable imports must be loaded lazily or otherwise isolated. Conditional injection alone cannot make invalid syntax importable.
- Preserve the existing pyiv Python 3.8+ baseline; introducing this feature must not itself require newer syntax.

## User stories and acceptance criteria

1. **Arbitrary version domains.** Bind implementations over named version domains with explicit inclusive/exclusive ranges and domain-specific comparators.
6. **Schema-aware construction.** Select Avro or Protobuf adapters using a caller-supplied schema version, including different versions in consecutive messages.
7. **Reusable core.** Implement package-version matching as an adapter over the same general conditional-binding engine, without duplicate selection logic.
8. **Version lifetime safety.** Keep environment-stable and message-scoped versions distinct, including cache and singleton semantics.
9. **Transitive dependency compatibility.** Given multiple conditional bindings for the same interface, select the implementation whose package constraint matches the installed distribution version, including when the package is only transitively installed.
6. **Version ranges.** Support meaningful constraints such as `<2.30`, `>=2.30,<3`, and exact pins, with clear handling of prereleases according to the chosen standards-compliant matcher.
7. **No matching version.** Report the package name, detected version, requested interface, and available constraints; never silently select an incompatible implementation.
8. **Package absent.** Report a distinct missing-distribution diagnostic. Avoid importing the target library merely to discover its version.
9. **Overlapping matches.** Reject ambiguous competing matches unless an explicit and documented precedence mechanism is introduced. Do not depend on registration order.
10. **Unconditional fallback.** Define explicit semantics for a normal binding alongside conditional candidates: use it only when no conditional match exists, if this behavior is opted into or documented. Never mask an unsupported version accidentally.
11. **Scopes and providers.** Ensure version-filtered bindings retain existing scope, provider, qualifier, and lifecycle behavior.
12. **Testability.** Permit injecting a version resolver or installed-distribution map in tests; exercise selection without monkeypatching global package metadata or installing multiple distributions.
13. **Determinism.** Resolve conditions at injector construction or a clearly specified stable phase, and cache per-injector results. Do not unexpectedly switch implementations during a running injector lifetime.
14. **Diagnostics.** Offer inspection of candidate bindings, version predicates, selected binding, and rejection reasons.

## Architecture considerations

- Treat version-source lookup and comparison as injectable collaborators so tests can provide deterministic values.
- Support numeric revision ranges and PEP 440 specifiers through separate comparison strategies; do not use string comparison for numbers or semantic versions.
- Decide how to detect overlap of ranges (at configuration time when possible, otherwise reject multiple matching candidates at resolution).
- Define behavior when a version context is absent, and distinguish that from an explicitly unknown schema revision.
- Preserve scopes and qualified keys while preventing cross-version cache contamination.

- Python `importlib.metadata.version("requests")` is an appropriate metadata source (with the Python 3.8 baseline), but distribution names and import names are not always identical. Accept the **distribution name**, normalize it per packaging conventions, and document this distinction.
- Conditional registrations cannot simply overwrite `Config._registrations[abstract]`: store candidate records independently and select after composing installed Config modules, private bindings, and overrides.
- Inspect `pyiv/binder.py` (`BindingBuilder` / `ConfigBinder`), `pyiv/config.py` (`register` and configuration composition), and `pyiv/injector.py` (resolution). Preserve existing unconditional binding semantics.
- Consider how a library config installed into a host config can contribute version alternatives without collision, and whether a host's explicit override takes precedence.
- A package version condition concerns the **environment** running the injector, not the version of the library declaring the binding.
- Do not imply multiple versions of the same distribution can be simultaneously loaded in one ordinary Python environment. The feature chooses among adapters for the one installed version.
- Consider extending conditions to multiple package predicates in a future iteration, but keep the first implementation focused on one distribution per binding.

## Suggested tests

Add tests for inclusive/exclusive boundaries, open-ended ranges, numeric ordering (9 vs 10), schema revisions varying between consecutive messages, version-context-scoped singleton behavior, custom comparators, exact-match-only identifiers, and package adapters using the generic selector.

Parameterized cases for simulated Python 3.8, 3.10, 3.11 and later, plus older/current package versions, exact pins, boundary versions, prereleases, absent packages, unmatched versions, overlapping ranges, conditional + unconditional bindings, scopes, providers, config installation, private configs, qualified keys, and deterministic resolver overrides. Verify that diagnostics are actionable and that the zero-dependency core remains installable.

## Open questions

- Should the fluent API use `for_version(domain, from_version=..., to_version=...)`, a reusable `VersionRange` object, or both?
- How is per-message version context passed through pyiv injection, including nested dependencies?
- Should non-ordered schema identifiers use a separate exact-match predicate rather than a range?
- Should schema adapters be chosen by writer schema version, reader schema version, or an explicit application compatibility epoch?

- Should a normal unconditional binding be a fallback by default or require an explicit fallback designation?
- Is version selection at configuration finalization or first injection a better fit for pyiv's overlays and overrides?
- Should version predicates be reusable objects for eventual OS, Python-version, and optional-feature predicates?
- How should the `packaging` dependency be handled while keeping core stdlib-only?

## Source

Original design inspiration: user-proposed `bind(HttpClient, to=...).for_package_version(X)` compatibility selection for transitive Python dependencies (2026-10-15). Adapted to pyiv's existing fluent Binder API.
