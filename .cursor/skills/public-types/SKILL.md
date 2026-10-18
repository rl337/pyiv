---
name: public-types
description: >-
  Design public pyiv types as pydantic-friendly shapes without a pydantic
  dependency. Use when adding or changing public classes, option bags,
  Protocols, Config value objects, stdlib injectable surfaces, HTTP/console
  DTOs, or frozen dataclasses in pyiv/ or extras/.
---

# Public types (pydantic-friendly without pydantic)

Core `pyiv` stays stdlib-only. Do **not** import pydantic, soft-import it, or
ship `__get_pydantic_core_schema__` hooks. Compatibility comes from **shapes**
pydantic already understands.

See also: [package-boundaries](../package-boundaries/SKILL.md),
`AGENTS.md` Design Principles, `.cursor/rules/public-types.mdc`.

## Split: services vs knobs

| Kind | Shape | Examples |
| --- | --- | --- |
| **Service** (injectable behavior) | `Protocol` or ABC + Real/Memory impls | `Filesystem`, `Clock`, `HttpClient`, `Logger` |
| **Knob** (options / DTO / qualifier) | `@dataclass(frozen=True)` or `TypedDict` | `LogOptions`, `HttpClientOptions`, `Named`, `RecordedRequest` |

Apps bind services in the injector. Knobs may be nested in host
`BaseModel` / `BaseSettings` without pyiv knowing about pydantic.

## Do

1. **Frozen dataclasses** for option bags and public value DTOs.
2. **Boring field types**: `str`, `int`, `float`, `bool`, `Path` (or str paths),
   `Mapping`/`dict`, `FrozenSet`, enums, `datetime` when natural.
3. **Annotated constructors** on services; prefer untyped optional kwargs only
   when bare `register(Iface, Impl)` must not try to inject `Mapping`/`str`.
4. **`as_dict` / `from_dict`** (or `dataclasses.asdict`) on knobs when Settings
   round-trip helps.
5. **Copy mutable mappings** into frozen instances in `__post_init__` when needed.
6. Point at existing patterns: `VersionBindingCandidate` in `pyiv/version.py`
   (frozen DI metadata); HTTP/console frozen DTOs after remediation.

## Don’t

1. Import or soft-depend on pydantic in core (or via `ImportError` probes).
2. Put pydantic on the `pyiv-common` allow-list “just in case.”
3. Custom metaclasses that fight `BaseModel`.
4. Mutable public dataclasses for value objects (prefer `frozen=True`).
5. God-object module mirrors (`Sys`, `Os`, `Io`) — use use-case packages.
6. Replace `Command`’s `argparse.Namespace` with a pydantic model in core;
   hosts adapt.
7. Expect `Type[T]` / Provider / Scope fields to be JSON-friendly (e.g.
   `VersionBindingCandidate` stays DI metadata).

## App pattern (document when touching knobs)

Host defines Settings → maps into pyiv frozen options →
`register_instance` / provider → services take Options or already-built deps.
pyiv never subclasses `BaseModel`.
