---
name: package-boundaries
description: >-
  Places code in pyiv (stdlib-only), pyiv-common (PyYAML, requests), or a
  dedicated pyiv-<domain> extra. Use when adding a runtime dependency, importing
  PyYAML, yaml, requests, or a third-party library; creating extras or
  pyiv-pgsql; packaging; or deciding whether a module belongs in core.
---

# Package boundaries

Core `pyiv` is stdlib-only. Third-party integrations live in extra packages.
Prefer **one** extra (`pyiv-common`) over a package per library.

## Decision tree

1. Implementation uses only the Python standard library? → **`pyiv` (core)**.
2. Needs a ubiquitous library (allow-list below)? → **`pyiv-common`**.
3. Needs a domain-specific stack (psycopg, boto3, redis, …)? → dedicated
   `pyiv-<domain>` extra, and **prefer not to**. Do not create a package
   “just in case.”

The README `PostgreSQL(Database)` class is a DI teaching example, not a driver.
A real Postgres integration would be a future `pyiv-pgsql`, not core or common.

## Allow-list for `pyiv-common`

Runtime dependencies today: **PyYAML**, **requests**.

Adding another common dependency is a product decision: update this skill,
`extras/pyiv-common/pyproject.toml`, and `CHANGELOG.md` under Unreleased.
Do not drive-by import a new third-party library.

Hard-depend on the allow-list libraries (no `pyiv-common[yaml]` extras).
Installing `pyiv-common` is one stack.

## Forbidden in core

- Third-party imports (`yaml`, `requests`, …).
- `try/except ImportError` that *uses* a third-party library if present.
- Optional extras that pull third-party code into the `pyiv` wheel.

Allowed: a documented lazy `__getattr__` re-export of an extra’s public type
(see `pyiv.serde` → `YAMLSerDe`). Do not put the name in `__all__` or autodoc.

## Layout

| PyPI name | Import | Path |
| --- | --- | --- |
| `pyiv` | `pyiv` | repo root |
| `pyiv-common` | `pyiv_common` | `extras/pyiv-common/` |
| future `pyiv-pgsql` | `pyiv_pgsql` | `extras/pyiv-pgsql/` |

Do not ship `pyiv.yaml` / `pyiv.pgsql` as namespace submodules. `pyiv` is a
regular package; a second dist cannot add `pyiv.*`.

Install: `pip install pyiv` (core). `pip install pyiv-common` or
`pip install pyiv[common]`. Unreleased extra:

`pip install "pyiv-common @ git+https://github.com/rl337/pyiv.git#subdirectory=extras/pyiv-common"`

## Adding a module to `pyiv-common`

1. Implement under `extras/pyiv-common/pyiv_common/` (subclass core `SerDe` /
   `NetworkClient` / `Config` — do not fork infrastructure).
2. Tests in `extras/pyiv-common/tests/` (no live network; mock `requests`).
3. Runnable module doctest **and** class docs for every public type (what +
   **why it exists** + Example doctest). Same bar as core; see
   `.cursor/rules/pydoc-doctest.mdc`. Export from `pyiv_common/__init__.py`.
4. Docs: `docs/guide/packages.rst` plus autodoc RST; changelog Unreleased.
5. Keep `pyiv-common` version independent (starts 0.1.0). Do not bump it from
   the core auto-version workflow.

## Dedicated extra (rare)

Justified when the dependency would pollute common (databases, cloud SDKs).
New tree: `extras/pyiv-<name>/` with import `pyiv_<name>`, depends on `pyiv`.
Do not add that dependency to `pyiv-common`.

Public-surface sync: [maintain-docs](../maintain-docs/SKILL.md).
