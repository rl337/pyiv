# Changelog

User-facing changes to pyiv, in [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
order. Install with `pip install pyiv`. Unreleased `main` is
`pip install git+https://github.com/rl337/pyiv.git`.

## Unreleased

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
