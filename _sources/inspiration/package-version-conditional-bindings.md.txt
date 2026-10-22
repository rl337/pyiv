# Inspiration: generalized version-aware conditional bindings

**Status:** env-stable core is implemented (see ``pyiv.version`` and the
user-guide page "Version-conditioned bindings"). Message-scoped /
per-request version context remains open.

The central abstraction is **version-conditioned bindings over named version
sources**, not specifically Python package versions. Package-version and
interpreter-version conditions are convenience adapters over that core.

## Implemented (env-stable)

- Fluent Binder: ``for_version``, ``for_package_version``,
  ``for_package_present``, ``for_package_absent``, ``for_python_version``
- ``VersionSource`` / ``VersionParser`` with named registry (``PEP440`` default)
- Public :mod:`pyiv.pep440` engine; parsers raise ``InvalidVersion`` subclasses
- Injectable ``PythonVersionProvider`` (``SysPythonVersionProvider`` /
  ``FixedPythonVersionProvider``) so tests simulate many interpreters
- Custom domains via host sources + named parsers
- Selection at injector construction; ambiguity / absent / fallback diagnostics
- ``MapVersionSource`` for non-Python domain tests

## Motivation

A host application may inherit a package such as `requests` transitively, with a version chosen by other dependencies. An adapter library should be able to register implementations compatible with different installed versions without requiring the host to select the adapter manually.

pyiv already provides Guice-style configuration, `Config.register`, and a fluent `self.get_binder().bind(Abstract).to(Concrete)` API. Extend that existing Binder surface rather than introducing a new binding dialect.

## Developer experience

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

Version specifiers for Python/package domains follow PEP 440 via a stdlib-only
matcher (no third-party runtime dependency).

Interpreter specialization uses an injectable provider:

```python
binder.bind(PythonVersionProvider).to_instance(FixedPythonVersionProvider("3.10.12"))
binder.bind(AsyncRunner).to(LegacyAsyncRunner).for_python_version("<3.11")
binder.bind(AsyncRunner).to(TaskGroupAsyncRunner).for_python_version(">=3.11")
```

Optional package **presence / absence** (accelerator vs stdlib) uses the same
candidate store — no version range required:

```python
binder.bind(Encoder).to(CJsonEncoder).for_package_present("cjson")
binder.bind(Encoder).to(JsonEncoder).for_package_absent("cjson")
```

Sugar for `for_package_version(dist, "*")` / `for_package_version(dist, "!")`
(`PACKAGE_PRESENT` / `PACKAGE_ABSENT`). Checks distribution metadata, not
`sys.modules`.

## Still open

### Request/message-scoped versions

Avro writer schema IDs, Protobuf envelope schema revisions, or negotiated
protocol versions may differ between successive resolutions. Supply a version
context to the relevant resolution or create an explicitly scoped child
injector. Never cache a schema-specific singleton across incompatible version
contexts.

Avro schema fingerprints, registry IDs, and Protobuf descriptor identities are
not necessarily ordered version numbers. Where no meaningful total order
exists, use exact-match identities or a separate compatibility predicate.

### Other follow-ups

- Version-conditioned ``bind_key`` / qualified keys
- Multi-package predicates on one binding
- Richer inspection APIs for candidate predicates and rejection reasons
- Optional ``from_version`` / ``to_version`` range sugar vs specifier strings only
- Import-name / ``find_spec`` presence (today presence is distribution metadata
  via ``for_package_present``)

## Source

Original design inspiration: user-proposed `bind(HttpClient, to=...).for_package_version(X)` compatibility selection for transitive Python dependencies (2026-10-15). Adapted to pyiv's existing fluent Binder API.
