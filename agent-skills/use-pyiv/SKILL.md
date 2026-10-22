---
name: use-pyiv
description: >-
  Builds and refactors Python apps with pyiv dependency injection: Config,
  Binder, scopes, Keys/Named/Matched, top-level injectables, and pyiv-common.
  Use when writing or changing code that uses pyiv, get_injector, register,
  bind, inject, or pyiv test doubles.
---

# Use pyiv

pyiv is Guice-style DI for Python. Prefer constructor injection and type
bindings over service locators or global state.

Install: `pip install pyiv`. Related: `pip install pyiv-common` (PyYAML,
requests). Docs: https://rl337.org/pyiv/

## Prefer top-level imports

Featured APIs are re-exported from `pyiv`:

```python
from pyiv import Config, get_injector, Filesystem, Clock, Logger, Environment
```

Use-case packages (`pyiv.files`, `pyiv.time`, `pyiv.log`, `pyiv.process`) are
fine for organization; top-level imports are the recommended app surface.

## Wire with Config

```python
from pyiv import Config, get_injector, Filesystem, MemoryFilesystem, RealFilesystem

class ProdConfig(Config):
    def configure(self):
        self.register(Filesystem, RealFilesystem)

class TestConfig(Config):
    def configure(self):
        self.register(Filesystem, MemoryFilesystem)

injector = get_injector(ProdConfig)
fs = injector.inject(Filesystem)
```

- Bind interfaces (ABC/Protocol) to implementations.
- Use `singleton=True` or scopes when one shared instance is required.
- Prefer `override(ProdConfig).with_(TestConfig)` to swap doubles in tests.
- Optional accelerators (distribution name, not import name):

```python
binder.bind(Encoder).to(CJsonEncoder).for_package_present("cjson")
binder.bind(Encoder).to(JsonEncoder).for_package_absent("cjson")
# or: for_package_present(...) then unconditional bind(...).to(Std) fallback
```

  Tests: `MapVersionSource` on `package_version_domain("cjson")` to simulate
  installed. Docs: https://rl337.org/pyiv/guide/version-bindings.html.

## Constructor injection

Annotate constructor parameters with types pyiv can resolve. Use
`Annotated[T, Named(...)]` / `Matched(...)` for qualified deps (constructor
params only — not field/`inject_members` paths).

## Do

1. Depend on injectables (`Filesystem`, `Clock`, `HttpClient`, `Logger`,
   `Environment`, `ProcessRunner`) instead of calling `open`, `time.sleep`,
   `os.environ`, `subprocess`, or `logging.getLogger` at call sites you own.
2. Keep option bags as frozen dataclasses with boring fields (`str`, `int`,
   `bool`, `Path`, mappings, enums) so Settings/pydantic hosts can nest them
   without pyiv depending on pydantic.
3. Put third-party stacks (DB, cloud SDKs) behind your own Protocols; bind
   Real vs Fake in Config. Core pyiv stays stdlib-only; `pyiv-common` is for
   YAML/requests only.

## Don't

1. Monkeypatch builtins or stdlib modules as the primary test strategy when a
   pyiv double exists.
2. Invent god-objects named after modules (`Os`, `Sys`, `Io`); use purpose
   surfaces already exported from `pyiv`.
3. Soft-import optional third-party libraries inside core app paths without an
   explicit extra/package story.

## See also

- Testing doubles: companion skill `pyiv-testing`
- Site: https://rl337.org/pyiv/guide/testing.html
- Catalog of stdlib surfaces:
  https://github.com/rl337/pyiv/blob/main/docs/inspiration/stdlib-injectable-surfaces.md
