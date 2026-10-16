# Inspiration: package-version-aware conditional bindings

Status: proposal, not implemented.

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

## User stories and acceptance criteria

1. **Transitive dependency compatibility.** Given multiple conditional bindings for the same interface, select the implementation whose package constraint matches the installed distribution version, including when the package is only transitively installed.
2. **Version ranges.** Support meaningful constraints such as `<2.30`, `>=2.30,<3`, and exact pins, with clear handling of prereleases according to the chosen standards-compliant matcher.
3. **No matching version.** Report the package name, detected version, requested interface, and available constraints; never silently select an incompatible implementation.
4. **Package absent.** Report a distinct missing-distribution diagnostic. Avoid importing the target library merely to discover its version.
5. **Overlapping matches.** Reject ambiguous competing matches unless an explicit and documented precedence mechanism is introduced. Do not depend on registration order.
6. **Unconditional fallback.** Define explicit semantics for a normal binding alongside conditional candidates: use it only when no conditional match exists, if this behavior is opted into or documented. Never mask an unsupported version accidentally.
7. **Scopes and providers.** Ensure version-filtered bindings retain existing scope, provider, qualifier, and lifecycle behavior.
8. **Testability.** Permit injecting a version resolver or installed-distribution map in tests; exercise selection without monkeypatching global package metadata or installing multiple distributions.
9. **Determinism.** Resolve conditions at injector construction or a clearly specified stable phase, and cache per-injector results. Do not unexpectedly switch implementations during a running injector lifetime.
10. **Diagnostics.** Offer inspection of candidate bindings, version predicates, selected binding, and rejection reasons.

## Architecture considerations

- Python `importlib.metadata.version("requests")` is an appropriate metadata source (with the Python 3.8 baseline), but distribution names and import names are not always identical. Accept the **distribution name**, normalize it per packaging conventions, and document this distinction.
- Conditional registrations cannot simply overwrite `Config._registrations[abstract]`: store candidate records independently and select after composing installed Config modules, private bindings, and overrides.
- Inspect `pyiv/binder.py` (`BindingBuilder` / `ConfigBinder`), `pyiv/config.py` (`register` and configuration composition), and `pyiv/injector.py` (resolution). Preserve existing unconditional binding semantics.
- Consider how a library config installed into a host config can contribute version alternatives without collision, and whether a host's explicit override takes precedence.
- A package version condition concerns the **environment** running the injector, not the version of the library declaring the binding.
- Do not imply multiple versions of the same distribution can be simultaneously loaded in one ordinary Python environment. The feature chooses among adapters for the one installed version.
- Consider extending conditions to multiple package predicates in a future iteration, but keep the first implementation focused on one distribution per binding.

## Suggested tests

Parameterized cases for older/current versions, exact pins, boundary versions, prereleases, absent packages, unmatched versions, overlapping ranges, conditional + unconditional bindings, scopes, providers, config installation, private configs, qualified keys, and deterministic resolver overrides. Verify that diagnostics are actionable and that the zero-dependency core remains installable.

## Open questions

- Should a normal unconditional binding be a fallback by default or require an explicit fallback designation?
- Is version selection at configuration finalization or first injection a better fit for pyiv's overlays and overrides?
- Should version predicates be reusable objects for eventual OS, Python-version, and optional-feature predicates?
- How should the `packaging` dependency be handled while keeping core stdlib-only?

## Source

Original design inspiration: user-proposed `bind(HttpClient, to=...).for_package_version(X)` compatibility selection for transitive Python dependencies (2026-10-15). Adapted to pyiv's existing fluent Binder API.
