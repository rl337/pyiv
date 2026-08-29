# Changelog

User-facing changes to pyiv, in [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
order. The first public PyPI version will be **0.3.0**. Until then, install with:

```bash
pip install git+https://github.com/rl337/pyiv.git
```

## Unreleased

### Added

- This changelog, a [docs page](https://rl337.org/pyiv/changelog.html), and a
  Changelog URL in package metadata.

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
