# Changelog

User-facing changes to pyiv, in [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
order. Install with `pip install pyiv`. Unreleased `main` is
`pip install git+https://github.com/rl337/pyiv.git`.

## Unreleased

### Added

- Constructor injection via ``Annotated[T, Named(...)]`` /
  ``Annotated[T, Matched(...)]``, including ``Optional[T]`` (``None`` only
  when there is no candidate; ambiguity still errors) and
  ``Annotated[Provider[T], Named|Matched]`` for lazy qualified lookup.
- ``InjectorProvider`` accepts a ``Key`` as well as a bare type.

### Notes

- Annotated Named/Matched applies to **constructor** (and callable factory)
  parameters only. ``inject_members`` / field injection still resolve bare
  types; use ``inject(Key(...))`` for qualified field wiring.
- ``Matched`` remains inject-only (not valid on ``register_key`` / ``bind_key``).

## 0.4.1 - 2026-09-27

### Added

- `Named` accepts a string or list/tuple of tags (normalized to a set);
  `Named("json") == Named(["json"])`.
- `Named(..., default=True)` marks the preferred binding for bare
  `inject(Type)` and for `Matched` tie-breaks (at most one per type).
- `Matched(required=..., prefer=...)` inject-only qualifier: required tags
  must match, then maximize prefer overlap, then `default=True`.
- Bare `inject(Type)` falls back to Named bindings when no unqualified
  registration exists (default, sole candidate, or ambiguous error).

### Changed

- Duplicate identical `Named` tag sets for the same type raise at
  registration (no silent last-wins). `install` / merge with replace still
  overwrites the same tag set.
- Ambiguous Named/`Matched` resolution raises `CreationError` with
  `ambiguous=True`; `Optional[T]` does not treat that as a missing binding.

## 0.4.0 - 2026-09-25

### Added

- `pyiv-common` extra package (`pip install pyiv-common` or
  `pip install pyiv[common]`): `YAMLSerDe` (PyYAML) and `RequestsClient`
  (requests). Core `pyiv` stays stdlib-only.
- Module composition: `Config.install` / `Binder.install` (last install wins).
- `PrivateConfig` with `expose()`, and `Injector.create_child()` for
  hierarchical injectors.
- `MapMultibinder` / `Config.map_multibinder` for `Dict[K, V]` injection.
- `override(base).with_(overrides)` for test/prod binding overlays.
- `Stage.DEVELOPMENT` / `Stage.PRODUCTION` with eager singleton warmup.
- `require_explicit_bindings()` to disable JIT construction.
- `CreationError` with dependency path and circular-dependency detection.
- Untargeted `binder.bind(Concrete)` self-bindings; `bind_key` registers
  qualified keys; inject `Injector` by type annotation.

### Changed

- `YAMLSerDe` moved from core to `pyiv-common`. `from pyiv.serde import
  YAMLSerDe` still works if the extra is installed.
- Missing bindings and injection failures raise `CreationError` (with path)
  instead of bare `ValueError` / `TypeError` at the injector boundary.
- Constructor deps that are concrete types are just-in-time constructed when
  explicit bindings are not required (transitive JIT).
- Public class docstrings now state why each type exists and include
  runnable usage examples (doctest-backed) across core DI and test doubles.

## 0.3.0 - 2026-09-07

First public PyPI release.

### Added

- `pip install pyiv` (Python 3.8–3.13).
- Changelog on the docs site and in package metadata.
- `py.typed` so type checkers treat pyiv as typed.

### Changed

- README, docs, and GitHub Releases use `pip install pyiv` instead of a git URL.

## 0.2.24 - 2026-08-29

### Added

- User guide: binding, scopes, keys and collections, testing with doubles.
- Homepage version badge from the package version.

### Fixed

- Sphinx autodoc no longer breaks on Markdown-style lists in docstrings.
- Package overview matches homepage features (injection, scopes, keys, test
  doubles), not factory-first copy.

## 0.2.22 - 2026-08-28

### Changed

- Package metadata: author Richard Lee, documentation
  [https://rl337.org/pyiv/](https://rl337.org/pyiv/).
- GitHub Releases and `RELEASE.md` install from git until PyPI exists.

## 0.2.21 - 2026-08-28

### Added

- Product docs at [https://rl337.org/pyiv/](https://rl337.org/pyiv/) (git
  install, grouped API nav).
- Doctests in CI for examples in `pyiv` module docstrings.

### Fixed

- `register_key` keeps the implementation class.
- `Multibinder.add` registers the binding.

## 0.2.20 - 2026-08-28

### Fixed

- Singleton resolution no longer recurses into itself.
- CI fails when pytest exits 2 (collection errors), not only on test failures.

## Earlier 0.2.x

Pre-PyPI history. Not every auto-bump is listed.

### Added

- Guice-style Provider, Scope, Key, Binder, MembersInjector, Optional, and
  Multibinder.
- Clock, Filesystem, Console (including TTY/PTY), and DateTimeService test
  doubles.
- Reflection, SerDe, network clients, and Command.
- Per-injector and process-wide singletons.
